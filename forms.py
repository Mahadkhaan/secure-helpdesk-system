from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length

VALID_STATUSES = [('Open', 'Open'), ('In Progress', 'In Progress'), ('Closed', 'Closed')]


class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])


class UserLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])


class AdminRegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters.')
    ])


class UserRegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters.')
    ])


class TicketForm(FlaskForm):
    title       = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[
        DataRequired(),
        Length(min=10, message='Description must be at least 10 characters.')
    ])
    # Status must be one of the three allowed values; default to Open on creation.
    status      = SelectField('Status', choices=VALID_STATUSES, default='Open')
    # Choices are populated dynamically in the route before validation.
    category_id = SelectField('Category', coerce=int)


class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[
        DataRequired(),
        Length(min=1, max=1000, message='Comment must be between 1 and 1000 characters.')
    ])
