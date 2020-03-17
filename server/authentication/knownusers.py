# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
	(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia
from server.hipparchiaobjects.authenticationobjects import PassUser


def loadusersdict(knownusersandpasswords=None):
	"""

	return the userobjects we know about

	:return:
	"""

	if not knownusersandpasswords:
		knownusersandpasswords = dict()

	userlist = [PassUser(k, knownusersandpasswords[k]) for k in knownusersandpasswords]

	if hipparchia.config['SETADEFAULTUSER']:
		defaultuser = PassUser(hipparchia.config['DEFAULTREMOTEUSER'], hipparchia.config['DEFAULTREMOTEPASS'])
		userlist.append(defaultuser)

	# anonymoususer = PassUser('Anonymous', 'NoPassword')
	# userlist.append(anonymoususer)

	usersdict = {u.username: u for u in userlist}

	return usersdict
