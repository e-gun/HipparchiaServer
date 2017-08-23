# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from os import path
from sys import argv

from flask import render_template

from server import hipparchia
from server.startup import authordict, authorgenresdict, authorlocationdict, workdict, workgenresdict, \
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
		results = sorted(results, key=lambda x: x['key'])
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


@hipparchia.route('/csssamples')
def styesheetsamples():
	"""

	show what everything will look like

	:return:
	"""

	excludes = ['td', 'th', 'table']

	currentpath = path.dirname(argv[0])
	stylesheet = hipparchia.config['CSSSTYLESHEET']
	stylefile = currentpath+'/server'+stylesheet

	stylecontents = []
	if path.isfile(stylefile):
		with open(stylefile, 'r') as f:
			stylecontents = f.read().splitlines()

	definitions = re.compile(r'^(.*?)\s{')
	styles = [re.sub(definitions, r'\1', s) for s in stylecontents
	          if re.search(definitions, s) and not re.search(r'\.', s[1:])]

	# take care of multiple simult definitions:
	#   .textuallemma, .interlineartext, .interlinearmarginalia, .marginaltext
	unpackedstyles = []
	for s in styles:
		up = s.split(', ')
		unpackedstyles += up

	invalid = re.compile(r'^[:@#]')
	styles = [s for s in unpackedstyles if not re.search(invalid, s) and s not in excludes]

	spanner = re.compile(r'^\.')
	spans = [s for s in styles if re.search(spanner, s)]
	notspans = list(set(styles) - set(spans))
	spans = [s[1:] for s in spans]
	spans = [s.split(':')[0] for s in spans]

	spans = sorted(spans)
	notspans = sorted(notspans)

	return render_template('stylesampler.html', css=stylesheet, spans=spans, notspans=notspans,
	                       numberfound=len(spans)+len(notspans))
