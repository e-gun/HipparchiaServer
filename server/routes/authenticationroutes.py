# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
	(see LICENSE in the top level directory of the distribution)
"""

import json

from flask import redirect, session, url_for


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


@hipparchia.route('/attemptlogin', methods=['GET', 'POST'])
def hipparchialogin():
	# https://flask-login.readthedocs.io/en/latest/
	# http://wtforms.readthedocs.io/en/latest/crash_course.html

	users = loadusersdict()

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
			pu = users[u]
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


@hipparchia.route('/hipparchialogout', methods=['GET'])
def hipparchialogout():

	session['loggedin'] = False
	session['userid'] = 'Anonymous'

	data = json.dumps(session['userid'])

	return data


@hipparchia.route('/checkuser', methods=['GET'])
def checkuser():

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
