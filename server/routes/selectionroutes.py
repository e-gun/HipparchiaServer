# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import request, session

from server import hipparchia
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import depunct
from server.listsandsession.genericlistfunctions import dropdupes, tidyuplist
from server.listsandsession.sessionfunctions import modifysessionvariable, rationalizeselections, returnactivelist, \
	selectionisactive
from server.formatting.sessionhtmlandjs import sessionselectionsashtml
from server.listsandsession.checksession import probeforsessionvariables
from server.startup import authordict, authorgenresdict, authorlocationdict, workdict, workgenresdict, \
	workprovenancedict


@hipparchia.route('/makeselection', methods=['GET'])
def selectionmade():
	"""
	once a choice is made, parse and register it inside session['selections']
	then return the human readable version of the same for display on the page

	'_AT_' syntax is used to restrict the scope of a search

	this function is also called without arguments to return the searchlist contents by
	skipping ahead to sessionselectionsashtml()

	sample input:
		'/makeselection?auth=gr0008&work=001&locus=3|4|23'

	sample output (pre-json):
		{'numberofselections': 2, 'timeexclusions': '', 'exclusions': '<span class="picklabel">Works</span><br /><span class="wkexclusions" id="searchselection_02" listval="0">Bacchylides, <span class="pickedwork">Dithyrambi</span></span><br />', 'selections': '<span class="picklabel">Author categories</span><br /><span class="agnselections" id="searchselection_00" listval="0">Lyrici</span><br />\n<span class="picklabel">Authors</span><br /><span class="auselections" id="searchselection_01" listval="0">AG</span><br />\n'}

	:return:
	"""

	probeforsessionvariables()

	uid = depunct(request.args.get('auth', ''))
	workid = depunct(request.args.get('work', ''))
	genre = depunct(request.args.get('genre', ''))
	auloc = depunct(request.args.get('auloc', ''))

	exclude = re.sub('[^tf]', '', request.args.get('exclude', ''))

	allowedpunct = '|,'
	locus = depunct(request.args.get('locus', ''), allowedpunct)
	endpoint = depunct(request.args.get('endpoint', ''), allowedpunct)

	allowedpunct = '.-?'
	wkprov = depunct(request.args.get('wkprov', ''), allowedpunct)

	allowedpunct = '.'
	wkgenre = depunct(request.args.get('wkgenre', ''), allowedpunct)

	if exclude != 't':
		suffix = 'selections'
		other = 'exclusions'
	else:
		suffix = 'exclusions'
		other = 'selections'

	# the selection box might contain stale info if you deselect a corpus while items are still in the box
	uid = selectionisactive(uid)

	if genre and genre not in returnactivelist(authorgenresdict):
		genre = str()

	if wkgenre and wkgenre not in returnactivelist(workgenresdict):
		wkgenre = str()

	if auloc and auloc not in returnactivelist(authorlocationdict):
		auloc = str()

	if wkprov and wkprov not in returnactivelist(workprovenancedict):
		wkprov = str()

	# you have validated the input, now do something with it...
	if (uid != '') and (workid != '') and (locus != '') and (endpoint != ''):
		# a span in an author: 3 verrine orations, e.g. [note that the selection is 'greedy': 1start - 3end]
		# http://127.0.0.1:5000/makeselection?auth=lt0474&work=005&locus=2|1&endpoint=2|3
		# convert this into a 'firstline' through 'lastline' format
		emptycursor = None
		workobject = None
		try:
			workobject = workdict['{a}w{b}'.format(a=uid, b=workid)]
		except KeyError:
			consolewarning('"makeselection/" sent a bad workuniversalid: {a}w{b}'.format(a=uid, b=workid))
		start = locus.split('|')
		stop = endpoint.split('|')
		start.reverse()
		stop.reverse()
		if workobject:
			firstline = finddblinefromincompletelocus(workobject, start, emptycursor)
			lastline = finddblinefromincompletelocus(workobject, stop, emptycursor, findlastline=True)
			citationtemplate = '{a}w{b}_FROM_{c}_TO_{d}'
			if firstline['code'] == 'success' and lastline['code'] == 'success':
				fl = firstline['line']
				ll = lastline['line']
				loc = citationtemplate.format(a=uid, b=workid, c=fl, d=ll)
				# print('span selected:', loc)
				# span selected: lt0474w005_FROM_4501_TO_11915
				# Cicero, In Verrem: 2.1.t.1
				# Cicero, In Verrem: 2.3.228.15
				if ll > fl:
					session['psg' + suffix].append(loc)
					session['psg' + suffix] = tidyuplist(session['psg' + suffix])
				else:
					msg = '"makeselection/" sent a firstline greater than the lastine value: {a} > {b} [{c}; {d}]'
					consolewarning(msg.format(a=fl, b=ll, c=locus, d=endpoint))
				rationalizeselections(loc, suffix)
			else:
				msg = '"makeselection/" could not find first and last: {a}w{b} - {c} TO {d}'
				consolewarning(msg.format(a=uid, b=workid, c=locus, d=endpoint))
	elif (uid != '') and (workid != '') and (locus != ''):
		# a specific passage
		session['psg' + suffix].append(uid + 'w' + workid + '_AT_' + locus)
		session['psg' + suffix] = tidyuplist(session['psg' + suffix])
		rationalizeselections(uid + 'w' + workid + '_AT_' + locus, suffix)
	elif (uid != '') and (workid != ''):
		# a specific work
		session['wk' + suffix].append(uid + 'w' + workid)
		session['wk' + suffix] = tidyuplist(session['wk' + suffix])
		rationalizeselections(uid + 'w' + workid, suffix)
	elif (uid != '') and (workid == ''):
		# a specific author
		session['au' + suffix].append(uid)
		session['au' + suffix] = tidyuplist(session['au' + suffix])
		rationalizeselections(uid, suffix)

	# if vs elif: allow multiple simultaneous instance
	if genre != '':
		# add to the +/- genre list and then subtract from the -/+ list
		session['agn' + suffix].append(genre)
		session['agn' + suffix] = tidyuplist(session['agn' + suffix])
		session['agn' + other] = dropdupes(session['agn' + other], session['agn' + suffix])
	if wkgenre != '':
		# add to the +/- genre list and then subtract from the -/+ list
		session['wkgn' + suffix].append(wkgenre)
		session['wkgn' + suffix] = tidyuplist(session['wkgn' + suffix])
		session['wkgn' + other] = dropdupes(session['wkgn' + other], session['wkgn' + suffix])
	if auloc != '':
		# add to the +/- locations list and then subtract from the -/+ list
		session['aloc' + suffix].append(auloc)
		session['aloc' + suffix] = tidyuplist(session['aloc' + suffix])
		session['aloc' + other] = dropdupes(session['aloc' + other], session['aloc' + suffix])
	if wkprov != '':
		# add to the +/- locations list and then subtract from the -/+ list
		session['wloc' + suffix].append(wkprov)
		session['wloc' + suffix] = tidyuplist(session['wloc' + suffix])
		session['wloc' + other] = dropdupes(session['wloc' + other], session['wloc' + suffix])

	# after the update to the session, you need to update the page html to reflect the changes
	# print('session["psgselections"]=', session['psgselections'])
	# print('session["psgexclusions"]=', session['psgexclusions'])

	return getcurrentselections()


@hipparchia.route('/setsessionvariable/<thevariable>/<thevalue>')
def setsessionvariable(thevariable, thevalue):
	"""
	accept a variable name and value: hand it off to the parser/setter
	returns:
		[{"latestdate": "1"}]
		[{"spuria": "no"}]
		etc.

	:return:
	"""

	# need to accept '-' because of the date spinner; '_' because of 'converted_date', etc
	validpunct = '-_'
	thevalue = depunct(thevalue, validpunct)

	try:
		session['authorssummary']
	except KeyError:
		# cookies are not enabled
		return json.dumps([{'none': 'none'}])

	modifysessionvariable(thevariable, thevalue)

	result = json.dumps([{thevariable: thevalue}])

	return result


@hipparchia.route('/clearselections/<category>/<index>')
def clearselections(category, index=-1):
	"""
	a selection gets thrown into the trash

	:return:
	"""

	selectiontypes = ['auselections', 'wkselections', 'psgselections', 'agnselections', 'wkgnselections',
						'alocselections', 'wlocselections', 'auexclusions', 'wkexclusions', 'psgexclusions',
						'agnexclusions', 'wkgnexclusions', 'alocexclusions', 'wlocexclusions']

	if category not in selectiontypes:
		category = None

	try:
		index = int(index)
	except ValueError:
		index = -1

	if category and index > -1:
		try:
			session[category].pop(index)
		except IndexError:
			consolewarning('\tclearselections() IndexError when popping {c}[{i}]'.format(c=category, i=str(index)), color='red')
			pass
		except KeyError:
			consolewarning('\tclearselections() KeyError when popping {c}[{i}]'.format(c=category, i=str(index)), color='red')
			pass

		session.modified = True

	return getcurrentselections()


@hipparchia.route('/getselections')
def getcurrentselections():
	"""

	send the html for what we have picked so that the relevant box can be populate

	get three bundles to put in the table cells

	:return:
	"""

	htmlbundles = sessionselectionsashtml(authordict, workdict)
	htmlbundles = json.dumps(htmlbundles)

	return htmlbundles
