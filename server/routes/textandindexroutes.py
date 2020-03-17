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
from server.authentication.authenticationwrapper import requireauthentication
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork, makeablankline
from server.dbsupport.miscdbfunctions import makeanemptyauthor, makeanemptywork
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.jsformatting import supplementalindexjs
from server.formatting.miscformatting import consolewarning, validatepollid
from server.formatting.wordformatting import avoidsmallvariants
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.parsingobjects import IndexmakerInputParsingObject, TextmakerInputParsingObject
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.listsandsession.checksession import probeforsessionvariables
from server.startup import progresspolldict, workdict
from server.textsandindices.indexmaker import buildindextowork
from server.textsandindices.textandindiceshelperfunctions import textsegmentfindstartandstop, wordindextohtmltable
from server.textsandindices.textbuilder import buildtext


@hipparchia.route('/indexto/<searchid>/<author>')
@hipparchia.route('/indexto/<searchid>/<author>/<work>')
@hipparchia.route('/indexto/<searchid>/<author>/<work>/<passage>')
@hipparchia.route('/indexto/<searchid>/<author>/<work>/<passage>/<endpoint>')
@requireauthentication
def buildindexto(searchid: str, author: str, work=None, passage=None, endpoint=None, citationdelimiter='|'):
	"""
	build a complete index to a an author, work, or segment of a work

	:return:
	"""

	probeforsessionvariables()

	pollid = validatepollid(searchid)

	starttime = time.time()

	progresspolldict[pollid] = ProgressPoll(pollid)
	progresspolldict[pollid].activate()

	dbconnection = ConnectionObject('autocommit')
	dbcursor = dbconnection.cursor()

	po = IndexmakerInputParsingObject(author, work, passage, endpoint, citationdelimiter)

	ao = po.authorobject
	wo = po.workobject
	psg = po.passageaslist
	stop = po.endpointlist

	if not work:
		wo = makeanemptywork('gr0000w000')

	# bool
	useheadwords = session['headwordindexing']

	allworks = list()
	output = list()
	cdict = dict()
	segmenttext = str()
	valid = True

	if ao and work and psg and stop:
		start = psg
		firstlinenumber = finddblinefromincompletelocus(wo, start, dbcursor)
		lastlinenumber = finddblinefromincompletelocus(wo, stop, dbcursor, findlastline=True)
		if firstlinenumber['code'] == 'success' and lastlinenumber['code'] == 'success':
			cdict = {wo.universalid: (firstlinenumber['line'], lastlinenumber['line'])}
			startln = dblineintolineobject(grabonelinefromwork(ao.universalid, firstlinenumber['line'], dbcursor))
			stopln = dblineintolineobject(grabonelinefromwork(ao.universalid, lastlinenumber['line'], dbcursor))
		else:
			msg = '"indexspan/" could not find first and last: {a}w{b} - {c} TO {d}'
			consolewarning(msg.format(a=author, b=work, c=passage, d=endpoint))
			startln = makeablankline(work, 0)
			stopln = makeablankline(work, 1)
			valid = False
		segmenttext = 'from {a} to {b}'.format(a=startln.shortlocus(), b=stopln.shortlocus())
	elif ao and work and psg:
		# subsection of a work of an author
		progresspolldict[pollid].statusis('Preparing a partial index to {t}'.format(t=wo.title))
		startandstop = textsegmentfindstartandstop(ao, wo, psg, dbcursor)
		startline = startandstop['startline']
		endline = startandstop['endline']
		cdict = {wo.universalid: (startline, endline)}
	elif ao and work:
		# one work
		progresspolldict[pollid].statusis('Preparing an index to {t}'.format(t=wo.title))
		startline = wo.starts
		endline = wo.ends
		cdict = {wo.universalid: (startline, endline)}
	elif ao:
		# whole author
		allworks = ['{w}  ⇒ {t}'.format(w=w.universalid[6:10], t=w.title) for w in ao.listofworks]
		allworks.sort()
		progresspolldict[pollid].statusis('Preparing an index to the works of {a}'.format(a=ao.shortname))
		for wkid in ao.listworkids():
			cdict[wkid] = (workdict[wkid].starts, workdict[wkid].ends)
	else:
		# we do not have a valid selection
		valid = False
		output = ['invalid input']

	if not stop:
		segmenttext = '.'.join(psg)

	if valid:
		output = buildindextowork(cdict, progresspolldict[pollid], useheadwords, dbcursor)

	# get ready to send stuff to the page
	count = len(output)

	try:
		locale.setlocale(locale.LC_ALL, 'en_US')
		count = locale.format_string('%d', count, grouping=True)
	except locale.Error:
		count = str(count)

	progresspolldict[pollid].statusis('Preparing the index HTML')
	indexhtml = wordindextohtmltable(output, useheadwords)

	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)
	progresspolldict[pollid].deactivate()

	if not ao:
		ao = makeanemptyauthor('gr0000')

	results = dict()
	results['authorname'] = avoidsmallvariants(ao.shortname)
	results['title'] = avoidsmallvariants(wo.title)
	results['structure'] = avoidsmallvariants(wo.citation())
	results['worksegment'] = segmenttext
	results['elapsed'] = buildtime
	results['wordsfound'] = count
	results['indexhtml'] = indexhtml
	results['keytoworks'] = allworks
	results['newjs'] = supplementalindexjs()
	results = json.dumps(results)

	dbconnection.connectioncleanup()
	del progresspolldict[pollid]

	return results


@hipparchia.route('/indextorawlocus/<searchid>/<author>/<work>/<location>')
@hipparchia.route('/indextorawlocus/<searchid>/<author>/<work>/<location>/<endpoint>')
@requireauthentication
def indexfromrawlocus(searchid: str, author: str, work=None, location=None, endpoint=None):
	"""

	the rawlocus version of buildindexto()

	:param searchid:
	:param author:
	:param work:
	:param location:
	:param endpoint:
	:return:
	"""

	delimiter = '.'

	return buildindexto(searchid, author, work, location, endpoint, citationdelimiter=delimiter)


@hipparchia.route('/textof/<author>')
@hipparchia.route('/textof/<author>/<work>')
@hipparchia.route('/textof/<author>/<work>/<passage>')
@hipparchia.route('/textof/<author>/<work>/<passage>/<endpoint>')
@requireauthentication
def textmaker(author: str, work=None, passage=None, endpoint=None, citationdelimiter='|'):
	"""
	build a text suitable for display

		"GET /textof/lt0474/024/20/30"

	:return:
	"""

	probeforsessionvariables()

	dbconnection = ConnectionObject('autocommit')
	dbcursor = dbconnection.cursor()

	linesevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	po = TextmakerInputParsingObject(author, work, passage, endpoint, citationdelimiter)

	ao = po.authorobject
	wo = po.workobject

	segmenttext = str()

	if ao and wo:
		# we have both an author and a work, maybe we also have a subset of the work
		if endpoint:
			firstlinenumber = finddblinefromincompletelocus(wo, po.passageaslist, dbcursor)
			lastlinenumber = finddblinefromincompletelocus(wo, po.endpointlist, dbcursor, findlastline=True)
			if firstlinenumber['code'] == 'success' and lastlinenumber['code'] == 'success':
				startline = firstlinenumber['line']
				endline = lastlinenumber['line']
				startlnobj = dblineintolineobject(grabonelinefromwork(ao.universalid, startline, dbcursor))
				stoplnobj = dblineintolineobject(grabonelinefromwork(ao.universalid, endline, dbcursor))
			else:
				msg = '"buildtexttospan/" could not find first and last: {a}w{b} - {c} TO {d}'
				consolewarning(msg.format(a=author, b=work, c=passage, d=endpoint))
				startlnobj = makeablankline(work, 0)
				stoplnobj = makeablankline(work, 1)
				startline = 0
				endline = 1
			segmenttext = 'from {a} to {b}'.format(a=startlnobj.shortlocus(), b=stoplnobj.shortlocus())
		elif not po.passageaslist:
			# whole work
			startline = wo.starts
			endline = wo.ends
		else:
			startandstop = textsegmentfindstartandstop(ao, wo, po.passageaslist, dbcursor)
			startline = startandstop['startline']
			endline = startandstop['endline']
		texthtml = buildtext(wo.universalid, startline, endline, linesevery, dbcursor)
	else:
		texthtml = str()

	if hipparchia.config['INSISTUPONSTANDARDANGLEBRACKETS']:
		texthtml = gtltsubstitutes(texthtml)

	if not segmenttext:
		segmenttext = '.'.join(po.passageaslist)

	if not ao or not wo:
		ao = makeanemptyauthor('gr0000')
		wo = makeanemptywork('gr0000w000')

	results = dict()
	results['authorname'] = avoidsmallvariants(ao.shortname)
	results['title'] = avoidsmallvariants(wo.title)
	results['structure'] = avoidsmallvariants(wo.citation())
	results['worksegment'] = segmenttext
	results['texthtml'] = texthtml

	results = json.dumps(results)

	dbconnection.connectioncleanup()

	return results


@hipparchia.route('/textofrawlocus/<author>/<work>/<location>')
@hipparchia.route('/textofrawlocus/<author>/<work>/<location>/<endpoint>')
@requireauthentication
def texmakerfromrawlocus(author: str, work: str, location: str, endpoint=None):
	"""

	the rawlocus version of textmaker()

	:param author:
	:param work:
	:param location:
	:param endpoint:
	:return:
	"""

	delimiter = '.'

	return textmaker(author, work, location, endpoint, citationdelimiter=delimiter)
