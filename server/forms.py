from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired

class SearchForm(Form):
    seeking = StringField('seeking', validators=[DataRequired()])
