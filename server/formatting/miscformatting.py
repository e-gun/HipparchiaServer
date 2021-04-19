# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time
from inspect import getsourcefile
from pathlib import Path

from click import secho

from server import hipparchia
from server.commandlineoptions import getcommandlineargs

commandlineargs = getcommandlineargs()


def htmlcommentdecorator(function):
	"""

	insert html comments to flag which function generated which segment of the output

	:param function:
	:return:
	"""
	newresulttemplate = """
	<!-- {s} {f}() output begins -->
	{r}
	<!-- {s} {f}() output ends -->
	"""

	def wrapper(*args, **kwargs):
		result = function(*args, **kwargs)
		if isinstance(result, str):
			s = Path(getsourcefile(function))
			result = newresulttemplate.format(s=s.name, f=function.__name__, r=result)
		return result

	return wrapper


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

	'magenta' and 'black' are the debugging colors ATM; they are suppressed in the standard debugsettings.py

	:param message:
	:return:
	"""

	if color not in ['red', 'yellow', 'green', 'cyan', 'magenta', 'black']:
		return str()

	if color not in hipparchia.config['CONSOLEWARNINGTYPES'] and not commandlineargs.debugmessages:
		return str()

	if color == 'black':
		isbold = True

	head = str()
	tail = str()

	template = '{head}{msg}{tail}'

	colormap = {
		'red': ('!!! ', ' !!!'),
		'yellow': ('>>> ', str()),
		'green': ('+++ ', str()),
		'cyan': ('=== ', str()),
		'magenta': ('??? ', ' ???'),
		'black': ('[debugging] ', ' [debugging]'),
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


def debugmessage(message: str):
	"""

	black console warnings are debug messages...

	"""
	return consolewarning(message, color='black')
