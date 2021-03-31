# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
	(see LICENSE in the top level directory of the distribution)
"""

from typing import TypeVar

import json

from flask import redirect, session, url_for
from flask import Response as FlaskResponse


from server import hipparchia
from server.formatting.miscformatting import consolewarning
from server.authentication.knownusers import loadusersdict
from server.hipparchiaobjects.authenticationobjects import LoginForm, PassUser

try:
	from flask_login import LoginManager
	loginmanager = LoginManager()
	loginmanager.init_app(hipparchia)

	@loginmanager.user_loader
	def loaduser(uid):
		return PassUser.getid(uid)

except ModuleNotFoundError:
	if hipparchia.config['LIMITACCESSTOLOGGEDINUSERS']:
		hipparchia.config['LIMITACCESSTOLOGGEDINUSERS'] = False
		consolewarning('flask_login not found: install via "~/hipparchia_venv/bin/pip install flask_login"', color='red')
		consolewarning('forcibly setting LIMITACCESSTOLOGGEDINUSERS to False', color='red')

	def loaduser(uid):
		return 'Anonymous'

JSON_STR = str
JSON_OR_RESPONSE = TypeVar('JSON_OR_RESPONSE', JSON_STR, FlaskResponse)

hipparchiausers = loadusersdict()


@hipparchia.route('/authentication/<action>', methods=['GET', 'POST'])
def authenticationactions(action: str) -> JSON_OR_RESPONSE:
	"""

	dispatcher for "/authenticate/..." requests

	"""

	knownfunctions = {'attemptlogin':
							{'fnc': hipparchialogin, 'param': None},
						'logout':
							{'fnc': hipparchialogout, 'param': None},
						'checkuser':
							{'fnc': checkuser, 'param': None},
						}

	if action not in knownfunctions:
		return json.dumps(str())

	f = knownfunctions[action]['fnc']
	p = knownfunctions[action]['param']

	if p:
		j = f(*p)
	else:
		j = f()

	if hipparchia.config['JSONDEBUGMODE']:
		print('/authenticate/{f}\n\t{j}'.format(f=action, j=j))

	return j


def hipparchialogin() -> FlaskResponse:
	""""

	log the user in

	"""
	# https://flask-login.readthedocs.io/en/latest/
	# http://wtforms.readthedocs.io/en/latest/crash_course.html

	returndata = dict()
	p = str()

	form = LoginForm()

	session['loggedin'] = False
	session['userid'] = 'Anonymous'

	pu = None

	if form.validate_on_submit():
		u = form.user.data
		p = form.pw.data
		try:
			pu = hipparchiausers[u]
		except KeyError:
			pass
	else:
		print(form.errors)

	if pu and pu.checkpassword(p):
		session['loggedin'] = True
		session['userid'] = loaduser(pu)

	returndata['user'] = session['userid']
	returndata['authenticated'] = None

	if session['loggedin']:
		returndata['authenticated'] = 'success'

	# unused ATM
	data = json.dumps(returndata)

	return redirect(url_for('frontpage'))


def hipparchialogout() -> JSON_STR:
	"""

	log the user out

	"""

	session['loggedin'] = False
	session['userid'] = 'Anonymous'

	data = json.dumps(session['userid'])

	return data


def checkuser() -> JSON_STR:
	"""

	is the user logged in?

	"""

	returndata = dict()
	try:
		returndata['userid'] = session['userid']
		returndata['loggedin'] = session['loggedin']
	except KeyError:
		session['loggedin'] = False
		session['userid'] = 'Anonymous'
		returndata['userid'] = session['userid']
		returndata['loggedin'] = session['loggedin']

	data = json.dumps(returndata)

	return data
