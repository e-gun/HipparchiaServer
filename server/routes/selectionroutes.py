# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import request, session
from werkzeug.datastructures import MultiDict

try:
	from rich import print
except ImportError:
	pass

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

JSON_STR = str


@hipparchia.route('/selection/<action>', methods=['GET'])
@hipparchia.route('/selection/<action>/<one>', methods=['GET'])
@hipparchia.route('/selection/<action>/<one>/<two>', methods=['GET'])
def selectionmaker(action: str, one=None, two=None) -> JSON_STR:
	"""

	dispatcher for "/selection/..." requests

	"""

	one = depunct(one)
	two = depunct(two)

	knownfunctions = {
		'make':
			{'fnc': selectionmade, 'param': [request.args]},
		'clear':
			{'fnc': clearselections, 'param': [one, two]},
		'fetch':
			{'fnc': getcurrentselections, 'param': None}
	}

	if action not in knownfunctions:
		return json.dumps(str())

	f = knownfunctions[action]['fnc']
	p = knownfunctions[action]['param']

	if p:
		j = f(*p)
	else:
		j = f()

	if hipparchia.config['JSONDEBUGMODE']:
		print('/selection/{f}/\n\t{j}'.format(f=action, j=j))

	return j


def selectionmade(requestargs: MultiDict) -> JSON_STR:
	"""

	once a choice is made, parse and register it inside session['selections']
	then return the human readable version of the same for display on the page

	'_AT_' syntax is used to restrict the scope of a search

	"GET /selection/make/_?auth=lt0474&work=001&locus=13|4&endpoint= HTTP/1.1"
	request.args ImmutableMultiDict([('auth', 'lt0474'), ('work', '001'), ('locus', '13|4'), ('endpoint', '')])

	"GET /selection/make/_?auth=lt0474&work=001&locus=10&endpoint=20&raw=t HTTP/1.1"
	request.args ImmutableMultiDict([('auth', 'lt0474'), ('work', '001'), ('locus', '10'), ('endpoint', '20'), ('raw', 't')])

	"GET /selection/make/_?auth=lt0474&work=001&exclude=t HTTP/1.1"
	request.args ImmutableMultiDict([('auth', 'lt0474'), ('work', '001'), ('exclude', 't')])

	:return:
	"""

	probeforsessionvariables()

	uid = depunct(requestargs.get('auth', str()))
	workid = depunct(requestargs.get('work', str()))
	genre = depunct(requestargs.get('genre', str()))
	auloc = depunct(requestargs.get('auloc', str()))

	rawdataentry = re.sub('[^tf]', str(), requestargs.get('raw', str()))
	exclude = re.sub('[^tf]', str(), requestargs.get('exclude', str()))

	allowedpunct = '|,.'
	locus = depunct(requestargs.get('locus', str()), allowedpunct)
	endpoint = depunct(requestargs.get('endpoint', str()), allowedpunct)

	allowedpunct = '.-?'
	wkprov = depunct(requestargs.get('wkprov', str()), allowedpunct)

	allowedpunct = '.'
	wkgenre = depunct(requestargs.get('wkgenre', str()), allowedpunct)

	if exclude != 't':
		suffix = 'selections'
		other = 'exclusions'
	else:
		suffix = 'exclusions'
		other = 'selections'

	if rawdataentry == 't':
		locus = re.sub(r'\.', '|', locus)
		endpoint = re.sub(r'\.', '|', endpoint)

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
	if uid and workid and locus and endpoint:
		# a span in an author: 3 verrine orations, e.g. [note that the selection is 'greedy': 1start - 3end]
		# http://127.0.0.1:5000/makeselection?auth=lt0474&work=005&locus=2|1&endpoint=2|3
		# convert this into a 'firstline' through 'lastline' format
		emptycursor = None
		workobject = None
		try:
			workobject = workdict['{a}w{b}'.format(a=uid, b=workid)]
		except KeyError:
			consolewarning('"/selection/make/" sent a bad workuniversalid: {a}w{b}'.format(a=uid, b=workid))
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
	elif uid and workid and locus:
		# a specific passage
		session['psg' + suffix].append(uid + 'w' + workid + '_AT_' + locus)
		session['psg' + suffix] = tidyuplist(session['psg' + suffix])
		rationalizeselections(uid + 'w' + workid + '_AT_' + locus, suffix)
	elif uid and workid:
		# a specific work
		session['wk' + suffix].append(uid + 'w' + workid)
		session['wk' + suffix] = tidyuplist(session['wk' + suffix])
		rationalizeselections(uid + 'w' + workid, suffix)
	elif uid and not workid:
		# a specific author
		session['au' + suffix].append(uid)
		session['au' + suffix] = tidyuplist(session['au' + suffix])
		rationalizeselections(uid, suffix)

	# if vs elif: allow multiple simultaneous instance
	if genre:
		# add to the +/- genre list and then subtract from the -/+ list
		session['agn' + suffix].append(genre)
		session['agn' + suffix] = tidyuplist(session['agn' + suffix])
		session['agn' + other] = dropdupes(session['agn' + other], session['agn' + suffix])
	if wkgenre:
		# add to the +/- genre list and then subtract from the -/+ list
		session['wkgn' + suffix].append(wkgenre)
		session['wkgn' + suffix] = tidyuplist(session['wkgn' + suffix])
		session['wkgn' + other] = dropdupes(session['wkgn' + other], session['wkgn' + suffix])
	if auloc:
		# add to the +/- locations list and then subtract from the -/+ list
		session['aloc' + suffix].append(auloc)
		session['aloc' + suffix] = tidyuplist(session['aloc' + suffix])
		session['aloc' + other] = dropdupes(session['aloc' + other], session['aloc' + suffix])
	if wkprov:
		# add to the +/- locations list and then subtract from the -/+ list
		session['wloc' + suffix].append(wkprov)
		session['wloc' + suffix] = tidyuplist(session['wloc' + suffix])
		session['wloc' + other] = dropdupes(session['wloc' + other], session['wloc' + suffix])

	# after the update to the session, you need to update the page html to reflect the changes
	# print('session["psgselections"]=', session['psgselections'])
	# print('session["psgexclusions"]=', session['psgexclusions'])

	return getcurrentselections()


def clearselections(category, index=-1) -> JSON_STR:
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


def getcurrentselections() -> JSON_STR:
	"""

	send the html for what we have picked so that the relevant box can be populate

	get three bundles to put in the table cells

	:return:
	"""

	htmlbundles = sessionselectionsashtml(authordict, workdict)
	htmlbundles = json.dumps(htmlbundles)

	return htmlbundles


@hipparchia.route('/setsessionvariable/<thevariable>/<thevalue>')
def setsessionvariable(thevariable, thevalue) -> JSON_STR:
	"""
	accept a variable name and value: hand it off to the parser/setter
	returns:
		[{"latestdate": "1"}]
		[{"spuria": "no"}]
		etc.

	:return:
	"""

	nullresult = json.dumps([{'none': 'none'}])

	# need to accept '-' because of the date spinner; '_' because of 'converted_date', etc
	validpunct = '-_'
	thevalue = depunct(thevalue, validpunct)

	if thevalue == 'null':
		# the js sent out something unexpected while you were in the middle of swapping values
		# 127.0.0.1 - - [09/Mar/2021 09:50:42] "GET /setsessionvariable/browsercontext/null HTTP/1.1" 500 -
		return nullresult

	try:
		session['authorssummary']
	except KeyError:
		# cookies are not enabled
		return nullresult

	modifysessionvariable(thevariable, thevalue)

	result = json.dumps([{thevariable: thevalue}])

	return result
