# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time

from sys import platform

from click import secho


def attemptcolorprint(*args, **kwargs):
	"""

	windows does odd things with the startup notifications: will not mix and match print and secho; instead you get
	all the secho's and then all the prints (although this is out of order of execution)

	:param args:
	:param kwargs:
	:return:
	"""
	if platform is not 'win32':
		secho(*args, **kwargs)
	else:
		print(*args)


def timedecorator(function):
	"""

	how long did the function take to execute?

	:param function:
	:return:
	"""

	launchtime = time.time()

	def wrapper(*args, **kwargs):
		result = function(*args, **kwargs)
		elapsed = round(time.time() - launchtime, 1)
		secho(' ({e}s)'.format(e=elapsed), fg='red')
		return result

	return wrapper


def validatepollid(searchid, maxchars=36) -> str:
	"""

	make sure the pollid is legit

	r'[^a-f0-9-]' allows for hex + '-'; i.e., a uuid formatted string

	UUIDs are 36 characters long

	the real question is what code is active in documentready.js and indexandtextmaker.js
		either:
			let searchid = generateId(8);
		or:
			let searchid = uuidv4();

	:param searchid:
	:return:
	"""

	pollid = re.sub(r'[^a-f0-9-]', '', searchid[:maxchars])

	if pollid != searchid:
		print('this_poll_will_never_be_found: searchid ≠ pollid ({a} ≠ {b})'.format(a=searchid, b=pollid))
		pollid = 'this_poll_will_never_be_found'

	return pollid
