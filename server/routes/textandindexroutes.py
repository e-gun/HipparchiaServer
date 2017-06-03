# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import time

from flask import request, session

from server import hipparchia
from server.dbsupport.dbfunctions import setconnection
from server.hipparchiaobjects.helperobjects import ProgressPoll
from server.startup import authordict, workdict, poll
from server.textsandindices.indexmaker import buildindextowork
from server.textsandindices.textandindiceshelperfunctions import tcparserequest, textsegmentfindstartandstop, \
	wordindextohtmltable, observedformjs
from server.textsandindices.textbuilder import buildtext


@hipparchia.route('/indexto', methods=['GET'])
def completeindex():
	"""
	build a complete index to a an author, work, or segment of a work

	:return:
	"""

	try:
		ts = str(int(request.args.get('id', '')))
	except:
		ts = str(int(time.time()))

	starttime = time.time()

	poll[ts] = ProgressPoll(ts)
	poll[ts].activate()

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	req = tcparserequest(request, authordict, workdict)
	ao = req['authorobject']
	wo = req['workobject']
	psg = req['passagelist']

	if session['headwordindexing'] == 'yes':
		useheadwords = True
	else:
		useheadwords = False

	if ao.universalid != 'gr0000' and wo.universalid != 'gr0000w000':
		# we have both an author and a work, maybe we also have a subset of the work
		if psg == ['']:
			# whole work
			poll[ts].statusis('Preparing an index to {t}'.format(t=wo.title))
			startline = wo.starts
			endline = wo.ends
		else:
			# partial work
			poll[ts].statusis('Preparing a partial index to {t}'.format(t=wo.title))
			startandstop = textsegmentfindstartandstop(ao, wo, psg, cur)
			startline = startandstop['startline']
			endline = startandstop['endline']

		cdict = {wo.universalid: (startline, endline)}
		output = buildindextowork(cdict, poll[ts], useheadwords, cur)
		allworks = []

	elif ao.universalid != 'gr0000' and wo.universalid == 'gr0000w000':
		poll[ts].statusis('Preparing an index to the works of {a}'.format(a=ao.shortname))
		# whole author
		cdict = {}
		for wkid in ao.listworkids():
			cdict[wkid] = (workdict[wkid].starts, workdict[wkid].ends)
		output = buildindextowork(cdict, poll[ts], useheadwords, cur)

		allworks = []
		for w in ao.listofworks:
			allworks.append(w.universalid[6:10] + ' ⇒ ' + w.title)
		allworks.sort()

	else:
		# we do not have a valid selection
		output = []
		allworks = []

	# get ready to send stuff to the page
	count = len(output)
	locale.setlocale(locale.LC_ALL, 'en_US')
	count = locale.format("%d", count, grouping=True)

	poll[ts].statusis('Preparing the index HTML')
	indexhtml = wordindextohtmltable(output, useheadwords)

	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)
	poll[ts].deactivate()

	results = {}
	results['authorname'] = ao.shortname
	results['title'] = wo.title
	results['structure'] = wo.citation()
	results['worksegment'] = '.'.join(psg)
	results['elapsed'] = buildtime
	results['wordsfound'] = count
	results['indexhtml'] = indexhtml
	results['keytoworks'] = allworks
	results['newjs'] = observedformjs()

	results = json.dumps(results)

	cur.close()
	del poll[ts]

	return results


@hipparchia.route('/textof', methods=['GET'])
def textmaker():
	"""
	build a text suitable for display
	:return:
	"""
	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	linesevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	req = tcparserequest(request, authordict, workdict)
	ao = req['authorobject']
	wo = req['workobject']
	psg = req['passagelist']

	if ao.universalid != 'gr0000' and wo.universalid == 'gr0000w000':
		# default to first work
		wo = ao.listofworks[0]

	if ao.universalid != 'gr0000' and wo.universalid != 'gr0000w000':
		# we have both an author and a work, maybe we also have a subset of the work
		if psg == ['']:
			# whole work
			startline = wo.starts
			endline = wo.ends
		else:
			startandstop = textsegmentfindstartandstop(ao, wo, psg, cur)
			startline = startandstop['startline']
			endline = startandstop['endline']

		texthtml = buildtext(wo.universalid, startline, endline, linesevery, cur)
	else:
		texthtml = ''

	results = {}
	results['authorname'] = ao.shortname
	results['title'] = wo.title
	results['structure'] = wo.citation()
	results['worksegment'] = '.'.join(psg)
	results['texthtml'] = texthtml

	results = json.dumps(results)

	cur.close()

	return results
