# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import asyncio
import json
import socket
import time
from urllib.request import urlopen

import websockets

from server import hipparchia
from server.startup import poll

"""

websockets 4.0.1 is buggy with Firefox 57
works but you will see the following

Error in data transfer
Traceback (most recent call last):
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/websockets/protocol.py", line 496, in transfer_data
    msg = yield from self.read_message()
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/websockets/protocol.py", line 526, in read_message
    frame = yield from self.read_data_frame(max_size=self.max_size)
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/websockets/protocol.py", line 591, in read_data_frame
    frame = yield from self.read_frame(max_size)
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/websockets/protocol.py", line 632, in read_frame
    extensions=self.extensions,
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/websockets/framing.py", line 100, in read
    data = yield from reader(2)
  File "/usr/local/Cellar/python3/3.6.3/Frameworks/Python.framework/Versions/3.6/lib/python3.6/asyncio/streams.py", line 668, in readexactly
    yield from self._wait_for_data('readexactly')
  File "/usr/local/Cellar/python3/3.6.3/Frameworks/Python.framework/Versions/3.6/lib/python3.6/asyncio/streams.py", line 458, in _wait_for_data
    yield from self._waiter
  File "/usr/local/Cellar/python3/3.6.3/Frameworks/Python.framework/Versions/3.6/lib/python3.6/asyncio/selector_events.py", line 724, in _read_ready
    data = self._sock.recv(self.max_size)
ConnectionResetError: [Errno 54] Connection reset by peer

current remedy:
	pip install -Iv websockets==3.4

"""

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
	except ValueError:
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
	to be available to the instance; redis, vel. sim could fix this, but that's a lot of trouble to go to

	at a minimum you can count on uWSGI giving you a KeyError when you ask for poll[ts]

	you must comply with RFC 6455 or you will get 'websockets.exceptions.InvalidHandshake', etc. from websockets

	sample exchange with websockets' http.py

		websocket at 5010 opened
		127.0.0.1 - - [06/Sep/2017 15:12:55] "GET /confirm/1504725175310 HTTP/1.1" 200 -
		read_line(): b'GET / HTTP/1.1\r\n'
		read_line(): b'Host: localhost:5010\r\n'
		read_line(): b'Connection: Upgrade\r\n'
		read_line(): b'Pragma: no-cache\r\n'
		read_line(): b'Cache-Control: no-cache\r\n'
		read_line(): b'Upgrade: websocket\r\n'
		read_line(): b'Origin: http://localhost:5000\r\n'
		read_line(): b'Sec-WebSocket-Version: 13\r\n'
		read_line(): b'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36\r\n'
		read_line(): b'DNT: 1\r\n'
		read_line(): b'Accept-Encoding: gzip, deflate, br\r\n'
		read_line(): b'Accept-Language: en-US,en;q=0.8\r\n'
		read_line(): b'Cookie: session=.eJxtk01v2zAMhv-LzhmQDusw5Nb7jrsNRaHIrE1YJh1Sqm0U_e-lnG87Rz1-9JokqE_na4IxxKzIpG73_3VTkEKEkG5Q5LDSjK28vLLy2kkNi2ruOi-T27kJ1Bn-8Bj9PoLbfbpaANq3Cud7s5Ukw-bEI9jV5O9hx9I3HLm-yNEnpAchR74IOcJ1yMBSBc6U9G17ZF8btxcfWkie6gjVpYMTDVnitIRiEcUkvjI9ZC9wY_KgIIEpwZgM_9waDY2gJvQUrLSs5wjwEhE0VT6VhB9_nos8T-IiHmMb8FVpAqmCEak-JyAFkNL_yZu_76d3gUMGCtPV0yDYlxnel2ATuxbw9LzdutMUFxoSKL9f2vq1cZ0fBTTHVKTf80WyhliIS9__7MwEDaZzRu_7SbLeB_fCI3aYSqVP5az1cvkMLbfvkNnKXuye2t9DY_l96eXvTOwNrDSWZJMEMaK2w4l8B4X3WfA6yQ9_exraZVVDu35zhS1LHdoVefAMhwfPcOxQi2JFvNDkvr4BWbtfzg.DJHUoA.Je_KZJQ0LY1Z6iFuJZU7iNTRfgU\r\n'
		read_line(): b'Sec-WebSocket-Key: gqDCHf/EPrL5rrU43t1yVg==\r\n'
		read_line(): b'Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits\r\n'
		read_line(): b'\r\n'

	from RFC 6455:
	The request MUST include a header field with the name
		|Sec-WebSocket-Key|.  The value of this header field MUST be a
		nonce consisting of a randomly selected 16-byte value that has
		been base64-encoded (see Section 4 of [RFC4648]).  The nonce
		MUST be selected randomly for each connection.

	:param ts:
	:return:
	"""

	try:
		ts = str(int(ts))
	except ValueError:
		ts = str(int(time.time()))

	pollport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']
	flaskserverport = hipparchia.config['FLASKSEENATPORT']
	if hipparchia.config['MYEXTERNALIPADDRESS'] != '127.0.0.1':
		theip = hipparchia.config['MYEXTERNALIPADDRESS']
	else:
		theip = '127.0.0.1'

	theurl = 'http://{ip}:{fp}/startwspolling/{pp}'.format(ip=theip, fp=flaskserverport, pp=pollport)

	handshake = list()
	handshake.append('GET / HTTP/1.1\r\n')
	handshake.append('Host: {ip}:{pp}\r\n')
	handshake.append('Connection: Upgrade\r\n')
	handshake.append('Upgrade: websocket\r\n')
	handshake.append('Origin: self_probe\r\n')
	handshake.append('Sec-WebSocket-Key: {k}\r\n')
	handshake.append('Sec-WebSocket-Version: 13\r\n')
	handshake.append('\r\n')
	handshake = ''.join(handshake)
	# oddly the next does not work (but hard-coding a random example is ok for our purposes)
	# key = b64encode(urandom(16))
	key = 'GwPND1CD9u2Sf3lnsNwRnw=='
	handshake = handshake.format(ip=theip, pp=flaskserverport, k=key)
	handshake = handshake.encode(encoding='UTF-8')

	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		try:
			s.connect((theip, pollport))
			s.sendall(handshake)
		except ConnectionRefusedError:
			# need to fire up the websocket
			try:
				response = urlopen(theurl, data=None, timeout=.1)
			except socket.timeout:
				# socket.timeout: but our aim was to send the request, not to read the response and get blocked
				# so we want to throw this exception so that we can eventually get to one of the 'returns'
				print('websocket at {p} opened'.format(p=pollport))

	s.close()
	del s

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
		except KeyError:
			return json.dumps('cannot_find_the_poll')
