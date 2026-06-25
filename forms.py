import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, ValidationError

VALID_STATUSES = [('Open', 'Open'), ('In Progress', 'In Progress'), ('Closed', 'Closed')]
VALID_STATUS_VALUES = frozenset(v for v, _ in VALID_STATUSES)


def strong_password(form, field):
    """Enforce complexity: upper, lower, digit, special character."""
    p = field.data or ''
    missing = []
    if not re.search(r'[A-Z]', p):
        missing.append('one uppercase letter')
    if not re.search(r'[a-z]', p):
        missing.append('one lowercase letter')
    if not re.search(r'[0-9]', p):
        missing.append('one digit (0-9)')
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]', p):
        missing.append('one special character (!@#$%^ etc.)')
    if missing:
        raise ValidationError('Password must contain at least: ' + ', '.join(missing) + '.')


class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])


class UserLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])


class AdminRegisterForm(FlaskForm):
    username          = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email             = StringField('Email',    validators=[DataRequired(), Email()])
    password          = PasswordField('Password', validators=[
                            DataRequired(),
                            Length(min=8, message='Password must be at least 8 characters.'),
                            strong_password,
                        ])
    registration_code = StringField('Admin Registration Code', validators=[
                            DataRequired(message='Registration code is required.')
                        ])


class UserRegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
                   DataRequired(),
                   Length(min=8, message='Password must be at least 8 characters.'),
                   strong_password,
               ])


class TicketForm(FlaskForm):
    title       = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[
                      DataRequired(),
                      Length(min=10, message='Description must be at least 10 characters.')
                  ])
    status      = SelectField('Status', choices=VALID_STATUSES, default='Open')
    # Choices populated dynamically in the route before validation.
    category_id = SelectField('Category', coerce=int)


class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[
                  DataRequired(),
                  Length(min=1, max=1000, message='Comment must be between 1 and 1000 characters.')
              ])
