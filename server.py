# Read env vars from .env file
from dotenv import load_dotenv
load_dotenv()

import base64
import os
import datetime
import plaid
import json
import time
from flask import Flask, request, jsonify, render_template, session, g, redirect, flash
from models import db, connect_db, Transactions, UserTransaction, User, Category, UserCategories
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from forms import SignupUser, LoginForm, EditUserForm, NewCategory
import os
# from flask_cors import CORS

# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
CURR_USER_KEY = "curr_user"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///plaid_db')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///plaid_db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "thisIsTopSecret!")
# app.config['SECRET_KEY'] = "plaidSandbox"
# CORS(app)

# Fill in your Plaid API keys - https://dashboard.plaid.com/account/keys

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
# Use 'sandbox' to test with Plaid's Sandbox environment (username: user_good,
# password: pass_good)
# Use `development` to test with live users and credentials and `production`
# to go live
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')
# PLAID_PRODUCTS is a comma-separated list of products to use when initializing
# Link. Note that this list must contain 'assets' in order for the app to be
# able to create and retrieve asset reports.
PLAID_PRODUCTS = os.getenv('PLAID_PRODUCTS', 'transactions').split(',')

# PLAID_COUNTRY_CODES is a comma-separated list of countries for which users
# will be able to select institutions from.
PLAID_COUNTRY_CODES = os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')

connect_db(app)
db.create_all()

def empty_to_none(field):
  value = os.getenv(field)
  if value is None or len(value) == 0:
    return None
  return value


# Parameters used for the OAuth redirect Link flow.
#
# Set PLAID_REDIRECT_URI to 'http://localhost:8000/oauth-response.html'
# The OAuth redirect flow requires an endpoint on the developer's website
# that the bank website should redirect to. You will need to configure
# this redirect URI for your client ID through the Plaid developer dashboard
# at https://dashboard.plaid.com/team/api.
PLAID_REDIRECT_URI = empty_to_none('PLAID_REDIRECT_URI')

client = plaid.Client(client_id=PLAID_CLIENT_ID,
                      secret=PLAID_SECRET,
                      environment=PLAID_ENV,
                      api_version='2019-05-29')


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""
    session[CURR_USER_KEY] = user.username


@app.route('/logout')
def logout_user():
  """Logout user"""
  if CURR_USER_KEY in session:
    del session[CURR_USER_KEY]
  return redirect('/')

@app.route('/')
def join_page():
  # if CURR_USER_KEY in session:
  #   return redirect ('/transactions')
  return render_template('home.html')

@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup. """
    
    form = SignupUser()
  
    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
            )
            db.session.add(user)
            db.session.commit()
            
            username = form.username.data
            user_id = User.query.filter_by(username=username).first()
            session['user-id'] = user_id.username

            # Insert universal categories into UserCategories model
            categories = ['Utilities', 'Eating Out', 'Entertainment', 'Groceries', 'Travel', 'Insurance', 'Rent/Mortgage', 'Monthly Subscriptions', 'Vehicle', 'Income']

            for cat in categories: 
              category = Category.query.filter_by(name = cat).first()
              cat_relationship = UserCategories(user_id = user_id.username, category_id = category.id)
              db.session.add(cat_relationship)
              db.session.commit()
        
        
        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('signup.html', form=form)

        do_login(user)
        return redirect("/new-user")

    else:
        return render_template('signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login_page():
  form = LoginForm()

  if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)
        
        if user:
            do_login(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect("/transactions")

        flash("Invalid credentials.", 'danger')


  return render_template('login.html', form=form)


# Show only uncategorized transactions
@app.route('/transactions', methods=["GET", "POST"])
def signed_in_user():
  form = NewCategory()

  if form.validate_on_submit():
    try:
      data = form.name.data
      new_cat = Category(name=data.title())
      db.session.add(new_cat)
      db.session.commit()

    except IntegrityError:
      db.session.rollback()
      data = form.name.data
      new_cat_id = Category.query.filter_by(name = data.title()).first()

      new_user_cat = UserCategories(user_id = session[CURR_USER_KEY], category_id = new_cat_id.id)

      db.session.add(new_user_cat)
      db.session.commit()
      return redirect('/transactions')    

    return redirect('/transactions')

  else:
    transactions = UserTransaction.query.filter_by(user_id = session[CURR_USER_KEY]).join(Transactions, UserTransaction.transaction).filter(Transactions.category_id == None).all()

    user_categories = UserCategories.query.filter_by(user_id = session[CURR_USER_KEY]).join(Category, UserCategories.category).order_by(Category.name).all()
    
    dollar_formatted = [("{:.2f}".format(i.transaction.amount)) for i in transactions]


    return render_template('trans-details.html', form=form, user_categories = user_categories, transactions=transactions, dollar_formatted = dollar_formatted, categorized='False')

# Show all transactions (inc. categorized transactions)
@app.route('/allTransactions', methods=["GET", "POST"])
def signed_in_user_categorized():
  form = NewCategory()

  if form.validate_on_submit():
    try:
      data = form.name.data
      new_cat = Category(name=data.title())
      db.session.add(new_cat)
      db.session.commit()

    except IntegrityError:
      db.session.rollback()
      data = form.name.data
      new_cat_id = Category.query.filter_by(name = data.title()).first()

      new_user_cat = UserCategories(user_id = session[CURR_USER_KEY], category_id = new_cat_id.id)

      db.session.add(new_user_cat)
      db.session.commit()
      return redirect('/allTransactions')    

    return redirect('/allTransactions')

  else:    
    transactions = UserTransaction.query.filter_by(user_id = session[CURR_USER_KEY]).join(Transactions, UserTransaction.transaction).all()

    user_categories = UserCategories.query.filter_by(user_id = session[CURR_USER_KEY]).join(Category, UserCategories.category).order_by(Category.name).all()
    
    dollar_formatted = [("{:.2f}".format(i.transaction.amount)) for i in transactions]

    return render_template('trans-details.html', form=form, user_categories = user_categories, transactions=transactions, dollar_formatted = dollar_formatted, categorized='True')

@app.route('/new-user')
def index():
  return render_template('index.html')

# This is an endpoint defined for the OAuth flow to redirect to.
@app.route('/oauth-response.html')
def oauth_response():
  return render_template(
    'oauth-response.html',
  )

# We store the access_token in memory - in production, store it in a secure
# persistent data store.
access_token = None

# The payment_id is only relevant for the UK Payment Initiation product.
# We store the payment_id in memory - in production, store it in a secure
# persistent data store.
payment_id = None

item_id = None

@app.route('/api/info', methods=['POST'])
def info():
  global access_token
  global item_id
  return jsonify({
    'item_id': item_id,
    'access_token': access_token,
    'products': PLAID_PRODUCTS
  })

@app.route('/api/create_link_token_for_payment', methods=['POST'])
def create_link_token_for_payment():
  global payment_id
  try:
    create_recipient_response = client.PaymentInitiation.create_recipient(
      'Harry Potter',
      'GB33BUKB20201555555555',
      {
        'street':      ['4 Privet Drive'],
        'city':        'Little Whinging',
        'postal_code': '11111',
        'country':     'GB'
      },
    )
    recipient_id = create_recipient_response['recipient_id']

    create_payment_response = client.PaymentInitiation.create_payment(
      recipient_id,
      'payment_ref',
      {
        'value': 12.34,
        'currency': 'GBP'
      },
    )
    pretty_print_response(create_payment_response)
    payment_id = create_payment_response['payment_id']
    response = client.LinkToken.create(
      {
        'user': {
          # This should correspond to a unique id for the current user.
          'client_user_id': 'user-id',
        },
        'client_name': "Plaid Quickstart",
        'products': PLAID_PRODUCTS,
        'country_codes': PLAID_COUNTRY_CODES,
        'language': "en",
        'redirect_uri': PLAID_REDIRECT_URI,
        'payment_initiation': {
          'payment_id': payment_id
        }
      }
    )
    pretty_print_response(response)
    return jsonify(response)
  except plaid.errors.PlaidError as e:
    return jsonify(format_error(e))

@app.route('/api/create_link_token', methods=['POST'])
def create_link_token():
  try:
    response = client.LinkToken.create(
      {
        'user': {
          # This should correspond to a unique id for the current user.
          'client_user_id': 'user-id',
        },
        'client_name': "Plaid Quickstart",
        'products': PLAID_PRODUCTS,
        'country_codes': PLAID_COUNTRY_CODES,
        'language': "en",
        'redirect_uri': PLAID_REDIRECT_URI,
      }
    )
    pretty_print_response(response)
    return jsonify(response)
  except plaid.errors.PlaidError as e:
    return jsonify(format_error(e))

# Exchange token flow - exchange a Link public_token for
# an API access_token
# https://plaid.com/docs/#exchange-token-flow
@app.route('/api/set_access_token', methods=['POST'])
def get_access_token():
  global access_token
  global item_id
  public_token = request.form['public_token']
  try:
    exchange_response = client.Item.public_token.exchange(public_token)
  except plaid.errors.PlaidError as e:
    return jsonify(format_error(e))

  pretty_print_response(exchange_response)
  access_token = exchange_response['access_token']
  item_id = exchange_response['item_id']
  return jsonify(exchange_response)

# Retrieve Transactions for an Item
# https://plaid.com/docs/#transactions
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
  
  try:
    transaction = UserTransaction.query.filter_by(user_id = session[CURR_USER_KEY]).join(Transactions, UserTransaction.transaction).order_by(Transactions.date.desc()).first()

  except:
    transaction = None
  
  
  # If no current transactions, import all
  if not transaction:
    start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-180))
    end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-15))
  
  # Else, import only new transactions
  else: 
    most_recent = transaction.transaction.date
    end_day = int(most_recent[-1])
    start_date = f'{most_recent[:-1]}{end_day+1}'
    end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())

  try:
    transactions_response = client.Transactions.get(access_token, start_date, end_date)

    transactions = transactions_response['transactions']

    for tran in transactions:
      t = Transactions (
        transaction_id = tran['transaction_id'],
        name = tran['name'],
        amount = tran['amount'],
        date = tran['date']
      )

      db.session.add(t)
      db.session.commit()

      u_t = UserTransaction (
        user_id = session['user-id'],
        transaction_id = tran['transaction_id']
      )
      
      db.session.add(u_t)
      db.session.commit()

  except plaid.errors.PlaidError as e:
    return jsonify(format_error(e))
  
  # pretty_print_response(transactions_response)
  return jsonify(transactions_response)

#  send json back to js file
@app.route('/api/transaction-ids')
def get_transaction_ids():
  user = User.query.get(session[CURR_USER_KEY])
  transactions = user.transactions
  trans_list = [i.transaction_id for i in transactions]
  
  return jsonify(trans_list)


# Get json from JS and update DB
@app.route('/apply-categories', methods=["POST"])
def apply_categories():
  for i,j in request.json.items():
    transaction = Transactions.query.get(i)
    transaction.category_id = j
    db.session.commit()
  # flash("Transactions successfully categorized", 'success')
  resp = jsonify(success=True)
  resp.status_code=200
  return resp

@app.route('/expense-report')
def redirect_user():
  return redirect('/expense-report-year')

# Allow for year/month/all-time functionality
@app.route('/expense-report-<date>', methods=["GET","POST"])
def get_report(date):
  if date == 'year':
    date = '2020-01-01'
  elif date == 'month':
    date = '{:%Y-%m-%d}'.format(datetime.datetime.now())
    date = date[0:7] + '-01'
  else:
    date = '2000-01-01'

  not_null_transaction = UserTransaction.query.filter_by(user_id = session[CURR_USER_KEY]).join(Transactions, UserTransaction.transaction).filter(Transactions.category_id != None).filter(Transactions.date > date).all()
  
  totals = {}
  for trans in not_null_transaction:
    if trans.transaction.category.name not in totals.keys():
      totals[trans.transaction.category.name] = "{:,.2f}".format(trans.transaction.amount)
    else:
      amount = totals[trans.transaction.category.name]
      amount = amount.split(',') 
      amount = ''.join(amount)  
      total = float(amount) + trans.transaction.amount
      totals[trans.transaction.category.name] = "{:,.2f}".format(total)
    
  income = 0
  expenses = 0
  for trans in not_null_transaction:
    if trans.transaction.amount < 0:
      amount = trans.transaction.amount * -1 
      income += amount
    else:
      expenses += trans.transaction.amount
  
  income = "{:,.2f}".format(income)
  expenses = "{:,.2f}".format(expenses)
  
  return render_template('reports.html', totals=totals, income=income, expenses=expenses)

############################################
def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True))

def format_error(e):
  return {'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type, 'error_message': e.message } }

if __name__ == '__main__':
    app.run(port=os.getenv('PORT', 8000))
