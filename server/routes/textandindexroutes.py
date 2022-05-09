# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import re
import time

from flask import session

try:
	from rich import print
except ImportError:
	pass

from server import hipparchia
from server.authentication.authenticationwrapper import requireauthentication
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork, makeablankline
from server.dbsupport.dblinefunctions import grabbundlesoflines
from server.dbsupport.miscdbfunctions import makeanemptyauthor, makeanemptywork
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.jsformatting import supplementalindexjs, supplementalvocablistjs
from server.formatting.miscformatting import consolewarning, validatepollid
from server.formatting.wordformatting import avoidsmallvariants, depunct
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.parsingobjects import IndexmakerInputParsingObject, TextmakerInputParsingObject
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.listsandsession.checksession import probeforsessionvariables
from server.listsandsession.genericlistfunctions import flattenlistoflists, polytonicsort
from server.startup import progresspolldict, workdict
from server.textsandindices.indexmaker import buildindextowork
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects, textsegmentfindstartandstop, \
	wordindextohtmltable
from server.textsandindices.textbuilder import buildtext

JSON_STR = str


@hipparchia.route('/text/<action>/<one>')
@hipparchia.route('/text/<action>/<one>/<two>')
@hipparchia.route('/text/<action>/<one>/<two>/<three>')
@hipparchia.route('/text/<action>/<one>/<two>/<three>/<four>')
@hipparchia.route('/text/<action>/<one>/<two>/<three>/<four>/<five>')
@requireauthentication
def textgetter(action: str, one=None, two=None, three=None, four=None, five=None) -> JSON_STR:
	"""

	dispatcher for "/text/..." requests

	"""

	one = depunct(one)
	two = depunct(two)
	three = depunct(three, allowedpunctuationsting='.|')
	four = depunct(four, allowedpunctuationsting='.|')
	five = depunct(five, allowedpunctuationsting='.|')

	knownfunctions = {'index':
							{'fnc': buildindexto, 'param': [one, two, three, four, five]},
						'vocab':
							{'fnc': generatevocabfor, 'param': [one, two, three, four, five]},
						'vocab_rawloc':
							{'fnc': vocabfromrawlocus, 'param': [one, two, three, four, five]},
						'index_rawloc':
							{'fnc': indexfromrawlocus, 'param': [one, two, three, four, five]},
						'make':
							{'fnc': textmaker, 'param': [one, two, three, four]},
						'make_rawloc':
							{'fnc': texmakerfromrawlocus, 'param': [one, two, three, four]},
						}

	if action not in knownfunctions:
		return json.dumps(str())

	f = knownfunctions[action]['fnc']
	p = knownfunctions[action]['param']

	j = f(*p)

	if hipparchia.config['JSONDEBUGMODE']:
		print('/text/{f}\n\t{j}'.format(f=action, j=j))

	return j


def buildindexto(searchid: str, author: str, work=None, passage=None, endpoint=None, citationdelimiter='|', justvocab=False) -> JSON_STR:
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

	if valid and justvocab:
		dbconnection.connectioncleanup()
		del progresspolldict[pollid]
		return cdict

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


def generatevocabfor(searchid: str, author: str, work=None, passage=None, endpoint=None, citationdelimiter='|') -> JSON_STR:
	"""

	given a text span
		figure out what words are used by this span
		then provide a vocabulary list from that list

	ex:
		http://localhost:5000/vocabularyfor/SEARCHID/lt0631/001/1/20

	this is a lot like building an index so we just leverage buildindexto() but pull away from it after the initial
	bit where we establish endpoints and get ready to gather the lines

	:param searchid:
	:param author:
	:param work:
	:param passage:
	:param endpoint:
	:param citationdelimiter:
	:return:
	"""

	starttime = time.time()
	segmenttext = str()

	dbconnection = ConnectionObject('autocommit')
	dbcursor = dbconnection.cursor()

	justvocab = True

	cdict = buildindexto(searchid, author, work, passage, endpoint, citationdelimiter, justvocab)
	lineobjects = grabbundlesoflines(cdict, dbcursor)

	allwords = [l.wordset() for l in lineobjects]
	allwords = set(flattenlistoflists(allwords))

	morphobjects = getrequiredmorphobjects(allwords)
	# 'dominatio': <server.hipparchiaobjects.dbtextobjects.dbMorphologyObject object at 0x14ab92d68>, ...

	baseformsmorphobjects = list()
	for m in morphobjects:
		try:
			baseformsmorphobjects.extend(morphobjects[m].getpossible())
		except AttributeError:
			# 'NoneType' object has no attribute 'getpossible'
			pass

	vocabset = {'{w} ~~~ {t}'.format(w=b.getbaseform(), t=b.gettranslation()) for b in baseformsmorphobjects if b.gettranslation()}
	vocabset = {v.split(' ~~~ ')[0]: v.split(' ~~~ ')[1].strip() for v in vocabset}
	vocabset = {v: vocabset[v] for v in vocabset if vocabset[v]}

	# the following can be in entries and will cause problems...:
	#   <tr opt="n">which had become milder</tr>

	vocabset = {v: re.sub(r'<(|/)tr.*?>', str(), vocabset[v]) for v in vocabset}

	# now you have { word1: definition1, word2: definition2, ...}

	vocabcounter = [b.getbaseform() for b in baseformsmorphobjects if b.gettranslation()]
	vocabcount = dict()
	for v in vocabcounter:
		try:
			vocabcount[v] += 1
		except KeyError:
			vocabcount[v] = 1

	po = IndexmakerInputParsingObject(author, work, passage, endpoint, citationdelimiter)

	ao = po.authorobject
	wo = po.workobject
	psg = po.passageaslist
	stop = po.endpointlist

	tableheadtemplate = """
	<tr>
		<th class="vocabtable">word</th>
		<th class="vocabtable">count</th>
		<th class="vocabtable">definitions</th>
	</tr>
	"""

	tablerowtemplate = """
	<tr>
		<td class="word"><vocabobserved id="{w}">{w}</vocabobserved></td>
		<td class="count">{c}</td>
		<td class="trans">{t}</td>
	</tr>
	"""

	tablehtml = """
	<table>
		{head}
		{rows}
	</table>
	"""

	byfrequency = session['indexbyfrequency']

	if not byfrequency:
		rowhtml = [tablerowtemplate.format(w=k, t=vocabset[k], c=vocabcount[k]) for k in polytonicsort(vocabset.keys())]
	else:
		vc = [(vocabcount[v], v) for v in vocabcount]
		vc.sort(reverse=True)
		vk = [v[1] for v in vc]
		vk = [v for v in vk if v in vocabset]
		rowhtml = [tablerowtemplate.format(w=k, t=vocabset[k], c=vocabcount[k]) for k in vk]

	wordsfound = len(rowhtml)
	rowhtml = '\n'.join(rowhtml)

	vocabhtml = tablehtml.format(head=tableheadtemplate, rows=rowhtml)

	if not ao:
		ao = makeanemptyauthor('gr0000')

	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)

	if not stop:
		segmenttext = '.'.join(psg)

	results = dict()
	results['authorname'] = avoidsmallvariants(ao.shortname)
	results['title'] = avoidsmallvariants(wo.title)
	results['structure'] = avoidsmallvariants(wo.citation())
	results['worksegment'] = segmenttext
	results['elapsed'] = buildtime
	results['wordsfound'] = wordsfound
	results['texthtml'] = vocabhtml
	results['keytoworks'] = str()
	results['newjs'] = supplementalvocablistjs()
	results = json.dumps(results)

	# print('vocabhtml', vocabhtml)

	return results


def vocabfromrawlocus(searchid: str, author: str, work=None, location=None, endpoint=None) -> JSON_STR:
	"""

	the rawlocus version of generatevocabfor()

	:param searchid:
	:param author:
	:param work:
	:param location:
	:param endpoint:
	:return:
	"""

	delimiter = '.'

	return generatevocabfor(searchid, author, work, location, endpoint, citationdelimiter=delimiter)


def indexfromrawlocus(searchid: str, author: str, work=None, location=None, endpoint=None) -> JSON_STR:
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


def textmaker(author: str, work=None, passage=None, endpoint=None, citationdelimiter='|') -> JSON_STR:
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

	# consolewarning('po.passageaslist: {p}'.format(p=po.passageaslist))

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


def texmakerfromrawlocus(author: str, work: str, location: str, endpoint=None) -> JSON_STR:
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
