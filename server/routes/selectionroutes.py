# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import redirect, request, session, url_for

from server import hipparchia
from server.formatting.wordformatting import depunct
from server.listsandsession.listmanagement import dropdupes, tidyuplist
from server.listsandsession.sessionfunctions import modifysessionvar, rationalizeselections, returnactivelist, \
	selectionisactive, sessionselectionsashtml
from server.startup import authordict, authorgenresdict, authorlocationdict, workdict, workgenresdict, \
	workprovenancedict


@hipparchia.route('/makeselection', methods=['GET'])
def selectionmade():
	"""
	once a choice is made, parse and register it inside session['selections']
	then return the human readable version of the same for display on the page

	this is also called without arguments to return the searchlist contents by
	skipping ahead to sessionselectionsashtml()

	sample input:
		'/makeselection?auth=gr0008&work=001&locus=3|4|23'

	sample output (pre-json):
		{'numberofselections': 2, 'timeexclusions': '', 'exclusions': '<span class="picklabel">Works</span><br /><span class="wkexclusions" id="searchselection_02" listval="0">Bacchylides, <span class="pickedwork">Dithyrambi</span></span><br />', 'selections': '<span class="picklabel">Author categories</span><br /><span class="agnselections" id="searchselection_00" listval="0">Lyrici</span><br />\n<span class="picklabel">Authors</span><br /><span class="auselections" id="searchselection_01" listval="0">AG</span><br />\n'}

	:return:
	"""

	uid = depunct(request.args.get('auth', ''))
	workid = depunct(request.args.get('work', ''))
	genre = depunct(request.args.get('genre', ''))
	auloc = depunct(request.args.get('auloc', ''))
	exclude = re.sub('[^tf]', '', request.args.get('exclude', ''))

	allowedpunct = '|,'
	locus = depunct(request.args.get('locus', ''), allowedpunct)

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
		genre = ''

	if wkgenre and wkgenre not in returnactivelist(workgenresdict):
		wkgenre = ''

	if auloc and auloc not in returnactivelist(authorlocationdict):
		auloc = ''

	if wkprov and wkprov not in returnactivelist(workprovenancedict):
		wkprov = ''

	# you have validated the input, now do something with it...

	if (uid != '') and (workid != '') and (locus != ''):
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

	# if vs elif: allow multiple simultaneous settings
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

	return getcurrentselections()


@hipparchia.route('/setsessionvariable', methods=['GET'])
def setsessionvariable():
	"""
	accept a variable name and value: hand it off to the parser/setter
	returns:
		[{"latestdate": "1"}]
		[{"spuria": "no"}]
		etc.

	:return:
	"""

	param = re.search(r'(.*?)=.*?', request.query_string.decode('utf-8'))
	param = param.group(1)
	val = request.args.get(param)
	# need to accept '-' because of the date spinner; '_' because of 'converted_date', etc
	validpunct = '-_'
	val = depunct(val, validpunct)

	modifysessionvar(param, val)

	result = json.dumps([{param: val}])

	return result


@hipparchia.route('/clearselections', methods=['GET'])
def clearselections():
	"""
	a selection gets thrown into the trash
	:return:
	"""
	category = request.args.get('cat', '')
	selectiontypes = ['auselections', 'wkselections', 'psgselections', 'agnselections', 'wkgnselections', 'alocselections', 'wlocselections',
						'auexclusions', 'wkexclusions', 'psgexclusions', 'agnexclusions', 'wkgnexclusions', 'alocexclusions', 'wlocexclusions']
	if category not in selectiontypes:
		category = ''

	item = request.args.get('id', '')
	item = int(item)

	try:
		session[category].pop(item)
	except IndexError:
		print('clearselections() failed to pop', category, str(item))
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


@hipparchia.route('/resetsession')
def clearsession():
	"""
	clear the session
	this will reset all settings and reload the front page
	:return:
	"""

	session.clear()
	return redirect(url_for('frontpage'))
