# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from uuid import uuid4


def assignuniquename() -> str:
	"""

	random name for:
		temporary tables
		dbconnections

	:return:
	"""

	# numberofletters = 12
	# n = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(numberofletters)])

	n = str(uuid4())

	return n
