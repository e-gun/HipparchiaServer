# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import psycopg2
import random

from server import hipparchia


class SimpleConnectionObject(object):
	"""

	open a connection to the db

	mirror psycopg2 methods

	add connectioncleanup() to the mix

	consider implementing a connection pool

	example:
		https://github.com/gevent/gevent/blob/master/examples/psycopg2_pool.py

	"""

	def __init__(self, autocommit='n', readonlyconnection=True, u='DBUSER', p='DBPASS'):
		self.autocommit = autocommit
		self.readonlyconnection = readonlyconnection
		self.dbconnection = psycopg2.connect(user=hipparchia.config[u],
											host=hipparchia.config['DBHOST'],
											port=hipparchia.config['DBPORT'],
											database=hipparchia.config['DBNAME'],
											password=hipparchia.config[p])

		if self.autocommit == 'autocommit':
			self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

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


ConnectionObject = SimpleConnectionObject

pools = False

if pools:
	import psycopg2.pool as connectionpool
	poolsize = 10

	kwds = {'user': hipparchia.config['DBUSER'],
			'host': hipparchia.config['DBHOST'],
			'port': hipparchia.config['DBPORT'],
			'database': hipparchia.config['DBNAME'],
			'password': hipparchia.config['DBPASS']}

	readonlypool = connectionpool.ThreadedConnectionPool(poolsize, poolsize * 3, **kwds)

	kwds['user'] = hipparchia.config['DBWRITEUSER']
	kwds['password'] = hipparchia.config['DBWRITEPASS']

	readandwritepool = connectionpool.ThreadedConnectionPool(poolsize, poolsize * 3, **kwds)


	class PooledConnectionObject(object):
		"""

		presently buggy: will launch, but searches will churn up these errors over and over:

			psycopg2.ProgrammingError: no results to fetch

			psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq

		it looks like there are serious threading issues: would need to write own version of psycopg2.pool?

		and it seems that the temp tables are not getting deleted:

			psycopg2.ProgrammingError: relation "gr7000_includelist" already exists

		[this can be fixed by adding 'DROP TABLE IF EXISTS' to the creation of the temp tables]

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
			self.id = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(12)])
			self.dbconnection = self.pool.getconn(key=self.id)

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
			self.dbconnection.set_session(readonly=False)
			self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)
			self.pool.putconn(self.dbconnection, key=self.id, close=False)

			return

	ConnectionObject = PooledConnectionObject
