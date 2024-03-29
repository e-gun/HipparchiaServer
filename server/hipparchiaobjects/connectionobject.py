# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import sys
import threading

import psycopg2
import psycopg2.pool as connectionpool

from server import hipparchia
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.miscformatting import consolewarning
from server.threading.mpthreadcount import setthreadcount


class GenericConnectionObject(object):
	"""

	generic template for the specific connection types
	
	provides the basic functions less the actual connection and the
	specific connectioncleanup()

	"""

	postgresproblem = """
	You have encountered a FATAL error:
	
		{e}
	"""

	noserverproblem = """Hipparchia cannot find a database server at {h}:{p}.
	
	You may need to edit 'settings/networksettings.py'"""

	badpassproblem = """Hipparchia was denied access to the database at {h}:{p}
	
	The password provided was rejected.
	You probably need to edit 'settings/securitysettings.py'"""

	darwinproblem = """	[NB if postgresql was not shut down cleanly it might fail to restart properly, 
	and, worse, it might not notify you that it has failed to restart properly...
	
	On macOS you can enter the following command:
		$ psql
	
	If you see:
		psql: could not connect to server: Connection refused
			Is the server running locally and accepting
			connections on Unix domain socket "/tmp/.s.PGSQL.5432"?
	
	Then execute the next two commands:
		$ rm /usr/local/var/postgres/postmaster.pid
		$ brew services restart postgres
	]
	"""

	dbuser = hipparchia.config['DBUSER']
	dbpass = hipparchia.config['DBPASS']
	dbwriteuser = hipparchia.config['DBWRITEUSER']
	dbwritepass = hipparchia.config['DBWRITEPASS']

	dbhost = hipparchia.config['DBHOST']
	dbport = hipparchia.config['DBPORT']
	dbname = hipparchia.config['DBNAME']

	def __init__(self, autocommit, readonlyconnection):
		# note that only autocommit='autocommit' will make a difference
		self.autocommit = autocommit
		self.readonlyconnection = readonlyconnection
		self.commitcount = hipparchia.config['MPCOMMITCOUNT']
		# used for the key for getconn() and putconn(); but unneeded if PersistentConnectionPool
		# also useful to have on hand for debugging
		self.uniquename = assignuniquename()
		# the next two must get filled out when the actual connection is made
		self.dbconnection = None
		self.curs = None

	def setautocommit(self):
		# other possible values are:
		# psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
		# psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
		# psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
		# psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
		self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

	def getautocommit(self):
		return getattr(self.dbconnection, 'autocommit')

	def setdefaultisolation(self):
		try:
			self.dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_DEFAULT)
		except psycopg2.InterfaceError:
			# ubuntu19 and fedora31 coughed this up
			# psycopg2.InterfaceError: connection already closed
			pass

	def cursor(self):
		return self.curs

	def commit(self):
		getattr(self.dbconnection, 'commit')()

	def close(self):
		return getattr(self, 'connectioncleanup')()

	def setreadonly(self, value):
		assert value in [True, False], 'setreadonly() accepts only "True" or "False"'
		self.commit()
		getattr(self.dbconnection, 'set_session')(readonly=value, autocommit=True)

	def getreadonly(self):
		getattr(self.dbconnection, 'readonly')

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
				consolewarning('{c} failed its commit()'.format(c=self.uniquename), color='red')
				status = self.dbconnection.get_transaction_status()
				consolewarning('\tConnectionObject {me} status is {s}'.format(me=self.uniquename, s=status))
		return

	def connectioncleanup(self):
		raise NotImplementedError

	def plzcleanpool(self):
		return False

	@staticmethod
	def resetpool():
		pass


class PooledConnectionObject(GenericConnectionObject):
	"""

	there can be serious threading issues if you use this:

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

	some error messages if you misthread:
		xgkhgwsadbuu - Process-3 failed to commit()
		PooledConnectionObject xgkhgwsadbuu - Process-3 status is 2
		DatabaseError for <cursor object at 0x13ba55428; closed: 0> @ Process-3

	"""

	_pools = dict()
	poolneedscleaning = False

	def __init__(self, autocommit='defaultisno', readonlyconnection=True, ctype='ro'):
		super().__init__(autocommit, readonlyconnection)
		self.cytpe = ctype
		if not PooledConnectionObject._pools:
			# initialize the borg
			# note that poolsize is implicitly a claim about how many concurrent users you imagine having
			poolsize = setthreadcount() + 3

			# three known pool types; simple should be faster as you are avoiding locking
			pooltype = connectionpool.SimpleConnectionPool
			# pooltype = connectionpool.ThreadedConnectionPool
			# pooltype = connectionpool.PersistentConnectionPool

			# [A] 'ro' pool
			kwds = {'user': GenericConnectionObject.dbuser,
					'host': GenericConnectionObject.dbhost,
					'port': GenericConnectionObject.dbport,
					'database': GenericConnectionObject.dbname,
					'password': GenericConnectionObject.dbpass}

			try:
				readonlypool = pooltype(poolsize, poolsize * 2, **kwds)
			except psycopg2.OperationalError as operror:
				thefailure = operror.args[0]
				noconnection = 'could not connect to server'
				badpass = 'password authentication failed'
				if noconnection in thefailure:
					e = GenericConnectionObject.noserverproblem.format(h=GenericConnectionObject.dbhost, p=GenericConnectionObject.dbport)
					consolewarning(GenericConnectionObject.postgresproblem.format(e=e))
					if sys.platform == 'darwin':
						consolewarning(GenericConnectionObject.darwinproblem)

				if badpass in thefailure:
					e = GenericConnectionObject.badpassproblem.format(h=GenericConnectionObject.dbhost, p=GenericConnectionObject.dbport)
					consolewarning(GenericConnectionObject.postgresproblem.format(e=e))

				sys.exit(0)

			# [B] 'rw' pool: only used by the vector graphing functions
			# and these are always going to be single-threaded
			littlepool = max(int(setthreadcount() / 2), 2)
			kwds['user'] = GenericConnectionObject.dbwriteuser
			kwds['password'] = GenericConnectionObject.dbwritepass
			# this can be smaller because only vectors do rw and the vectorbot is not allowed in the pool
			# but you also need to be free to leave rw unset
			try:
				readandwritepool = pooltype(littlepool, littlepool, **kwds)
			except psycopg2.OperationalError:
				readandwritepool = None

			PooledConnectionObject._pools['ro'] = readonlypool
			PooledConnectionObject._pools['rw'] = readandwritepool

		assert self.cytpe in ['ro', 'rw'], 'connection type must be either "ro" or "rw"'
		self.pool = PooledConnectionObject._pools[self.cytpe]

		if self.cytpe == 'rw':
			self.readonlyconnection = False

		if threading.current_thread().name == 'vectorbot':
			# the vectobot lives in a thread and it will exhaust the pool
			self.simpleconnectionfallback()
		else:
			try:
				self.dbconnection = self.pool.getconn(key=self.uniquename)
			except psycopg2.pool.PoolError:
				# the pool is exhausted: try a basic connection instead
				# but in the long run should probably make a bigger pool/debug something
				# at the moment the only way to hit this error is via some sort of platform bug that yields a hung search
				# that is, something like a ryzen c-state aborted search damages the pool in the long run...
				consolewarning('PoolError: emergency fallback to SimpleConnectionObject()')
				self.simpleconnectionfallback()
				PooledConnectionObject.poolneedscleaning = True

		if self.autocommit == 'autocommit':
			self.setautocommit()

		self.setreadonly(self.readonlyconnection)
		self.curs = getattr(self.dbconnection, 'cursor')()

	@staticmethod
	def resetpool():
		# dangerous to do this while anything interesting is going on
		# currently checking to see if need cleaning at head of searchdispatcher
		consolewarning('emptying out PooledConnectionObject._pools()')
		PooledConnectionObject._pools = dict()
		PooledConnectionObject.poolneedscleaning = False

	def plzcleanpool(self):
		if PooledConnectionObject.poolneedscleaning:
			return True
		else:
			return False

	def simpleconnectionfallback(self):
		# print('SimpleConnectionObject', self.uniquename)
		c = SimpleConnectionObject(autocommit=self.autocommit, readonlyconnection=self.readonlyconnection, ctype=self.cytpe)
		c.thisisafallback = True
		self.dbconnection = c.dbconnection
		self.connectioncleanup = c.connectioncleanup

	def connectioncleanup(self):
		"""

		close a connection down in the most tedious way possible

		:param cursor:
		:param dbconnectiononnection:
		:return:
		"""

		self.commit()
		try:
			self.dbconnection.set_session(readonly=False)
		except psycopg2.OperationalError:
			# ubuntu19 and fedora31 constantly send you here
			# consolewarning('change your connection type to "simple" in "networksettings.py"; pooled connections are failing', color='red')
			pass
		self.setdefaultisolation()
		self.pool.putconn(self.dbconnection, key=self.uniquename)
		# print('connection returned to pool:', self.uniquename)

		return


class SimpleConnectionObject(GenericConnectionObject):
	"""

	open a connection to the db

	mirror psycopg2 methods

	add connectioncleanup() to the mix

	"""

	poolneedscleaning = False

	def __init__(self, autocommit='defaultisno', readonlyconnection=True, ctype='ro'):
		super().__init__(autocommit, readonlyconnection)
		assert ctype in ['ro', 'rw'], 'connection type must be either "ro" or "rw"'
		if ctype != 'rw':
			u = GenericConnectionObject.dbuser
			p = GenericConnectionObject.dbpass
		else:
			u = GenericConnectionObject.dbwriteuser
			p = GenericConnectionObject.dbwritepass
			self.readonlyconnection = False

		try:
			self.dbconnection = psycopg2.connect(user=u,
												host=GenericConnectionObject.dbhost,
												port=GenericConnectionObject.dbport,
												database=GenericConnectionObject.dbname,
												password=p)
		except psycopg2.OperationalError as operror:
			thefailure = operror.args[0]
			unknown = 'no pg_hba.conf entry for'
			if unknown in thefailure:
				thefailure = 'username and password problem for "DBWRITEUSER": check "securitysettings.py"'
			consolewarning(GenericConnectionObject.postgresproblem.format(e=thefailure), color='red')
			sys.exit(0)

		if self.autocommit == 'autocommit':
			self.setautocommit()

		self.setreadonly(self.readonlyconnection)
		self.curs = getattr(self.dbconnection, 'cursor')()
		self.thisisafallback = False

	def connectioncleanup(self):
		"""

		close a connection down in the most tedious way possible

		this overkill is mostly a legacy of the FreeBSD bug-hunt (which was actually a hardware issue...)

		:param cursor:
		:param dbconnectiononnection:
		:return:
		"""

		self.commit()

		getattr(self.curs, 'close')()
		del self.curs

		getattr(self.dbconnection, 'close')()
		del self.dbconnection
		# print('deleted connection', self.uniquename)

		return

	def plzcleanpool(self):
		return self.thisisafallback


if hipparchia.config['CONNECTIONTYPE'] == 'simple':
	class ConnectionObject(SimpleConnectionObject):
		pass
else:
	class ConnectionObject(PooledConnectionObject):
		pass
