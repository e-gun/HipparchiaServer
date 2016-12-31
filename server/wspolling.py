# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import time
import socket
from threading import Thread

import asyncio
import websockets
import warnings
import signal
from websockets.server import WebSocketServer, WebSocketServerProtocol
import datetime
import random
# from server.hipparchiaclasses import ProgressPoll
from multiprocessing import Value, Array
from contextlib import suppress


# needed for testing

class MPCounter(object):
	"""
	a counter that is mp safe
	"""
	
	def __init__(self):
		self.val = Value('i', 0)
	
	def increment(self, n=1):
		with self.val.get_lock():
			self.val.value += n
	
	@property
	def value(self):
		return self.val.value


class ProgressPoll(object):
	"""

	a dictionary of Values that can be shared between processes
	the items and their methods build a polling package for progress reporting

	general scheme:
		create the object
		set up some shareable variables
		hand them to the search functions
		report on their fate
		delete when done

	locking checks mostly unimportant: not esp worried about race conditions; most of this is simple fyi
	"""
	
	def __init__(self, timestamp):
		self.pd = {}
		self.searchid = str(timestamp)
		self.socket = 0
		
		self.pd['active'] = Value('b', False)
		self.pd['remaining'] = Value('i', -1)
		self.pd['poolofwork'] = Value('i', -1)
		self.pd['statusmessage'] = Array('c', b'')
		self.pd['hits'] = MPCounter()
		self.pd['hits'].increment(-1)
	
	def getstatus(self):
		return self.pd['statusmessage'].decode('utf-8')
	
	def getremaining(self):
		return self.pd['remaining'].value
	
	def gethits(self):
		return self.pd['hits'].value
	
	def worktotal(self):
		return self.pd['poolofwork'].value
	
	def statusis(self, statusmessage):
		self.pd['statusmessage'] = bytes(statusmessage, encoding='UTF-8')
	
	def allworkis(self, amount):
		self.pd['poolofwork'].value = amount
	
	def remain(self, remaining):
		with self.pd['remaining'].get_lock():
			self.pd['remaining'].value = remaining
	
	def sethits(self, found):
		self.pd['hits'].val.value = found
	
	def addhits(self, hits):
		self.pd['hits'].increment(hits)
	
	def activate(self):
		self.pd['active'] = True
	
	def deactivate(self):
		self.pd['active'] = False
	
	def getactivity(self):
		return self.pd['active']

# end needed for testing


class WSPoll(object):
	def __init__(self, ProgressPoll):
	
		self.pp = ProgressPoll
		self.test = True
	
	async def websocketpoll(self, websocket, path):
		loop = asyncio.get_event_loop()
		counter = 0
		while True:
			print('b')
			counter += 1
			if counter > 5:
				#break
				self.pp.statusis('closed')
				break
			s = self.pp.getstatus()
			await websocket.send(s)
			await asyncio.sleep(.3)
		
		# what follows does not in fact gracefully shut down: loop.stop() will hurl a warning at you
		# nevertheless if you don't destroy a pending task you can't break out of this function
		# it seems like websocket basically refuses to return a value and so fulfil a future
		# the API could be more helpful in this regard...
		# so the way out is 'ugly' at the moment
		print('c')
		try:
			loop.call_soon(loop.stop())
		except:
			raise StopAsyncIteration
		# print("Pending tasks at exit: %s" % asyncio.Task.all_tasks(loop))
		
		# loop.stop()
		
		# websocket.close()
		# pending = asyncio.Task.all_tasks()
		# for task in pending:
		# 	task.cancel()
		# 	try:
		# 		loop.run_until_complete(task)
		# 	except:
		# 		pass
		# try:
		# 	loop.stop()
		# except:
		# 	pass
		#
		# loop.close()
	
	def startserving(self):
		
		loop = asyncio.get_event_loop()
		print('activity',self.pp.getactivity())
		serve = websockets.serve(self.websocketpoll, '127.0.0.1', 5678)
		loop.run_until_complete(serve)
		# Blocking call which returns when the websocketpoll() coroutine is done
		loop.run_forever()
		serve.close()
		serve.wait_closed()
		pending = asyncio.Task.all_tasks()
		print('d')
		#loop.call_soon(loop.stop())
		#loop.call_soon(loop.close())
		
		for task in pending:
			print(task)
			# loop.run_until_complete(task)
		loop.close()
		
		return
	

p = ProgressPoll(1234)
p.statusis('testing 123')
p.activate()

w = WSPoll(p)

w.startserving()
print('out')


