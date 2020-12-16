"""Models for Budget App"""

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()

def connect_db(app):
    db.app = app
    db.init_app(app)


class Transactions(db.Model):
    """Transactions model"""

    __tablename__ = 'transactions'

    transaction_id = db.Column(db.Text, primary_key = True)
    name = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Text, nullable=False)
    category = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    users = db.relationship("User", secondary="user_transactions")


class Category(db.Model):
    """category Model"""

    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, unique = True)

class User(db.Model):
    """User model"""

    __tablename__ = 'users'

    username = db.Column(db.String(25), primary_key=True, unique=True, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)

    # TODO: Finish this, and impliment it on trans-details.html 
    transactions = db.relationship("Transactions", secondary="user_transactions")

    @classmethod
    def signup(cls, username, email, password):
        """Sign up user. Hashes password and adds user to system."""

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`."""

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False
     
# TODO: remove underscore
class UserTransaction(db.Model):
    """User transactions model"""

    __tablename__ = 'user_transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Text, db.ForeignKey('users.username'), nullable=False)
    transaction_id = db.Column(db.Text, db.ForeignKey('transactions.transaction_id'), nullable=False)

    user = db.relationship(User, backref=db.backref("user_transactions", cascade="all, delete-orphan"))
    transaction = db.relationship(Transactions, backref=db.backref("user_transactions", cascade="all, delete-orphan"))
    
    
