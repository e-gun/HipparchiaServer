# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import threading
import time

from server import hipparchia
from server.startup import poll
from server.threading.websocketthread import startwspolling


@hipparchia.route('/confirm/<ts>')
def checkforactivesearch(ts):
	"""

	test the activity of a poll so you don't start conjuring a bunch of key errors if you use wscheckpoll() prematurely

	note that uWSGI does not look like it will ever be able to work with the polling: poll[ts].getactivity() will
	never return anything because the processing and threading of uWSGI means that the poll is not going
	to be available to the instance; redis, vel. sim could fix this, but that's a lot of trouble to go to

	at a minimum you can count on uWSGI giving you a KeyError when you ask for poll[ts]

	:param ts:
	:return:
	"""

	try:
		ts = str(int(ts))
	except ValueError:
		ts = str(int(time.time()))

	pollport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	active = [t.name for t in threading.enumerate()]
	if 'websocketpoll' not in active:
		pollstart = threading.Thread(target=startwspolling, name='websocketpoll', args=())
		pollstart.start()

	try:
		if poll[ts].getactivity():
			return json.dumps(pollport)
	except KeyError:
		time.sleep(.10)
		try:
			if poll[ts].getactivity():
				return json.dumps(pollport)
			else:
				print('checkforactivesearch() reports that the websocket is still inactive: there is a serious problem?')
				return json.dumps('nothing at {p}'.format(p=pollport))
		except KeyError:
			return json.dumps('cannot_find_the_poll')
