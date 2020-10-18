# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import asyncio
import json
import re

import websockets

from server import hipparchia
from server.formatting.miscformatting import consolewarning
from server.formatting.miscformatting import validatepollid
from server.startup import progresspolldict


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
			progress['total'] = progresspolldict[pollid].worktotal()
			progress['remaining'] = progresspolldict[pollid].getremaining()
			progress['hits'] = progresspolldict[pollid].gethits()
			progress['message'] = progresspolldict[pollid].getstatus()
			progress['elapsed'] = progresspolldict[pollid].getelapsed()
			if not hipparchia.config['SUPPRESSLONGREQUESTMESSAGE']:
				if progresspolldict[pollid].getnotes():
					progress['extrainfo'] = progresspolldict[pollid].getnotes()
			else:
				progress['extrainfo'] = str()
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


def startwspolling(theport=hipparchia.config['PROGRESSPOLLDEFAULTPORT']):
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
		consolewarning('websocket could not be launched: cannot get access to {i}:{p}'.format(p=theport, i=theip), color='red')
		pass

	try:
		loop.run_forever()
	finally:
		loop.run_until_complete(loop.shutdown_asyncgens())
		loop.close()

	# actually this function never returns
	consolewarning('wow: startwspolling() returned')
	return
