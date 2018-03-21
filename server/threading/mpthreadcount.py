# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from os import cpu_count

from server import hipparchia


def setthreadcount(startup=False):
	"""

	used to set worker count on multithreaded functions
	return either the manual config value or determine it algorithmically

	:return:
	"""

	if hipparchia.config['AUTOCONFIGWORKERS'] != 'yes':
		workers = hipparchia.config['WORKERS']
	else:
		workers = int(cpu_count() / 2) + 1

	if workers < 1:
		workers = 1

	if workers > cpu_count() and startup:
		print('\nWARNING: threadcount exceeds total available number of threads: {a} vs {b}'.format(a=workers, b=cpu_count()))

	return workers
