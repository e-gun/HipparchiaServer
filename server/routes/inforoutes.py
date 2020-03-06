# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re
import time
from os import path

from flask import redirect, render_template, session, url_for

from server import hipparchia
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.startup import authordict, authorgenresdict, authorlocationdict, workdict, workgenresdict, \
	workprovenancedict
from server.startup import progresspolldict


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
		results = list()
		for c in categories:
			results += viewing[c]
		results = list(set(results))
		results = [{'key': '', 'value': r} for r in results]
		results = sorted(results, key=lambda x: x['value'])
	else:
		results = list()
		dictionarytodisplay = '[invalid value]'

	return render_template('dbcontentslister.html', found=results, numberfound=len(results), label=dictionarytodisplay, tag='Available')


@hipparchia.route('/csssamples')
def styesheetsamples():
	"""

	show what everything will look like

	:return:
	"""

	excludes = ['td', 'th', 'table']

	stylesheet = hipparchia.config['CSSSTYLESHEET']
	stylefile = hipparchia.root_path+'/css/'+stylesheet

	stylecontents = list()
	if path.isfile(stylefile):
		with open(stylefile, 'r') as f:
			stylecontents = f.read().splitlines()

	definitions = re.compile(r'^(.*?)\s{')
	styles = [re.sub(definitions, r'\1', s) for s in stylecontents
	          if re.search(definitions, s) and not re.search(r'\.', s[1:])]

	# take care of multiple simult definitions:
	#   .textuallemma, .interlineartext, .interlinearmarginalia, .marginaltext
	unpackedstyles = list()
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


@hipparchia.route('/showsession')
def showsessioncontents():
	"""

	dump the contents of the session to a browser page

	:return:
	"""
	stylesheet = hipparchia.config['CSSSTYLESHEET']

	output = list()
	linetemplate = '{k}: {v}'

	for k in session.keys():
		output.append(linetemplate.format(k=k, v=session[k]))

	return render_template('genericlistdumper.html', info=output, css=stylesheet)


@hipparchia.route('/testroute')
def testroute():
	"""

	execute a debugging function of your choice...

	note that we expect to be using print() to generate the results and to send them to the console

	:return:
	"""

	ts = str(int(time.time()))
	progresspolldict[ts] = ProgressPoll(ts)
	activepoll = progresspolldict[ts]
	activepoll.activate()
	activepoll.statusis('executing testroute()')

	# looking for CAP-U when we need CAP-V
	# from server.hipparchiaobjects.connectionobject import ConnectionObject
	# # select marked_up_line from lt0914 where marked_up_line like '%U%' limit 1;
	# lt = {x for x in authordict if x[0:2] == 'lt'}
	# dbconnection = ConnectionObject()
	# cursor = dbconnection.cursor()
	# problematic = list()
	# for au in lt:
	# 	q = "select marked_up_line from {x} where marked_up_line like '%U%' limit 1;".format(x=au)
	# 	cursor.execute(q)
	# 	f = cursor.fetchone()
	# 	if f:
	# 		print('{a}\t{b}'.format(a=au, b=f))
	# 		problematic.append(au)
	# print('has CAP-U', problematic)
	#
	# dbconnection.connectioncleanup()

	# from server.routes.vectorroutes import findlatentsemanticindex
	#
	# so = buildsearchobject(ts, request, session)
	#
	# doimportedfunction = findlatentsemanticindex(activepoll, so)


	# # looking for all of the unique chars required to generate all of the citations.
	#
	# dbconnection = ConnectionObject()
	# cursor = dbconnection.cursor()
	# flatten = lambda x: [item for sublist in x for item in sublist]
	#
	# authorlist = [a for a in authordict]
	#
	# charlist = list()
	#
	# count = 0
	# for a in authorlist:
	# 	count += 1
	# 	q = 'select level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value from {t}'
	# 	cursor.execute(q.format(t=a))
	# 	f = cursor.fetchall()
	# 	c = set(str().join(flatten(f)))
	# 	charlist.append(c)
	#
	# charlist = flatten(charlist)
	# charlist = set(charlist)
	# charlist = list(charlist)
	# charlist.sort()
	#
	# print(charlist)
	# dbconnection.connectioncleanup()

	del activepoll

	return redirect(url_for('frontpage'))
