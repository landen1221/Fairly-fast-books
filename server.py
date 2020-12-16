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
from models import db, connect_db, Transactions, UserTransaction, User, Category
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from forms import SignupUser, LoginForm, EditUserForm, NewCategory
# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
CURR_USER_KEY = "curr_user"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///plaid_db'
app.config['SECRET_KEY'] = "plaidSandbox"

# Fill in your Plaid API keys - https://dashboard.plaid.com/account/keys
PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID', '5fd2b9d7284fbe00120a1d93')
PLAID_SECRET = os.getenv('PLAID_SECRET', 'e2378e768e4862e413091800c2f592')
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
            return redirect("/home")

        flash("Invalid credentials.", 'danger')


  return render_template('login.html', form=form)

# TODO: Render transaction table
@app.route('/home', methods=["GET", "POST"])
def signed_in_user():
  form = NewCategory()

  if form.validate_on_submit():
    print(form.name.data)
    try:
      data = form.name.data
      new_cat = Category(name=data.title())
      db.session.add(new_cat)
      db.session.commit()

    except IntegrityError:
      flash("Category already exists", 'danger')
      return redirect('/home')
    
    return redirect('/home')

  else:
    user = User.query.get(session[CURR_USER_KEY])
    categories = Category.query.all()
    
    dollar_formatted = [("{:.2f}".format(i.amount)) for i in user.transactions]
    length = len(dollar_formatted)

    return render_template('trans-details.html', user=user, categories=categories, dollar_formatted=dollar_formatted, length=length, form=form)



@app.route('/new-user')
def index():
  return render_template('index.html')

# This is an endpoint defined for the OAuth flow to redirect to.
@app.route('/oauth-response.html')
def oauth_response():
  return render_template(
    'oauth-response.html',
  )

# TODO: store this in session?
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

# Retrieve ACH or ETF account numbers for an Item
# https://plaid.com/docs/#auth
@app.route('/api/auth', methods=['GET'])
def get_auth():
  try:
    auth_response = client.Auth.get(access_token)
  except plaid.errors.PlaidError as e:
    return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(auth_response)
  return jsonify(auth_response)

# Retrieve Transactions for an Item
# https://plaid.com/docs/#transactions
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
  # Pull transactions for the last 30 days
  start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-120))
  end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())
  try:
    transactions_response = client.Transactions.get(access_token, start_date, end_date)

    # TODO:
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
  
  pretty_print_response(transactions_response)
  return jsonify(transactions_response)

#  TODO: send json back to js file
@app.route('/api/transaction-ids')
def get_transaction_ids():
  user = User.query.get(session[CURR_USER_KEY])
  transactions = user.transactions
  trans_list = [i.transaction_id for i in transactions]
  
  return jsonify(trans_list)

# Retrieve Identity data for an Item
# https://plaid.com/docs/#identity
@app.route('/api/identity', methods=['GET'])
def get_identity():
  try:
    identity_response = client.Identity.get(access_token)
  except plaid.errors.PlaidError as e:
    return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(identity_response)
  return jsonify({'error': None, 'identity': identity_response['accounts']})

# Retrieve real-time balance data for each of an Item's accounts
# https://plaid.com/docs/#balance
@app.route('/api/balance', methods=['GET'])
def get_balance():
  try:
    balance_response = client.Accounts.balance.get(access_token)
  except plaid.errors.PlaidError as e:
    return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(balance_response)
  return jsonify(balance_response)

# Retrieve an Item's accounts
# https://plaid.com/docs/#accounts
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
  try:
    accounts_response = client.Accounts.get(access_token)
  except plaid.errors.PlaidError as e:
    return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(accounts_response)
  return jsonify(accounts_response)

# Create and then retrieve an Asset Report for one or more Items. Note that an
# Asset Report can contain up to 100 items, but for simplicity we're only
# including one Item here.
# https://plaid.com/docs/#assets
@app.route('/api/assets', methods=['GET'])
def get_assets():
  try:
    asset_report_create_response = client.AssetReport.create([access_token], 10)
  except plaid.errors.PlaidError as e:
    return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
  pretty_print_response(asset_report_create_response)

  asset_report_token = asset_report_create_response['asset_report_token']

  # Poll for the completion of the Asset Report.
  num_retries_remaining = 20
  asset_report_json = None
  while num_retries_remaining > 0:
    try:
      asset_report_get_response = client.AssetReport.get(asset_report_token)
      asset_report_json = asset_report_get_response['report']
      break
    except plaid.errors.PlaidError as e:
      if e.code == 'PRODUCT_NOT_READY':
        num_retries_remaining -= 1
        time.sleep(1)
        continue
      return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })

  if asset_report_json == None:
    return jsonify({'error': {'display_message': 'Timed out when polling for Asset Report', 'error_code': '', 'error_type': '' } })

  asset_report_pdf = None
  try:
    asset_report_pdf = client.AssetReport.get_pdf(asset_report_token)
  except plaid.errors.PlaidError as e:
    return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })

  return jsonify({
    'error': None,
    'json': asset_report_json,
    'pdf': base64.b64encode(asset_report_pdf).decode('utf-8'),
  })

# Retrieve investment holdings data for an Item
# https://plaid.com/docs/#investments
# @app.route('/api/holdings', methods=['GET'])
# def get_holdings():
#   try:
#     holdings_response = client.Holdings.get(access_token)
#   except plaid.errors.PlaidError as e:
#     return jsonify({'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type } })
#   pretty_print_response(holdings_response)
#   return jsonify({'error': None, 'holdings': holdings_response})

# Retrieve Investment Transactions for an Item
# https://plaid.com/docs/#investments
# @app.route('/api/investment_transactions', methods=['GET'])
# def get_investment_transactions():
#   # Pull transactions for the last 30 days
#   start_date = '{:%Y-%m-%d}'.format(datetime.datetime.now() + datetime.timedelta(-30))
#   end_date = '{:%Y-%m-%d}'.format(datetime.datetime.now())
#   try:
#     investment_transactions_response = client.InvestmentTransactions.get(access_token,
#                                                                          start_date,
#                                                                          end_date)
#   except plaid.errors.PlaidError as e:
#     return jsonify(format_error(e))
#   pretty_print_response(investment_transactions_response)
#   return jsonify({'error': None, 'investment_transactions': investment_transactions_response})

# This functionality is only relevant for the UK Payment Initiation product.
# Retrieve Payment for a specified Payment ID
# @app.route('/api/payment', methods=['GET'])
# def payment():
#   global payment_id
#   payment_get_response = client.PaymentInitiation.get_payment(payment_id)
#   pretty_print_response(payment_get_response)
#   return jsonify({'error': None, 'payment': payment_get_response})

# Retrieve high-level information about an Item
# https://plaid.com/docs/#retrieve-item
@app.route('/api/item', methods=['GET'])
def item():
  global access_token
  item_response = client.Item.get(access_token)
  institution_response = client.Institutions.get_by_id(item_response['item']['institution_id'])
  pretty_print_response(item_response)
  pretty_print_response(institution_response)
  return jsonify({'error': None, 'item': item_response['item'], 'institution': institution_response['institution']})

def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True))

def format_error(e):
  return {'error': {'display_message': e.display_message, 'error_code': e.code, 'error_type': e.type, 'error_message': e.message } }

if __name__ == '__main__':
    app.run(port=os.getenv('PORT', 8000))
