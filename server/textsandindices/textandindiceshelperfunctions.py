# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from collections import deque
from multiprocessing import Manager, Process

from server import hipparchia
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork
from server.dbsupport.miscdbfunctions import makeanemptyauthor, makeanemptywork
from server.formatting.wordformatting import depunct
from server.hipparchiaobjects.connectionobject import PooledConnectionObject
from server.lexica.lexicalookups import lookformorphologymatches
from server.searching.searchfunctions import atsignwhereclauses
from server.threading.mpthreadcount import setthreadcount


def tcparserequest(request, authordict, workdict):
	"""

	return the author, work, and locus requested
	also some other handy variable derived from these items

	:param request:
	:param authordict:
	:param workdict:
	:return:
	"""

	uid = depunct(request.args.get('auth', ''))
	workid = depunct(request.args.get('work', ''))

	allowed = ',;|'
	locus = depunct(request.args.get('locus', ''), allowed)

	workdb = uid + 'w' + workid
	
	if uid != str():
		try:
			ao = authordict[uid]
			if len(workdb) == 10:
				try:
					wo = workdict[workdb]
				except KeyError:
					wo = makeanemptywork('gr0000w000')
			else:
					wo = makeanemptywork('gr0000w000')
		except KeyError:
			ao = makeanemptyauthor('gr0000')
			wo = makeanemptywork('gr0000w000')
		
		passage = locus.split('|')
		passage.reverse()

	else:
		ao = makeanemptyauthor('gr0000')
		wo = makeanemptywork('gr0000w000')
		passage = list()
	
	req = dict()
	
	req['authorobject'] = ao
	req['workobject'] = wo
	req['passagelist'] = passage
	req['rawlocus'] = locus
	
	return req


def textsegmentfindstartandstop(authorobject, workobject, passageaslist, cursor):
	"""
	find the first and last lines of a work segment
	:return:
	"""
	
	p = tuple(passageaslist)
	lookforline = finddblinefromincompletelocus(workobject, p, cursor)
	# assuming that lookforline['code'] == 'success'
	# lookforline['code'] is (allegedly) only relevant to the Perseus lookup problem where a bad locus can be sent
	foundline = lookforline['line']
	line = grabonelinefromwork(authorobject.universalid, foundline, cursor)
	lo = dblineintolineobject(line)
	
	# let's say you looked for 'book 2' of something that has 'book, chapter, line'
	# that means that you want everything that has the same level2 value as the lineobject
	# build a where clause
	passageaslist.reverse()
	atloc = '|'.join(passageaslist)
	selection = '{uid}_AT_{line}'.format(uid=workobject.universalid, line=atloc)
	
	w = atsignwhereclauses(selection, '=', {authorobject.universalid: authorobject})
	d = [workobject.universalid]
	qw = str()
	for i in range(0, len(w)):
		qw += 'AND (' + w[i][0] + ') '
		d.append(w[i][1])

	query = 'SELECT index FROM {au} WHERE wkuniversalid=%s {whr} ORDER BY index DESC LIMIT 1'.format(au=authorobject.universalid, whr=qw)
	data = tuple(d)

	cursor.execute(query, data)
	found = cursor.fetchone()
	
	startandstop = dict()
	startandstop['startline'] = lo.index
	startandstop['endline'] = found[0]

	return startandstop


def wordindextohtmltable(indexingoutput, useheadwords):
	"""
	pre-pack the concordance output into an html table so that the page JS can just iterate through a set of lines when the time comes
	each result in the list is itself a list: [word, count, lociwherefound]
	
	input:
		('sum¹', 'sunt', 1, '1.1')
		('superus', 'summa', 1, '1.4')
		...
	:param indexingoutput:
	:return:
	"""

	if len(indexingoutput) < hipparchia.config['CLICKABLEINDEXEDWORDSCAP'] or hipparchia.config['CLICKABLEINDEXEDWORDSCAP'] < 0:
		thwd = '<td class="headword"><indexobserved id="{wd}">{wd}</indexobserved></td>'
		thom = '<td class="word"><span class="homonym"><indexobserved id="{wd}">{wd}</indexobserved></td>'
		twor = '<td class="word"><indexobserved id="{wd}">{wd}</indexobserved></td>'
	else:
		thwd = '<td class="headword">{wd}</td>'
		thom = '<td class="word"><span class="homonym">{wd}</td>'
		twor = '<td class="word">{wd}</td>'

	previousheadword = str()

	outputlines = deque()
	if useheadwords:
		boilerplate = """
		[nb: <span class="word"><span class="homonym">homonyms</span></span> 
		are listed under every known headword and their <span class="word">
		<span class="homonym">display differs</span></span> from that of 
		<span class="word">unambiguous entries</span>]
		<br>
		<br>	
		"""

		tablehead = """
		<table>
		<tr>
			<th class="indextable">headword</th>
			<th class="indextable">word</th>
			<th class="indextable">count</th>
			<th class="indextable">passages</th>
		</tr>
		"""
		outputlines.append(boilerplate)
		outputlines.append(tablehead)
	else:
		tablehead = """
		<table>
		<tr>
			<th class="indextable">word</th>
			<th class="indextable">count</th>
			<th class="indextable">passages</th>
		</tr>
		"""
		outputlines.append(tablehead)

	for i in indexingoutput:
		outputlines.append('<tr>')
		headword = i[0]
		observedword = i[1]
		if useheadwords and headword != previousheadword:
			outputlines.append(thwd.format(wd=headword))
			previousheadword = headword
		elif useheadwords and headword == previousheadword:
			outputlines.append('<td class="headword">&nbsp;</td>')
		if i[4] == 'isahomonymn':
			outputlines.append(thom.format(wd=observedword))
		else:
			outputlines.append(twor.format(wd=observedword))
		outputlines.append('<td class="count">{ct}</td>'.format(ct=i[2]))
		outputlines.append('<td class="passages">{psg}</td>'.format(psg=i[3]))
		outputlines.append('</tr>')
	outputlines.append('</table>')

	html = '\n'.join(list(outputlines))

	return html


def dictmerger(masterdict, targetdict):
	"""

	a more complex version also present in HipparchiaBuilder

	there does not seem to be a quicker way to do this with comprehensions since they have
	to break the job up into too many parts in order to non-destructively merge the intersection

	intersection = masterdict.keys() & targetdict.keys()
	mast = masterdict.keys() - intersection
	targ = targetdict.keys() - intersection

	inter = {i: masterdict[i] + targetdict[i] for i in intersection}
	m = {k: masterdict[k] for k in mast}
	t = {k: targetdict[k] for k in targ}

	merged = {**m, **t, **inter}

	:param masterdict:
	:param targetdict:
	:return:
	"""

	for item in targetdict:
		if item in masterdict:
			masterdict[item] += targetdict[item]
		else:
			masterdict[item] = targetdict[item]

	return masterdict


def setcontinuationvalue(thisline, previousline, previouseditorialcontinuationvalue, brktype, openfinder=None, closefinder=None):
	"""

	used to determine if a bracket span is running for multiple lines

	type should be something that findactivebrackethighlighting() can return and that bracketopenedbutnotclosed()
	can receive: 'square', 'curly', etc.

	openfinder & closefinder used to send pre-compiled bracket sniffing regex so that you do not compile inside a loop

	:param thisline:
	:param previousline:
	:param previouseditorialcontinuationvalue:
	:param brktype:
	:param openfinder:
	:param closefinder:
	:return:
	"""

	if thisline.bracketopenedbutnotclosed(brktype, bracketfinder=openfinder):
		newcv = True
	elif not thisline.samelevelas(previousline):
		newcv = False
	elif (previousline.bracketopenedbutnotclosed(brktype, bracketfinder=openfinder) or previouseditorialcontinuationvalue) and not thisline.bracketclosed(brktype, bracketfinder=closefinder):
		newcv = True
	else:
		newcv = False

	return newcv


def getrequiredmorphobjects(listofterms):
	"""

	take a list of terms

	find the morphobjects associated with them

	:param terms:
	:return:
	"""
	manager = Manager()
	terms = manager.list(listofterms)
	morphobjects = manager.dict()
	workers = setthreadcount()

	oneconnectionperworker = {i: PooledConnectionObject() for i in range(workers)}

	jobs = [Process(target=mpmorphology, args=(terms, morphobjects, oneconnectionperworker[i])) for i in range(workers)]
	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	for c in oneconnectionperworker:
		oneconnectionperworker[c].connectioncleanup()

	return morphobjects


def mpmorphology(terms, morphobjects, dbconnection):
	"""

	build a dict of morphology objects

	:param terms:
	:param morphobjects:
	:param commitcount:
	:return:
	"""

	dbcursor = dbconnection.cursor()

	commitcount = 0
	while terms:
		commitcount += 1
		try:
			term = terms.pop()
		except IndexError:
			term = None

		if term:
			mo = lookformorphologymatches(term, dbcursor)
			if mo:
				morphobjects[term] = mo
			else:
				morphobjects[term] = None

		dbconnection.checkneedtocommit(commitcount)

	return morphobjects
