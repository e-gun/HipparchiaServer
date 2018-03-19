# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import psycopg2

from server import hipparchia


class ConnectionObject(object):
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
