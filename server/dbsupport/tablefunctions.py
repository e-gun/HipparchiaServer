# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from uuid import uuid4


def assignuniquename(maxlength=None) -> str:
	"""

	random name for:
		temporary tables
		dbconnections

	FreeBSD's postgres will choke on the '-' in something like 'b3eb3e01-afe0-48ae-acb8-605ae58c9d6d'

		psycopg2.ProgrammingError: syntax error at or near "="

	This is not true in MacOS

	:return:
	"""

	# numberofletters = 12
	# n = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(numberofletters)])

	n = str(uuid4())

	n = re.sub(r'-', str(), n)

	if maxlength:
		n = n[:maxlength]

	return n
