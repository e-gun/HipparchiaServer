# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import render_template

from server import hipparchia
from server.startup import authordict, workdict, authorgenresdict, authorlocationdict, workgenresdict, \
	workprovenancedict


#
# unadorned views for quickly peeking at the data
#

@hipparchia.route('/databasecontents/<dictionarytodisplay>')
def databasecontents(dictionarytodisplay):
	"""
	a simple dump of info available in the db

	:return:
	"""

	icandisplay = {
		'authors': (authordict, 'universalid', 'cleanname'),
		'works': (workdict, 'universalid', 'title'),
		'augenres': (authorgenresdict, None, None),
		'aulocations': (authorlocationdict, None, None),
		'wkgenres': (workgenresdict, None, None),
		'wklocations': (workprovenancedict, None, None)
	}

	if dictionarytodisplay in icandisplay.keys() and icandisplay[dictionarytodisplay][1]:
		viewing = icandisplay[dictionarytodisplay][0]
		columnone = icandisplay[dictionarytodisplay][1]
		columntwo = icandisplay[dictionarytodisplay][2]
		keys = list(viewing.keys())
		results = [{'key': getattr(viewing[k], columnone), 'value': getattr(viewing[k], columntwo)} for k in keys]
		results = sorted(results, key= lambda x: x['key'])
	elif dictionarytodisplay in icandisplay.keys() and not icandisplay[dictionarytodisplay][1]:
		viewing = icandisplay[dictionarytodisplay][0]
		categories = ['gr', 'lt', 'in', 'dp', 'ch']
		results = []
		for c in categories:
			results += viewing[c]
		results = list(set(results))
		results = [{'key': '', 'value': r} for r in results]
		results = sorted(results, key=lambda x: x['value'])
	else:
		results = []
		dictionarytodisplay = '[invalid value]'

	return render_template('dbcontentslister.html', found=results, numberfound=len(results), label=dictionarytodisplay)
