# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-20
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField
from wtforms.validators import DataRequired


class PassUser(object):
    """

    log people into hipparchia

    """
    def __init__(self, username, password):
        self.username = username
        self.setpassword(password)

    def setpassword(self, password):
        self.pw_hash = generate_password_hash(password)

    def checkpassword(self, password):
        return check_password_hash(self.pw_hash, password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.username)  # python 3


class LoginForm(FlaskForm):
    user = StringField('username', validators=[DataRequired()])
    pw = StringField('password', validators=[DataRequired()])
