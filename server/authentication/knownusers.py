# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
	(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia
from server.hipparchiaobjects.authenticationobjects import PassUser
from server.formatting.miscformatting import consolewarning
from server.dbsupport.tablefunctions import assignuniquename


def loadusersdict(knownusersandpasswords=None):
	"""

	return the userobjects we know about

	note that this is effectively empty: no dict of users is being passed ATM

	anyone with ambitions re. a collection of users should insert them via securitysettings.py

		KNOWNUSERSDICT = {'user1': 'pass1, 'user2': 'pass2'}

	elaborate user and authentication schemes are a non-priority (as is encryption...)

	:return:
	"""

	userlist = list()

	if not knownusersandpasswords and hipparchia.config['KNOWNUSERSDICT']:
		knownusersandpasswords = hipparchia.config['KNOWNUSERSDICT']
		userlist = [PassUser(k, knownusersandpasswords[k]) for k in knownusersandpasswords]

	if hipparchia.config['SETADEFAULTUSER']:
		thepass = hipparchia.config['DEFAULTREMOTEPASS']
		if thepass == 'yourremoteuserpassheretrytomakeitstrongplease':
			thepass = assignuniquename()
			consolewarning('DEFAULTREMOTEPASS cannot be left as "yourremoteuserpassheretrytomakeitstrongplease"')
			consolewarning('temporary one-time password is "{p}"'.format(p=thepass))
		defaultuser = PassUser(hipparchia.config['DEFAULTREMOTEUSER'], thepass)
		userlist.append(defaultuser)

	# anonymoususer = PassUser('Anonymous', 'NoPassword')
	# userlist.append(anonymoususer)

	usersdict = {u.username: u for u in userlist}

	return usersdict
