# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import psycopg2
import psycopg2.pool as connectionpool

from server import hipparchia
from server.threading.mpthreadcount import setthreadcount
from server.dbsupport.tablefunctions import uniquetablename


class PooledConnectionObject(object):
	"""

	it looks like there are serious threading issues if you use this:

	a connection must be assigned to each worker *before* you join the MP jobs

	otherwise the different threads will not share the connections properly and you will end
	up with a lot of closed/broken connections

	psycopg connection status values.
	STATUS_SETUP = 0
	STATUS_READY = 1
	STATUS_BEGIN = 2
	STATUS_SYNC = 3  # currently unused
	STATUS_ASYNC = 4  # currently unused
	STATUS_PREPARED = 5

	# This is a useful mnemonic to check if the connection is in a transaction
	STATUS_IN_TRANSACTION = STATUS_BEGIN

	the interesting thing is that you can get something like the BSD stuck thread
	behavior on MacOS by pounding at this...

	you can eliminate the behavior by giving substringsearch(), etc its own ConnectionObject()
	this will slow you down plenty, though

	troubled connections have STATUS_BEGIN assigned to them when the disaster strikes

	some messages:
		xgkhgwsadbuu - Process-3 failed to commit()
		PooledConnectionObject xgkhgwsadbuu - Process-3 status is 2
		DatabaseError for <cursor object at 0x13ba55428; closed: 0> @ Process-3

	"""

	__pools = dict()

	def __init__(self, autocommit='nope', readonlyconnection=True, u='DBUSER', p='DBPASS'):
		# note that only autocommit='autocommit' will make a difference
		if not PooledConnectionObject.__pools:
			# initialize the borg
			# note that poolsize is implicitly a claim about how many concurrent users you imagine having
			poolsize = setthreadcount() + 2

			# three known pool types; simple should be faster as you are avoiding locking
			pooltype = connectionpool.SimpleConnectionPool
			# pooltype = connectionpool.ThreadedConnectionPool
			# pooltype = connectionpool.PersistentConnectionPool

			kwds = {'user': hipparchia.config['DBUSER'],
			        'host': hipparchia.config['DBHOST'],
			        'port': hipparchia.config['DBPORT'],
			        'database': hipparchia.config['DBNAME'],
			        'password': hipparchia.config['DBPASS']}

			readonlypool = pooltype(poolsize, poolsize * 2, **kwds)

			kwds['user'] = hipparchia.config['DBWRITEUSER']
			kwds['password'] = hipparchia.config['DBWRITEPASS']

			readandwritepool = pooltype(poolsize, poolsize * 2, **kwds)
			PooledConnectionObject.__pools['ro'] = readonlypool
			PooledConnectionObject.__pools['rw'] = readandwritepool

		self.autocommit = autocommit
		self.readonlyconnection = readonlyconnection
		if u == 'DBUSER':
			self.pool = PooledConnectionObject.__pools['ro']
		elif u == 'DBWRITEUSER':
			self.pool = PooledConnectionObject.__pools['rw']
		else:
			print('unknown dbuser: no connection made')
			self.pool = None

		# used for the key for getconn() and putconn(); but unneeded if PersistentConnectionPool
		self.uniquename = uniquetablename()
		try:
			self.dbconnection = self.pool.getconn(key=self.uniquename)
		except psycopg2.pool.PoolError:
			# this will probably get you in trouble eventually
			print('PoolError: fallback to SimpleConnectionObject()')
			self.dbconection = SimpleConnectionObject(autocommit, readonlyconnection=self.readonlyconnection, u=u, p=p)

		if self.autocommit == 'autocommit':
			self.setautocommit()

		self.dbconnection.set_session(readonly=self.readonlyconnection)
		self.connectioncursor = getattr(self.dbconnection, 'cursor')()
		self.commitcount = hipparchia.config['MPCOMMITCOUNT']

	def setautocommit(self):
		# other possible values are:
		# psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
		# psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
		# psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
		# psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

	def setdefaultisolation(self):
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)

	def cursor(self):
		return self.connectioncursor

	def commit(self):
		getattr(self.dbconnection, 'commit')()

	def close(self):
		return self.connectioncleanup()

	def connectionisclosed(self):
		return self.dbconnection.closed

	def checkneedtocommit(self, commitcountervalue):
		# commitcountervalue is an MPCounter?
		try:
			v = commitcountervalue.value
		except AttributeError:
			v = commitcountervalue
		if v % self.commitcount == 0:
			try:
				getattr(self.dbconnection, 'commit')()
			except psycopg2.DatabaseError:
				# psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq
				# will return often-but-not-always '2' as the status: i.e., STATUS_IN_TRANSACTION
				print(self.uniquename, 'failed its commit()')
				status = self.dbconnection.get_transaction_status()
				print('\tPooledConnectionObject {me} status is {s}'.format(me=self.uniquename, s=status))
		return

	def connectioncleanup(self):
		"""

		close a connection down in the most tedious way possible

		:param cursor:
		:param dbconnection:
		:return:
		"""

		self.commit()
		self.dbconnection.set_session(readonly=False)
		self.setdefaultisolation()
		self.pool.putconn(self.dbconnection, key=self.uniquename, close=False)
		# print('connection returned to pool:', self.uniquename)

		return


class SimpleConnectionObject(object):
	"""

	open a connection to the db

	mirror psycopg2 methods

	add connectioncleanup() to the mix

	consider implementing a connection pool

	example:
		https://github.com/gevent/gevent/blob/master/examples/psycopg2_pool.py

	"""

	def __init__(self, autocommit='nope', readonlyconnection=True, u='DBUSER', p='DBPASS'):
		self.autocommit = autocommit
		self.readonlyconnection = readonlyconnection
		self.dbconnection = psycopg2.connect(user=hipparchia.config[u],
											host=hipparchia.config['DBHOST'],
											port=hipparchia.config['DBPORT'],
											database=hipparchia.config['DBNAME'],
											password=hipparchia.config[p])

		if self.autocommit == 'autocommit':
			self.setautocommit()

		self.dbconnection.set_session(readonly=readonlyconnection)
		self.connectioncursor = self.dbconnection.cursor()
		self.commitcount = hipparchia.config['MPCOMMITCOUNT']

	def cursor(self):
		return self.connectioncursor

	def commit(self):
		getattr(self.dbconnection, 'commit')()
		return

	def close(self):
		getattr(self.dbconnection, 'close')()
		return

	def setautocommit(self):
		# other possible values are:
		# psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
		# psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
		# psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
		# psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

	def setdefaultisolation(self):
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)

	def connectionisclosed(self):
		return self.dbconnection.closed

	def cursorisclosed(self):
		return self.connectioncursor.closed

	def checkneedtocommit(self, commitcountervalue):
		# commitcountervalue is an MPCounter?
		try:
			v = commitcountervalue.value
		except:
			v = commitcountervalue
		if v % self.commitcount == 0:
			self.dbconnection.commit()
		return

	def connectioncleanup(self):
		"""

		close a connection down in the most tedious way possible

		this overkill is mostly part of the FreeBSD bug-hunt

		:param cursor:
		:param dbconnection:
		:return:
		"""

		self.commit()

		self.connectioncursor.close()
		del self.connectioncursor

		self.close()
		del self.dbconnection

		return


class ConnectionObject(PooledConnectionObject):
	pass
