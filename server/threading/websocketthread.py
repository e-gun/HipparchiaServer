# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import asyncio
import json

import websockets

from server import hipparchia
from server.startup import poll


async def wscheckpoll(websocket, path):
	"""

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
		progress = dict()
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

	if hipparchia.config['MYEXTERNALIPADDRESS'] != '127.0.0.1':
		theip = hipparchia.config['MYEXTERNALIPADDRESS']
	else:
		theip = '127.0.0.1'

	# because we are not in the main thread we cannot ask for the default loop
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	wspolling = websockets.serve(wscheckpoll, theip, port=theport, loop=loop)
	print('websocket at {p} opened'.format(p=theport))

	try:
		loop.run_until_complete(wspolling)
	except OSError:
		print('websocket could not be launched: port {p} is busy'.format(p=theport))
		pass

	try:
		loop.run_forever()
	finally:
		loop.run_until_complete(loop.shutdown_asyncgens())
		loop.close()

	# actually this function never returns
	print('wow: startwspolling() returned')
	return
