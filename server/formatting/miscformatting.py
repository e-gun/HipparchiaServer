# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time

from click import secho


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

	pollid = re.sub(r'[^a-f0-9-]', str(), searchid[:maxchars])

	if pollid != searchid:
		consolewarning('this_poll_will_never_be_found: searchid ≠ pollid ({a} ≠ {b})'.format(a=searchid, b=pollid), color='red')
		pollid = 'this_poll_will_never_be_found'

	return pollid


def consolewarning(message: str, color='yellow', isbold=False, colorcoded=True, baremessage=False):
	"""

	send color text output because something interesting happened

	:param message:
	:return:
	"""
	head = str()
	tail = str()

	template = '{head}{msg}{tail}'

	colormap = {
		'red': ('!!! ', ' !!!'),
		'yellow': ('>>> ', str()),
		'green': ('+++ ', str()),
		'cyan': ('=== ', str()),
	}

	try:
		head = colormap[color][0]
		tail = colormap[color][1]
	except KeyError:
		colorcoded = False

	if not colorcoded:
		head = '>>> '
		tail = str()

	if baremessage:
		head = str()
		tail = str()

	secho(template.format(head=head, tail=tail, msg=message), bold=isbold, fg=color)

	return
