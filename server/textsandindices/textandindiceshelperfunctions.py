# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from collections import deque
from multiprocessing import Manager, Process
from typing import List

from server import hipparchia
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork
from server.dbsupport.lexicaldbfunctions import lookformorphologymatches
from server.dbsupport.miscdbfunctions import icanpickleconnections
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.searching.searchhelperfunctions import atsignwhereclauses
from server.threading.mpthreadcount import setthreadcount


def textsegmentfindstartandstop(authorobject, workobject, passageaslist, cursor) -> dict:
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


def wordindextohtmltable(indexingoutput: List[tuple], useheadwords: bool) -> str:
	"""

	pre-pack the concordance output into an html table so that the page JS can just iterate through a set of lines when the time comes
	each result in the list is itself a list: [word, count, lociwherefound]

	:param indexingoutput:
	:param useheadwords:
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
		are listed under every possible headword and their <span class="word">
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


def dictmerger(masterdict: dict, targetdict: dict):
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


def setcontinuationvalue(thisline: dbWorkLine, previousline: dbWorkLine, previouseditorialcontinuationvalue: bool, brktype: str, openfinder=None, closefinder=None):
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


def getrequiredmorphobjects(setofterms: set, furtherdeabbreviate=False) -> dict:
	"""

	take a set of terms

	find the morphobjects associated with them

	:param terms:
	:return:
	"""
	manager = Manager()
	terms = manager.list(setofterms)
	morphobjects = manager.dict()
	workers = setthreadcount()

	if icanpickleconnections():
		oneconnectionperworker = {i: ConnectionObject() for i in range(workers)}
	else:
		oneconnectionperworker = {i: None for i in range(workers)}

	jobs = [Process(target=mpmorphology, args=(terms, furtherdeabbreviate, morphobjects, oneconnectionperworker[i]))
	        for i in range(workers)]
	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	if oneconnectionperworker[0]:
		for c in oneconnectionperworker:
			oneconnectionperworker[c].connectioncleanup()

	return morphobjects


def mpmorphology(terms: list, furtherdeabbreviate: bool, dictofmorphobjects, dbconnection: ConnectionObject) -> dict:
	"""

	build a dict of morphology objects

	:param terms:
	:param furtherdeabbreviate:
	:param dictofmorphobjects:
	:param dbconnection:
	:return:
	"""

	if not dbconnection:
		dbconnection = ConnectionObject()

	dbcursor = dbconnection.cursor()

	commitcount = 0
	while terms:
		commitcount += 1
		dbconnection.checkneedtocommit(commitcount)
		try:
			term = terms.pop()
		except IndexError:
			term = None

		if term:
			mo = lookformorphologymatches(term, dbcursor, furtherdeabbreviate=furtherdeabbreviate)
			if mo:
				dictofmorphobjects[term] = mo
			else:
				dictofmorphobjects[term] = None

	return dictofmorphobjects


def paragraphformatting(listoflines: List[dbWorkLine]) -> List[dbWorkLine]:
	"""

	look for formatting that spans collections of lines

	rewrite individual lines to make them part of this formatting block

	presupposes "htmlifydatabase = y" in config.ini for HipparchiaBuilder

	:param listoflines:
	:return:
	"""

	spanopenfinder = re.compile(r'<span class="(.*?)">')
	spanclosefinder = re.compile(r'</span>')

	memory = str()

	# it is possible that this will not yield balanced HTML: the original data is unbalanced
	# e.g. <span class="normal"> furenti similis. <hmu_serviusformatting>sane quidam volunt, Vergilium</span></hmu_serviusformatting>
	# this gets 'fixed' by hmurewrite() which yields '</span></span>' instead

	for line in listoflines:
		paragraphtag = spanopenedbutnotclosed(line.markedup, spanopenfinder, spanclosefinder)
		# print('[{m}], [{p}],\t{l}'.format(m=memory, p=paragraphtag, l=line.markedup))
		if memory and paragraphtag:
			# you are finishing old business and starting new business
			# e.g: 	Ἑλλάδα</span>. καὶ ἑτέρωθι πάλιν <span class="expanded_text">εἶτα τὸν τοῦτο τὸ μη-
			line.markedup = '<span class="{t}">{ln}</span>'.format(t=memory, ln=line.markedup)
			memory = paragraphtag
		if memory and not paragraphtag:
			# you have ongoing business
			if spanclosedbeforeopened(line.markedup, spanopenfinder, spanclosefinder):
				# [a] it might be over:
				# e.g.: μου πράϲϲοντα</span>. καὶ πάλιν ἑτέρωθι βουλόμενοϲ δεῖ-
				line.markedup = '<span class="{t}">{ln}'.format(t=memory, ln=line.markedup)
				memory = str()
			else:
				# [b] it might be continuing
				# e.g.: the line "τίκα δὴ μάλα δώϲειν δίκην ἀφείλετο τὴν ἀλή-" in
				# πραγμάτων προάγειν τὸν λόγον ϲεμνὸν ϲφόδρα. <span class="expanded_text">εἰ μὴ
				# Θεϲπιαὶ καὶ Πλαταιαὶ καὶ τὸ Θηβαίουϲ αὐ-
				# τίκα δὴ μάλα δώϲειν δίκην ἀφείλετο τὴν ἀλή-
				# θειαν</span> ** ἀλλ’ οἱ λέγοντεϲ τὰ περὶ Θεϲπιέων καὶ Πλα-
				line.markedup = '<span class="{t}">{ln}</span>'.format(t=memory, ln=line.markedup)
		if paragraphtag:
			# you are starting something new
			line.markedup = '{ln}</span>'.format(ln=line.markedup)
			memory = paragraphtag
		line.generatehtmlversion()
	return listoflines


def spanopenedbutnotclosed(linehtml, openfinder, closefinder) -> str:
	"""

	we are looking for paragraphs of formatting that are just getting started

	return the tag name if there is an <hmu_...> and not a corresponding </hmu...> in the line

	otherwise return false

	:return:
	"""

	opentag = str()
	opened = list(re.finditer(openfinder, linehtml))
	closed = list(re.finditer(closefinder, linehtml))

	if not opened and not closed:
		return str()

	if len(opened) > len(closed):
		opentag = opened[-1].group(1)

	if len(opened) == len(closed) and opened[-1].end() > closed[-1].end():
		opentag = opened[-1].group(1)

	return opentag


def spanclosedbeforeopened(linehtml, openfinder, closefinder) -> bool:
	"""

	true if there is a stray '</span>' at the head of the line

	:return:
	"""

	opened = list(re.finditer(openfinder, linehtml))
	closed = list(re.finditer(closefinder, linehtml))

	if not closed:
		return False

	if closed and not opened:
		return True

	if opened[-1].end() < closed[-1].end():
		return True

	return False


# slated for removal

def oldparagraphformatting(listoflines: List[dbWorkLine]) -> List[dbWorkLine]:
	"""

	look for formatting that spans collections of lines

	rewrite individual lines to make them part of this paragraph

	:param listoflines:
	:return:
	"""

	memory = None
	for line in listoflines:
		paragraphtag = line.hmuopenedbutnotclosed()
		if paragraphtag:
			memory = paragraphtag
			# it is possible that this will not yield balanced HTML
			# e.g. <span class="normal"> furenti similis. <hmu_serviusformatting>sane quidam volunt, Vergilium</span></hmu_serviusformatting>
			# this gets 'fixed' by hmurewrite() which yields '</span></span>' instead
			line.markedup = '{ln}</{t}>'.format(t=memory, ln=line.markedup)
		if memory and line.hmuclosedbeforeopened(memory):
			# it is possible that this will not yield balanced HTML
			line.markedup = '<{t}>{ln}'.format(t=memory, ln=line.markedup)
			memory = None
		if memory and not paragraphtag:
			# 'and not' because the first condition already rewrote this line
			line.markedup = '<{t}>{ln}</{t}>'.format(t=memory, ln=line.markedup)
		line.generatehtmlversion()
	return listoflines

