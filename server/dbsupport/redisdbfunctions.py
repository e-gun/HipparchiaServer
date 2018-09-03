# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from typing import List

import redis

from server import hipparchia


def establishredisconnection() -> redis.client.Redis:
	"""

	make a connection to redis



	:return:
	"""

	dbid = hipparchia.config['REDISDBID']
	if hipparchia.config['REDISPORT'] != 0:
		port = hipparchia.config['REDISPORT']
		redisconnection = redis.Redis(host='localhost', port=port, db=dbid)
	else:
		sock = hipparchia.config['REDISCOCKET']
		redisconnection = redis.Redis(unix_socket_path=sock, db=dbid)

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
