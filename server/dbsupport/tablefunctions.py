# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import random

from uuid import uuid4

from server.hipparchiaobjects.dbtextobjects import dbAuthor


def tablenamer(authorobject: dbAuthor, thework: int) -> str:
	"""

	tell me the name of your table
	work 1 is stored as 0: try not to create a table 0; lots of unexpected results can stem from this off-by-one slip

	:param authorobject:
	:param thework:
	:return:
	"""

	wk = authorobject.listofworks[thework - 1]
	# wk = authorobject.listworks()[thework - 1]
	nm = authorobject.authornumber
	wn = wk.worknumber

	lg = wk.language
	# how many bilingual authors are there again?
	if lg == 'G':
		pr = 'gr'
	elif lg == 'L':
		pr = 'lt'
	else:
		pr = ''
		print('oh, I do not speak {lg} and I will be unable to access a DB'.format(lg=lg))

	workdbname = '{p}{n}w{w}'.format(p=pr, n=nm, w=wn)

	return workdbname


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
