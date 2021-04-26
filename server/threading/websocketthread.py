# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import asyncio
import json
import re
import subprocess
import websockets
import threading

from os import path

from server import hipparchia
from server.formatting.miscformatting import consolewarning, debugmessage
from server.formatting.miscformatting import validatepollid
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.startup import progresspolldict

gosearch = None
try:
	from server.golangmodule import hipparchiagolangsearching as gosearch
except ImportError:
	pass


failurestring = '{f} returned: this is not supposed to happen. Polling must be broken'


class WebSocketCheckBorg(object):
	"""

	a borg to hold a permanent value

	"""
	_sockethasbeenactivated = False

	def __init__(self):
		pass

	def setasactive(self):
		WebSocketCheckBorg._sockethasbeenactivated = True

	def checkifactive(self):
		return WebSocketCheckBorg._sockethasbeenactivated


def checkforlivewebsocket():
	"""

	only turn on the websockets once

	"""
	b = WebSocketCheckBorg()
	if not b.checkifactive():
		pollstart = threading.Thread(target=startwspolling, name='websocketpoll', args=())
		pollstart.start()
		b.setasactive()
	else:
		# debugmessage('websockets have already been activated')
		pass
	return


def startwspolling(theport=None):
	"""

	you need a websocket poll server

	pick between python and golang as a delivery medium

	"""

	if not theport:
		theport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	if not gosearch:
		debugmessage('websockets are to be provided via the python socket server')
		startpythonwspolling(theport)

	if hipparchia.config['GOLANGPROVIDESWEBSOCKETS']:
		debugmessage('websockets are to be provided via the golang socket server')
		startgolangwebsocketserver(theport)
		return

	if hipparchia.config['GOLANGLOADING'] != 'cli':
		debugmessage('websockets are to be provided via the golang socket server')
		startgolangwebsocketserver(theport)
		return

	startpythonwspolling(theport)

	# actually this function never returns
	consolewarning(failurestring.format(f='startwspolling()'), color='red')
	return


def startgolangwebsocketserver(theport):
	"""

	use the golang websocket server

	it locks if you try to use it as a module; so we will invoke it via a binary

	you can probably just run it without arguments since the build defaults are the same
	as the defaults in the configuration files for HipparchiaServer

	nevertheless, we will be doing this the tedious way...

	Usage of ./WebSocketApp:
	  -l int
			logging level: 0 is silent; 2 is very noisy
	  -p int
			port on which to open the websocket server (default 5010)
	  -r string
			redis logon information (as a JSON string) (default "{\"Addr\": \"localhost:6379\", \"Password\": \"\", \"DB\": 0}")
	  -t int
			fail threshold before messages stop being sent (default 5)

	"""

	if not hipparchia.config['EXTERNALWSGI']:
		basepath = path.dirname(__file__)
		basepath = '/'.join(basepath.split('/')[:-2])
	else:
		# path.dirname(argv[0]) = /home/hipparchia/hipparchia_venv/bin
		basepath = path.abspath(hipparchia.config['HARDCODEDPATH'])

	binary = '/server/golangmodule/WebSocketApp'
	command = basepath + binary

	arguments = dict()

	rld = {'Addr': '{a}:{b}'.format(a=hipparchia.config['REDISHOST'], b=hipparchia.config['REDISPORT']),
		   'Password': str(),
		   'DB': hipparchia.config['REDISDBID']}
	arguments['r'] = json.dumps(rld)
	arguments['l'] = hipparchia.config['GOLANGWSSLOGLEVEL']
	arguments['p'] = theport
	# arguments['t'] = 5
	argumentlist = [['-{k}'.format(k=k), '{v}'.format(v=arguments[k])] for k in arguments]
	argumentlist = flattenlistoflists(argumentlist)
	commandandarguments = [command] + argumentlist

	subprocess.Popen(commandandarguments)
	debugmessage('successfully opened {b}'.format(b=binary))

	return


def startpythonwspolling(theport):
	"""

	launch a websocket poll server

	tricky because loop.run_forever() will run forever: requires threading

	the poll is more or less eternal: the libary was coded that way, and it is kind of irritating

	multiple servers on multiple ports is possible, but not yet implemented: a multi-client model is not a priority

	:param theport:
	:return:
	"""

	try:
		theport = int(theport)
	except ValueError:
		theport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	theip = hipparchia.config['MYEXTERNALIPADDRESS']

	# because we are not in the main thread we cannot ask for the default loop
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	wspolling = websockets.serve(wscheckpoll, theip, port=theport, loop=loop)
	consolewarning('opening websocket at {p}'.format(p=theport), color='cyan', isbold=False)

	try:
		loop.run_until_complete(wspolling)
	except OSError:
		consolewarning('websocket could not be launched: cannot get access to {i}:{p}'.format(p=theport, i=theip),
					   color='red')
		pass

	try:
		loop.run_forever()
	finally:
		loop.run_until_complete(loop.shutdown_asyncgens())
		loop.close()

	# actually this function never returns
	consolewarning(failurestring.format(f='startpythonwspolling()'), color='red')
	return


async def wscheckpoll(websocket, path):
	"""

	a poll checker started by startwspolling(): the client sends the name of a poll and this will output
	the status of the poll continuously while the poll remains active

	example:
		progress {'active': 1, 'total': 20, 'remaining': 20, 'hits': 48, 'message': 'Putting the results in context', 'elapsed': 14.0, 'extrainfo': '<span class="small"></span>'}

	:param websocket:
	:param path:
	:return:
	"""

	try:
		pollid = await websocket.recv()
	except websockets.exceptions.ConnectionClosed:
		# you reloaded the page
		return

	# comes to us with quotes: "eb91fb11" --> eb91fb11
	pollid = re.sub(r'"', str(), pollid)
	pollid = validatepollid(pollid)

	while True:
		progress = dict()
		try:
			active = progresspolldict[pollid].getactivity()
			progress['poolofwork'] = progresspolldict[pollid].worktotal()
			progress['remaining'] = progresspolldict[pollid].getremaining()
			progress['hitcount'] = progresspolldict[pollid].gethits()
			progress['statusmessage'] = progresspolldict[pollid].getstatus()
			progress['launchtime'] = progresspolldict[pollid].getlaunchtime()
			if not hipparchia.config['SUPPRESSLONGREQUESTMESSAGE']:
				if progresspolldict[pollid].getnotes():
					progress['notes'] = progresspolldict[pollid].getnotes()
			else:
				progress['notes'] = str()
		except KeyError:
			# the poll key is deleted from progresspolldict when the query ends; you will always end up here
			progress['active'] = 'inactive'
			try:
				await websocket.send(json.dumps(progress))
			except websockets.exceptions.ConnectionClosed:
				# you reloaded the page in the middle of a search and both the poll and the socket vanished
				pass
			break

		await asyncio.sleep(.4)
		# print('progress %', ((progress['total'] - progress['remaining']) / progress['total']) * 100)

		try:
			# something changed amid backend updates and json.dumps() started choking on progresspolldict[pollid].getactivity()
			# active is (now) a <Synchronized wrapper for c_byte(1)>; that was the unexpected change: it was 'bool'
			# <class 'multiprocessing.sharedctypes.Synchronized'>
			progress['active'] = active.value
		except AttributeError:
			# AttributeError: 'str' (or 'int' or 'bool') object has no attribute 'value'
			progress['active'] = active

		try:
			await websocket.send(json.dumps(progress))
		except websockets.exceptions.ConnectionClosed:
			# websockets.exceptions.ConnectionClosed because you reloaded the page in the middle of a search
			pass
		except TypeError as e:
			# "Object of type Synchronized is not JSON serializable"
			# macOS and indexmaker combo is a problem; macOS is the real problem?
			consolewarning('websocket non-fatal error: "{e}"'.format(e=e), color='yellow', isbold=False)
			pass
	return
