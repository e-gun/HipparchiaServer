# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import time

from flask import session

from server import hipparchia
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork, makeablankline
from server.dbsupport.miscdbfunctions import makeanemptywork, buildauthorworkandpassage
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.jsformatting import supplementalindexjs
from server.formatting.miscformatting import consolewarning, validatepollid
from server.formatting.wordformatting import avoidsmallvariants
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.listsandsession.checksession import probeforsessionvariables
from server.startup import authordict, poll, workdict
from server.textsandindices.indexmaker import buildindextowork
from server.textsandindices.textandindiceshelperfunctions import textsegmentfindstartandstop, wordindextohtmltable
from server.textsandindices.textbuilder import buildtext


@hipparchia.route('/indexto/<searchid>/<author>')
@hipparchia.route('/indexto/<searchid>/<author>/<work>')
@hipparchia.route('/indexto/<searchid>/<author>/<work>/<passage>')
def buildindexto(searchid: str, author: str, work=None, passage=None):
	"""
	build a complete index to a an author, work, or segment of a work

	:return:
	"""

	probeforsessionvariables()

	pollid = validatepollid(searchid)

	starttime = time.time()

	poll[pollid] = ProgressPoll(pollid)
	poll[pollid].activate()

	dbconnection = ConnectionObject('autocommit')
	dbcursor = dbconnection.cursor()

	requested = buildauthorworkandpassage(author, work, passage, authordict, workdict, dbcursor)
	ao = requested['authorobject']
	wo = requested['workobject']
	psg = requested['passagelist']

	if not work:
		wo = makeanemptywork('gr0000w000')

	# bool
	useheadwords = session['headwordindexing']

	allworks = list()
	output = list()
	cdict = dict()
	valid = True

	if ao and work and psg:
		# subsection of a work of an author
		poll[pollid].statusis('Preparing a partial index to {t}'.format(t=wo.title))
		startandstop = textsegmentfindstartandstop(ao, wo, psg, dbcursor)
		startline = startandstop['startline']
		endline = startandstop['endline']
		cdict = {wo.universalid: (startline, endline)}
	elif ao and work:
		# one work
		poll[pollid].statusis('Preparing an index to {t}'.format(t=wo.title))
		startline = wo.starts
		endline = wo.ends
		cdict = {wo.universalid: (startline, endline)}
	elif ao:
		# whole author
		allworks = ['{w}  ⇒ {t}'.format(w=w.universalid[6:10], t=w.title) for w in ao.listofworks]
		allworks.sort()
		poll[pollid].statusis('Preparing an index to the works of {a}'.format(a=ao.shortname))
		for wkid in ao.listworkids():
			cdict[wkid] = (workdict[wkid].starts, workdict[wkid].ends)
	else:
		# we do not have a valid selection
		valid = False
		output = ['invalid input']

	if valid:
		output = buildindextowork(cdict, poll[pollid], useheadwords, dbcursor)

	# get ready to send stuff to the page
	count = len(output)

	try:
		locale.setlocale(locale.LC_ALL, 'en_US')
		count = locale.format_string('%d', count, grouping=True)
	except locale.Error:
		count = str(count)

	poll[pollid].statusis('Preparing the index HTML')
	indexhtml = wordindextohtmltable(output, useheadwords)

	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)
	poll[pollid].deactivate()

	results = dict()
	results['authorname'] = avoidsmallvariants(ao.shortname)
	results['title'] = avoidsmallvariants(wo.title)
	results['structure'] = avoidsmallvariants(wo.citation())
	results['worksegment'] = '.'.join(psg)
	results['elapsed'] = buildtime
	results['wordsfound'] = count
	results['indexhtml'] = indexhtml
	results['keytoworks'] = allworks
	results['newjs'] = supplementalindexjs()

	results = json.dumps(results)

	dbconnection.connectioncleanup()
	del poll[pollid]

	return results


@hipparchia.route('/indexspan/<searchid>/<author>/<work>/<startpoint>/<endpoint>')
def buildindextospan(searchid: str, author: str, work: str, startpoint: str, endpoint: str):
	"""

	build an index to a subset of a work:
		Cic., De Or. 2.3 - 2.20
		"GET /indexspan/117aba39/lt0474/037/2|3/2|20 HTTP/1.1"

	:param searchid:
	:param author:
	:param work:
	:param startpoint:
	:param endpoint:
	:return:
	"""

	# print('startpoint, endpoint', startpoint, endpoint)
	probeforsessionvariables()

	pollid = validatepollid(searchid)

	starttime = time.time()

	poll[pollid] = ProgressPoll(pollid)
	poll[pollid].activate()

	dbconnection = ConnectionObject('autocommit')
	dbcursor = dbconnection.cursor()

	requested = buildauthorworkandpassage(author, work, startpoint, authordict, workdict, dbcursor, endpoint=endpoint)
	ao = requested['authorobject']
	wo = requested['workobject']
	start = requested['passagelist']
	stop = requested['endpointlist']

	allworks = list()
	output = list()
	cdict = dict()
	valid = True
	useheadwords = session['headwordindexing']

	poll[pollid].statusis('Preparing a partial index to {t}'.format(t=wo.title))
	firstlinenumber = finddblinefromincompletelocus(wo, start, dbcursor)
	lastlinenumber = finddblinefromincompletelocus(wo, stop, dbcursor, findlastline=True)
	if firstlinenumber['code'] == 'success' and lastlinenumber['code'] == 'success':
		cdict = {wo.universalid: (firstlinenumber['line'], lastlinenumber['line'])}
		startln = dblineintolineobject(grabonelinefromwork(ao.universalid, firstlinenumber['line'], dbcursor))
		stopln = dblineintolineobject(grabonelinefromwork(ao.universalid, lastlinenumber['line'], dbcursor))
	else:
		msg = '"indexspan/" could not find first and last: {a}w{b} - {c} TO {d}'
		consolewarning(msg.format(a=author, b=work, c=startpoint, d=endpoint))
		startln = makeablankline(work, 0)
		stopln = makeablankline(work, 1)
		valid = False

	if valid:
		output = buildindextowork(cdict, poll[pollid], useheadwords, dbcursor)

	# get ready to send stuff to the page
	count = len(output)

	try:
		locale.setlocale(locale.LC_ALL, 'en_US')
		count = locale.format_string('%d', count, grouping=True)
	except locale.Error:
		count = str(count)

	poll[pollid].statusis('Preparing the index HTML')
	indexhtml = wordindextohtmltable(output, useheadwords)

	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)
	poll[pollid].deactivate()

	results = dict()
	results['authorname'] = avoidsmallvariants(ao.shortname)
	results['title'] = avoidsmallvariants(wo.title)
	results['structure'] = avoidsmallvariants(wo.citation())
	results['worksegment'] = 'from {a} to {b}'.format(a=startln.shortlocus(), b=stopln.shortlocus())
	results['elapsed'] = buildtime
	results['wordsfound'] = count
	results['indexhtml'] = indexhtml
	results['keytoworks'] = allworks
	results['newjs'] = supplementalindexjs()

	results = json.dumps(results)

	dbconnection.connectioncleanup()
	del poll[pollid]

	return results


@hipparchia.route('/textof/<author>')
@hipparchia.route('/textof/<author>/<work>')
@hipparchia.route('/textof/<author>/<work>/<passage>')
def textmaker(author: str, work=None, passage=None):
	"""
	build a text suitable for display
	:return:
	"""

	probeforsessionvariables()

	dbconnection = ConnectionObject('autocommit')
	dbcursor = dbconnection.cursor()

	linesevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	requested = buildauthorworkandpassage(author, work, passage, authordict, workdict, dbcursor)
	ao = requested['authorobject']
	wo = requested['workobject']
	psg = requested['passagelist']

	if ao and wo:
		# we have both an author and a work, maybe we also have a subset of the work
		if not psg:
			# whole work
			startline = wo.starts
			endline = wo.ends
		else:
			startandstop = textsegmentfindstartandstop(ao, wo, psg, dbcursor)
			startline = startandstop['startline']
			endline = startandstop['endline']
		texthtml = buildtext(wo.universalid, startline, endline, linesevery, dbcursor)
	else:
		texthtml = str()

	if hipparchia.config['INSISTUPONSTANDARDANGLEBRACKETS']:
		texthtml = gtltsubstitutes(texthtml)

	results = dict()
	results['authorname'] = avoidsmallvariants(ao.shortname)
	results['title'] = avoidsmallvariants(wo.title)
	results['structure'] = avoidsmallvariants(wo.citation())
	results['worksegment'] = '.'.join(psg)
	results['texthtml'] = texthtml

	results = json.dumps(results)

	dbconnection.connectioncleanup()

	return results


@hipparchia.route('/textofspan//<author>/<work>/<startpoint>/<endpoint>')
def buildtexttospan(author: str, work: str, startpoint: str, endpoint: str):
	"""

	build a text of a span:


	:param author:
	:param work:
	:param startpoint:
	:param endpoint:
	:return:
	"""

	probeforsessionvariables()

	dbconnection = ConnectionObject('autocommit')
	dbcursor = dbconnection.cursor()

	linesevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	requested = buildauthorworkandpassage(author, work, startpoint, authordict, workdict, dbcursor, endpoint=endpoint)
	ao = requested['authorobject']
	wo = requested['workobject']
	start = requested['passagelist']
	stop = requested['endpointlist']

	firstlinenumber = finddblinefromincompletelocus(wo, start, dbcursor)
	lastlinenumber = finddblinefromincompletelocus(wo, stop, dbcursor, findlastline=True)
	texthtml = str()
	if firstlinenumber['code'] == 'success' and lastlinenumber['code'] == 'success':
		fl = firstlinenumber['line']
		ll = lastlinenumber['line']
		texthtml = buildtext(wo.universalid, fl, ll, linesevery, dbcursor)
		startln = dblineintolineobject(grabonelinefromwork(ao.universalid, fl, dbcursor))
		stopln = dblineintolineobject(grabonelinefromwork(ao.universalid, ll, dbcursor))
	else:
		msg = '"buildtexttospan/" could not find first and last: {a}w{b} - {c} TO {d}'
		consolewarning(msg.format(a=author, b=work, c=startpoint, d=endpoint))
		startln = makeablankline(work, 0)
		stopln = makeablankline(work, 1)
		valid = False

	if hipparchia.config['INSISTUPONSTANDARDANGLEBRACKETS']:
		texthtml = gtltsubstitutes(texthtml)

	results = dict()
	results['authorname'] = avoidsmallvariants(ao.shortname)
	results['title'] = avoidsmallvariants(wo.title)
	results['structure'] = avoidsmallvariants(wo.citation())
	results['worksegment'] = 'from {a} to {b}'.format(a=startln.shortlocus(), b=stopln.shortlocus())
	results['texthtml'] = texthtml

	results = json.dumps(results)

	dbconnection.connectioncleanup()

	return results
