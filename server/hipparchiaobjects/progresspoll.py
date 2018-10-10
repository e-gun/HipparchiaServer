# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
import time
from multiprocessing import Array, Value

from server import hipparchia
from server.dbsupport.redisdbfunctions import establishredisconnection
from server.hipparchiaobjects.helperobjects import MPCounter


class SharedMemoryProgressPoll(object):
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

	polltcpport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	def __init__(self, searchid, portnumber=polltcpport):
		self.searchid = str(searchid)
		self.launchtime = time.time()
		self.portnumber = portnumber
		self.active = Value('b', False)
		self.remaining = Value('i', -1)
		self.poolofwork = Value('i', -1)
		self.statusmessage = Array('c', b'')
		self.hitcount = MPCounter()
		self.hitcount.increment(-1)
		self.notes = ''
		self.polltype = 'SharedMemoryProgressPoll'
		# print('SharedMemoryProgressPoll()', self.searchid)

	def getstatus(self):
		return self.statusmessage.decode('utf-8')

	def getelapsed(self):
		elapsed = round(time.time() - self.launchtime, 0)
		return elapsed

	def getremaining(self):
		return self.remaining.value

	def gethits(self):
		return self.hitcount.value

	def worktotal(self):
		return self.poolofwork.value

	def statusis(self, statusmessage):
		self.statusmessage = bytes(statusmessage, encoding='UTF-8')

	def allworkis(self, amount):
		self.poolofwork.value = amount

	def remain(self, remaining):
		with self.remaining.get_lock():
			self.remaining.value = remaining

	def sethits(self, found):
		self.hitcount.val.value = found

	def addhits(self, hits):
		self.hitcount.increment(hits)

	def activate(self):
		self.active = True

	def deactivate(self):
		self.active = False

	def getactivity(self):
		return self.active

	def setnotes(self, message):
		self.notes = message

	def getnotes(self):
		message = '<span class="small">{msg}</span>'
		if 14 < self.getelapsed() < 21:
			m = '(long requests can be aborted by reloading the page)'
		elif re.search('unavailable', self.notes) and 7 < self.getelapsed() < 15:
			m = self.notes
		elif re.search('unavailable', self.notes) is None:
			m = self.notes
		else:
			m = ''

		return message.format(msg=m)


class RedisProgressPoll(object):
	"""

	a dictionary of Values that can be shared between processes
	the items and their methods build a polling package for progress reporting

	general scheme:
		create the object
		set up some shareable variables
		hand them to the search functions
		report on their fate
		delete when done

	the interface is rather baroque because the underlying simple mechanism was late in arriving

	HSET is tempting instead of SET...

	note that you should not request things like self.poolofwork: it will not be accurate after initialization
		self.worktotal(), etc. are how you get the real values

	"""

	polltcpport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	def __init__(self, searchid, pollservedfromportnumber=polltcpport):
		self.searchid = str(searchid)
		self.launchtime = time.time()
		self.portnumber = pollservedfromportnumber
		self.active = False
		self.remaining = -1
		self.poolofwork = -1
		self.statusmessage = str()
		self.hitcount = -1
		self.notes = str()
		self.keytypes = self.setkeytypes()
		self.polltype = 'RedisProgressPoll'
		self.redisconnection = establishredisconnection()
		self.initializeredispoll()

	def __del__(self):
		if hipparchia.config['RETAINREDISPOLLS'] != 'yes':
			self.deleteredispoll()

	def setkeytypes(self):
		keytypes = {'launchtime': float,
		            'portnumber': int,
		            'active': bool,
		            'remaining': int,
		            'poolofwork': int,
		            'statusmessage': bytes,
		            'hitcount': int,
		            'notes': bytes}

		return keytypes

	def initializeredispoll(self):
		for k in self.keytypes:
			rediskey = self.returnrediskey(k)
			redisvalue = getattr(self, k)
			self.redisconnection.set(rediskey, redisvalue)

	def deleteredispoll(self):
		for k in self.keytypes:
			rediskey = self.returnrediskey(k)
			self.redisconnection.delete(rediskey)

	def returnrediskey(self, keyname):
		return '{id}_{k}'.format(id=self.searchid, k=keyname)

	def setredisvalue(self, key, value):
		k = self.returnrediskey(key)
		# print('setredisvalue({k}): {v}'.format(k=k, v=value))
		self.redisconnection.set(k, value)

	def getredisvalue(self, key):
		self.redisconnection.set_response_callback('GET', self.keytypes[key])
		k = self.returnrediskey(key)
		return self.redisconnection.get(k)

	def getstatus(self):
		m = self.getredisvalue('statusmessage')
		return m.decode('utf-8')

	def getelapsed(self):
		launch = self.getredisvalue('launchtime')
		elapsed = round(time.time() - launch, 0)
		return elapsed

	def getremaining(self):
		return self.getredisvalue('remaining')

	def gethits(self):
		return self.getredisvalue('hitcount')

	def worktotal(self):
		return self.getredisvalue('poolofwork')

	def statusis(self, message):
		self.setredisvalue('statusmessage', message)

	def allworkis(self, amount):
		self.setredisvalue('poolofwork', amount)

	def remain(self, remaining):
		self.setredisvalue('remaining', remaining)

	def sethits(self, found):
		self.setredisvalue('hitcount', found)

	def addhits(self, hits):
		k = self.returnrediskey('hitcount')
		self.redisconnection.incrby(k, hits)

	def activate(self):
		self.setredisvalue('active', True)

	def deactivate(self):
		self.setredisvalue('active', False)

	def getactivity(self):
		return self.getredisvalue('active')

	def getredisnotes(self):
		notes = self.getredisvalue('notes')
		return notes.decode('utf-8')

	def setnotes(self, message):
		self.setredisvalue('notes', message)

	def getnotes(self):
		notes = self.getredisnotes()
		message = '<span class="small">{msg}</span>'
		if 14 < self.getelapsed() < 21:
			m = '(long requests can be aborted by reloading the page)'
		elif re.search('unavailable', notes) and 9 < self.getelapsed() < 15:
			m = notes
		elif re.search('unavailable', notes) is None:
			m = notes
		else:
			m = ''

		return message.format(msg=m)


if hipparchia.config['POLLCONNECTIONTYPE'] != 'redis':
	class ProgressPoll(SharedMemoryProgressPoll):
		pass
else:
	class ProgressPoll(RedisProgressPoll):
		pass
