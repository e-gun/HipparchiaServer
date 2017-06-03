# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import render_template

from server import hipparchia
from server.startup import authordict


#
# unadorned views for quickly peeking at the data
#

@hipparchia.route('/authors')
def authorlist():
	"""
	a simple dump of the authors available in the db

	:return:
	"""

	keys = list(authordict.keys())
	keys.sort()

	authors = [authordict[k] for k in keys]

	return render_template('authorlister.html', found=authors, numberfound=len(authors))
