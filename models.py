"""Models for Budget App"""

from flask_sqlalchemy import SQLAlchemy

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


    # def serialize(self):
    #     return {
    #         'id': self.id,
    #         'flavor': self.flavor,
    #         'size': self.size,
    #         'rating': self.rating,
    #         'image': self.image
    #     }