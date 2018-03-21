# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import psycopg2
import psycopg2.pool as connectionpool
import multiprocessing

from server import hipparchia
from server.dbsupport.dbfunctions import uniquetablename

poolsize = 20
# pooltype = connectionpool.SimpleConnectionPool
pooltype = connectionpool.ThreadedConnectionPool
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


class PooledConnectionObject(object):
	"""
	presently buggy: will launch and will yield results, but searches will churn up these errors over and over:

		psycopg2.ProgrammingError: no results to fetch

		psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq

	it looks like there are serious threading issues: WORKERS = 1 fixes the problem; WORKERS = 2 generates is

	and it seems that the temp tables are not getting deleted when one expects them to vanish:

		psycopg2.ProgrammingError: relation "gr7000_includelist" already exists

	this can be fixed by adding 'DROP TABLE IF EXISTS' or 'DELETE ON COMMIT to the creation of the temp tables]
	but instead we are avoiding name collisions instead

	psycopg connection status values.
	STATUS_SETUP = 0
	STATUS_READY = 1
	STATUS_BEGIN = 2
	STATUS_SYNC = 3  # currently unused
	STATUS_ASYNC = 4  # currently unused
	STATUS_PREPARED = 5

	# This is a useful mnemonic to check if the connection is in a transaction
	STATUS_IN_TRANSACTION = STATUS_BEGIN

	the interesting thing is that you can get something like the BDS stuck thread
	behavior on MacOS by pounding at this...

	you can eliminate the behavior by giving substringsearch(), etc its own ConnectionObject()
	this will slow you down plenty, though

	troubled connections have STATUS_BEGIN assigned to them when the disaster strikes

	some messages:
		xgkhgwsadbuu - Process-3 failed to commit()
		PooledConnectionObject xgkhgwsadbuu - Process-3 status is 2
		DatabaseError for <cursor object at 0x13ba55428; closed: 0> @ Process-3

	"""

	def __init__(self, autocommit='n', readonlyconnection=True, u='DBUSER', p='DBPASS'):
		self.autocommit = autocommit
		self.readonlyconnection = readonlyconnection
		if u == 'DBUSER':
			self.pool = readonlypool
		elif u == 'DBWRITEUSER':
			self.pool = readandwritepool
		else:
			print('unknown dbuser: no connection made')
			self.pool = None

		# used for the key for getconn() and putconn(); but unneeded if PersistentConnectionPool
		self.open = False
		self.dippedintopool = 0
		while not self.open:
			self.dippedintopool += 1
			self.id = '{a} - {b}'.format(a=uniquetablename(), b=multiprocessing.current_process().name)
			# print('PooledConnectionObject init', self.id)
			self.dbconnection = self.pool.getconn(key=self.id)
			self.open = not self.dbconnection.closed
			if not self.open:
				self.pool.putconn(self.dbconnection, key=self.id, close=True)
		# print('PooledConnectionObject getconn {me} after {n} tries'.format(me=self.id, n=self.dippedintopool))
		# status = self.dbconnection.get_transaction_status()
		# print('PooledConnectionObject {me} status is {s}'.format(me=self.id, s=status))

		if self.autocommit == 'autocommit':
			# other possible values are:
			# psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
			# psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
			# psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
			# psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
			self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

		self.dbconnection.set_session(readonly=self.readonlyconnection)
		self.connectioncursor = getattr(self.dbconnection, 'cursor')()
		self.commitcount = hipparchia.config['MPCOMMITCOUNT']

	def cursor(self):
		return self.connectioncursor

	def commit(self):
		if not self.connectioncursor.closed and not self.dbconnection.closed:
			getattr(self.dbconnection, 'commit')()
		else:
			print('not committing because closed:', self.id)
		return

	def close(self):
		return self.connectioncleanup()

	def isclosed(self):
		return self.dbconnection.closed

	def checkneedtocommit(self, commitcountervalue):
		# commitcountervalue is an MPCounter?
		try:
			v = commitcountervalue.value
		except:
			v = commitcountervalue
		if v % self.commitcount == 0:
			try:
				getattr(self.dbconnection, 'commit')()
			except psycopg2.DatabaseError:
				# psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq
				# will return often-but-not-always '2' as the status: i.e., STATUS_IN_TRANSACTION
				print(self.id, 'failed to commit()')
				status = self.dbconnection.get_transaction_status()
				print('PooledConnectionObject {me} status is {s}'.format(me=self.id, s=status))
		return

	def connectioncleanup(self):
		"""

		close a connection down in the most tedious way possible

		:param cursor:
		:param dbconnection:
		:return:
		"""

		if not self.dbconnection.closed:
			self.commit()
			self.dbconnection.set_session(readonly=False)
			self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)
			self.pool.putconn(self.dbconnection, key=self.id, close=False)
			print('PooledConnectionObject putconn', self.id)
		else:
			print('putting away closed', self.id)
			self.pool.putconn(self.dbconnection, key=self.id, close=True)

		return
