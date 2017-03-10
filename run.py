# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia

if __name__ == '__main__':

	hipparchia.run(threaded=True, host="0.0.0.0")