from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length


class SignupUser(FlaskForm):
    """Form for signing up new user."""

    username = StringField('Username*', validators=[DataRequired()])
    email = StringField('Email*', validators=[DataRequired(), Email()])
    password = PasswordField('Password*', validators=[Length(min=6)])

class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])

class EditUserForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])

class NewCategory(FlaskForm):
    """Form for adding category."""

    name = StringField('Add custom category', validators=[DataRequired()])