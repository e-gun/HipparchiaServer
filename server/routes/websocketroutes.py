# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import asyncio
import errno
import json
import socket
import time
from urllib.request import urlopen

import websockets

from server import hipparchia
from server.startup import poll


async def wscheckpoll(websocket, path):
	"""

	note that this is a non-route in a route file: a pain to import it becuase it needs access to poll = {}

	a poll checker started by startwspolling(): the client sends the name of a poll and this will output
	the status of the poll continuously while the poll remains active

	:param websocket:
	:param path:
	:return:
	"""

	try:
		ts = await websocket.recv()
	except websockets.exceptions.ConnectionClosed:
		# you reloaded the page
		return

	while True:
		progress = {}
		try:
			progress['active'] = poll[ts].getactivity()
			progress['total'] = poll[ts].worktotal()
			progress['remaining'] = poll[ts].getremaining()
			progress['hits'] = poll[ts].gethits()
			progress['message'] = poll[ts].getstatus()
			progress['elapsed'] = poll[ts].getelapsed()
			if hipparchia.config['SUPPRESSLONGREQUESTMESSAGE'] == 'no':
				if poll[ts].getnotes():
					progress['extrainfo'] = poll[ts].getnotes()
			else:
				progress['extrainfo'] = ''
		except KeyError:
			# the poll is deleted when the query ends; you will always end up here
			progress['active'] = 'inactive'
			try:
				await websocket.send(json.dumps(progress))
			except websockets.exceptions.ConnectionClosed:
				# you reloaded the page in the middle of a search and both the poll and the socket vanished
				pass
			break
		await asyncio.sleep(.4)
		# print('progress',progress)
		try:
			await websocket.send(json.dumps(progress))
		except websockets.exceptions.ConnectionClosed:
			# websockets.exceptions.ConnectionClosed because you reloaded the page in the middle of a search
			pass

	return


@hipparchia.route('/startwspolling/<theport>', methods=['GET'])
def startwspolling(theport=hipparchia.config['PROGRESSPOLLDEFAULTPORT']):
	"""

	launch a websocket poll server

	tricky because loop.run_forever() will run forever: you can't start this when you launch HipparchiaServer without
	blocking execution of everything else; only a call via the URL mechanism will let you delagate this to an independent
	thread

	the poll is more or less eternal: the libary was coded that way, and it is kind of irritating

	startwspolling() will get called every time you reload the front page: it is at the top of documentready.js

	multiple servers on multiple ports is possible, but not yet implemented: a multi-client model is not a priority

	:param theport:
	:return:
	"""

	try:
		theport = int(theport)
	except:
		theport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	if hipparchia.config['MYEXTERNALIPADDRESS'] != '127.0.0.1':
		theip = hipparchia.config['MYEXTERNALIPADDRESS']
	else:
		theip = '127.0.0.1'

	# min/max are a very good idea since you are theoretically giving anyone anywhere the power to open a ws socket: 64k+ of them would be sad
	if hipparchia.config['PROGRESSPOLLMINPORT'] < theport < hipparchia.config['PROGRESSPOLLMAXPORT']:
		theport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	# because we are not in the main thread we cannot ask for the default loop
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	wspolling = websockets.serve(wscheckpoll, theip, port=theport, loop=loop)

	try:
		loop.run_until_complete(wspolling)
	except OSError:
		# print('websocket is already listening at',theport)
		pass

	try:
		loop.run_forever()
	finally:
		loop.run_until_complete(loop.shutdown_asyncgens())
		loop.close()

	# actually this function never returns
	print('wow: startwspolling() returned')
	return


@hipparchia.route('/confirm/<ts>')
def checkforactivesearch(ts):
	"""

	test the activity of a poll so you don't start conjuring a bunch of key errors if you use wscheckpoll() prematurely

	note that uWSGI does not look like it will ever be able to work with the polling: poll[ts].getactivity() will
	never return anything because the processing and threading of uWSGI means that the poll is not going
	to be inside the instance of HipparchiaServer that receives the confirmation request

	or something like that...

	at a minimum you can count on uWSGI giving you a KeyError when you ask for poll[ts]

	:param ts:
	:return:
	"""

	try:
		ts = str(int(ts))
	except:
		ts = str(int(time.time()))

	pollport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']
	flaskserverport = hipparchia.config['FLASKSEENATPORT']
	if hipparchia.config['MYEXTERNALIPADDRESS'] != '127.0.0.1':
		theip = hipparchia.config['MYEXTERNALIPADDRESS']
	else:
		theip = '127.0.0.1'

	theurl = 'http://{ip}:{fp}/startwspolling/{pp}'.format(ip=theip, fp=flaskserverport, pp=pollport)

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# sock.setblocking(0)
	result = sock.connect_ex((theip, pollport))
	if result == 0:
		pass
	else:
		print('websocket probe failed:',errno.errorcode[result])
		# need to fire up the websocket
		try:
			r = urlopen(theurl, data=None, timeout=.1)
		except socket.timeout:
			# socket.timeout: but our aim was to send the request, not to read the response and get blocked
			print('websocket at {p} was told to launch'.format(p=pollport))

	sock.close()
	del sock

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
				return json.dumps('nothing at '+str(pollport))
		except:
			return json.dumps('cannot_find_the_poll')
