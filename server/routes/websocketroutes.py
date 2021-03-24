# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import threading
import time

from server import hipparchia
from server.formatting.miscformatting import consolewarning
from server.formatting.miscformatting import validatepollid
from server.startup import progresspolldict
from server.threading.websocketthread import startwspolling
from server.dbsupport.redisdbfunctions import establishredisconnection

JSON_STR = str


@hipparchia.route('/confirm/<searchid>')
def checkforactivesearch(searchid) -> JSON_STR:
	"""

	test the activity of a poll so you don't start conjuring a bunch of key errors if you use wscheckpoll() prematurely

	note that uWSGI does not look like it will ever be able to work with the polling: poll[ts].getactivity() will
	never return anything because the processing and threading of uWSGI means that the poll is not going
	to be available to the instance; redis, vel. sim could fix this, but that's a lot of trouble to go to

	at a minimum you can count on uWSGI giving you a KeyError when you ask for poll[ts]

	:param searchid:
	:return:
	"""

	pollid = validatepollid(searchid)

	pollport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	activethreads = [t.name for t in threading.enumerate()]
	if 'websocketpoll' not in activethreads:
		pollstart = threading.Thread(target=startwspolling, name='websocketpoll', args=())
		pollstart.start()

	if hipparchia.config['EXTERNALWSGI'] and hipparchia.config['POLLCONNECTIONTYPE'] == 'redis':
		return externalwsgipolling(pollid)

	try:
		if progresspolldict[pollid].getactivity():
			return json.dumps(pollport)
	except KeyError:
		# print('websocket checkforactivesearch() KeyError', pollid)
		time.sleep(.10)
		try:
			if progresspolldict[pollid].getactivity():
				return json.dumps(pollport)
			else:
				consolewarning('checkforactivesearch() reports that the websocket is still inactive: there is a serious problem?')
				return json.dumps('nothing at {p}'.format(p=pollport))
		except KeyError:
			return json.dumps('cannot_find_the_poll')


def externalwsgipolling(pollid) -> JSON_STR:
	"""

	polls can make it through WGSI; the real problem are the threads

	so ignore the problem...

	:param pollid:
	:return:
	"""

	time.sleep(.10)
	pollport = hipparchia.config['UWSGIPOLLPORT']

	# the following is just to get feedback when debugging...
	# keep keytypes in sync with "progresspoll.py" and RedisProgressPoll()

	# keytypes = {'launchtime': float,
	#             'portnumber': int,
	#             'active': bytes,
	#             'remaining': int,
	#             'poolofwork': int,
	#             'statusmessage': bytes,
	#             'hitcount': int,
	#             'notes': bytes}
	#
	# mykey = 'active'
	#
	# c = establishredisconnection()
	# c.set_response_callback('GET', keytypes[mykey])
	# storedkey = '{id}_{k}'.format(id=pollid, k=mykey)
	# try:
	# 	response = c.get(storedkey)
	# except TypeError:
	# 	# TypeError: cannot convert 'NoneType' object to bytes
	# 	response = b'no response'
	# print('response', response)

	return json.dumps(pollport)