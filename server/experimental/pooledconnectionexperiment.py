# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import random

import psycopg2
import psycopg2.pool as connectionpool

from server import hipparchia
from server.dbsupport.dbfunctions import uniquetablename

poolsize = 20

kwds = {'user': hipparchia.config['DBUSER'],
		'host': hipparchia.config['DBHOST'],
		'port': hipparchia.config['DBPORT'],
		'database': hipparchia.config['DBNAME'],
		'password': hipparchia.config['DBPASS']}

readonlypool = connectionpool.ThreadedConnectionPool(poolsize, poolsize * 2, **kwds)

kwds['user'] = hipparchia.config['DBWRITEUSER']
kwds['password'] = hipparchia.config['DBWRITEPASS']

readandwritepool = connectionpool.ThreadedConnectionPool(poolsize, poolsize * 2, **kwds)


class PooledConnectionObject(object):
	"""
	presently buggy: will launch and will yield results, but searches will churn up these errors over and over:

		psycopg2.ProgrammingError: no results to fetch

		psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq

	it looks like there are serious threading issues

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
		self.id = uniquetablename()
		print('PooledConnectionObject init', self.id)
		self.dbconnection = self.pool.getconn(key=self.id)
		print('PooledConnectionObject getconn', self.id)
		status = self.dbconnection.get_transaction_status()
		print('PooledConnectionObject {me} status is {s}'.format(me=self.id, s=status))

		if self.autocommit == 'autocommit':
			# other possible values are:
			# psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
			# psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
			# psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
			# psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
			self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

		self.dbconnection.set_session(readonly=self.readonlyconnection)
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

	def checkneedtocommit(self, commitcountervalue):
		# commitcountervalue is an MPCounter?
		try:
			v = commitcountervalue.value
		except:
			v = commitcountervalue
		if v % self.commitcount == 0:
			try:
				self.dbconnection.commit()
			except psycopg2.DatabaseError:
				# psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq
				# will return '2' as the status: i.e., STATUS_IN_TRANSACTION
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

		self.commit()
		self.dbconnection.set_session(readonly=False)
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)
		self.pool.putconn(self.dbconnection, key=self.id, close=False)
		print('PooledConnectionObject putconn', self.id)

		return
