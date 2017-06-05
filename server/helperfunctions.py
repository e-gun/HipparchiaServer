# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
from os import cpu_count

from server import hipparchia

config = configparser.ConfigParser()
config.read('config.ini')


def setthreadcount():
	"""
	
	used to set worker count on multithreaded functions
	return either the manual config value or determine it algorithmically
	
	:return: 
	"""

	if hipparchia.config['AUTOCONFIGWORKERS'] != 'yes':
		return hipparchia.config['WORKERS']
	else:
		return int(cpu_count() / 2) + 1


