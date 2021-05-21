# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import pickle
from multiprocessing import current_process, Queue, Process
from typing import List

from click import secho

try:
	import redis
except ImportError:
	if current_process().name == 'MainProcess':
		secho('redis unavailable', fg='bright_black')
	redis = None

from server import hipparchia
from server.threading.mpthreadcount import setthreadcount


class NullRedis(object):
	def __init__(self):
		pass

	class client():
		def Redis(self):
			pass


if not redis:
	redis = NullRedis()


class PooledRedisBorg(object):
	"""

	set up a connection pool to redis

	we are preventing the destruction of the link to avoid startup costs
	[unfortunately this is not actually yielding increased speed]

	will always use the first item in a list with only one element

	"""

	_pool = list()

	def __init__(self):
		if not PooledRedisBorg._pool:
			poolsize = setthreadcount() + 2
			dbid = hipparchia.config['REDISDBID']
			if hipparchia.config['REDISPORT'] != 0:
				port = hipparchia.config['REDISPORT']
				redishost = hipparchia.config['REDISHOST']
				redisconnection = redis.ConnectionPool(host=redishost, port=port, db=dbid, max_connections=poolsize)
			else:
				sock = hipparchia.config['REDISCOCKET']
				redisconnection = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=sock, db=dbid, max_connections=poolsize)
			PooledRedisBorg._pool.append(redisconnection)
			# print('initialized PooledRedisBorg')
		self.pool = PooledRedisBorg._pool[0]
		self.connection = redis.Redis(connection_pool=self.pool)


def establishredisconnection() -> redis.client.Redis:
	"""

	make a connection to redis

	:return:
	"""

	# do it the simple way
	# dbid = hipparchia.config['REDISDBID']
	# if hipparchia.config['REDISPORT'] != 0:
	# 	port = hipparchia.config['REDISPORT']
	# 	redisconnection = redis.Redis(host='localhost', port=port, db=dbid)
	# else:
	# 	sock = hipparchia.config['REDISCOCKET']
	# 	redisconnection = redis.Redis(unix_socket_path=sock, db=dbid)

	# do it the borg way
	redisobject = PooledRedisBorg()

	redisconnection = redisobject.connection

	return redisconnection


def buildredissearchlist(listofsearchlocations: List, searchid: str):
	"""

	take a list of places to search and load it into redis as the shared state handler


	:param listofsearchlocations:
	:param searchid:
	:return:
	"""

	rc = establishredisconnection()

	rediskey = '{id}_searchlist'.format(id=searchid)

	rc.delete(rediskey)

	while listofsearchlocations:
		rc.sadd(rediskey, listofsearchlocations.pop())

	# print('search set is', rc.smembers(rediskey))

	return


def loadredisresults(searchid):
	"""

	search results were passed to redis

	grab and return them

	:param searchid:
	:return:
	"""

	redisfindsid = '{id}_findslist'.format(id=searchid)
	rc = establishredisconnection()
	finds = rc.lrange(redisfindsid, 0, -1)
	# foundlineobjects = [dblineintolineobject(pickle.loads(f)) for f in finds]
	foundlineobjects = [pickle.loads(f) for f in finds]
	return foundlineobjects


def mutiredisfetch(vectorresultskey):
	"""

	parallelize redis fetching

	"""

	workers = setthreadcount()

	q = Queue()
	processes = list()
	results = list()
	for _ in range(workers):
		p = Process(target=redisfetch, args=(vectorresultskey, q))
		processes.append(p)
		p.start()
	for _ in processes:
		oneresult = q.get()  # will block
		results.append(oneresult)
	for p in processes:
		p.join()

	compositeresults = list()
	for r in results:
		compositeresults.extend(r)

	return compositeresults


def redisfetch(vectorresultskey, queue):
	"""

	generic fetcher to be used with mutiredisfetch()

	"""
	rc = establishredisconnection()
	redisresults = list()

	while vectorresultskey:
		r = rc.spop(vectorresultskey)
		if r:
			redisresults.append(r)
		else:
			vectorresultskey = None

	queue.put(redisresults)

	return



"""

[G] [not actually a case where we need debugging ATM] REDIS debug notes:

[build a connection by hand]

    import redis
    sock='/tmp/redis.sock'
    dbid=0
    poolsize=4
    port = 6379
    redisconnection = redis.ConnectionPool(host='localhost', port=port, db=dbid, max_connections=poolsize)
    # redisconnection = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=sock, db=dbid, max_connections=poolsize)
    c = redis.Redis(connection_pool=redisconnection)

ex queries:

    c.keys()
    len([k for k in c.keys() if b'_searchlist' in k])
    c.delete(b'dab1038f_searchlist')

    r = [k for k in c.keys() if b'remain' in k]
    a = [c.delete(key) for key in r]

"""
