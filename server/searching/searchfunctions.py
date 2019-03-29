# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time
from multiprocessing import JoinableQueue
from string import punctuation
from typing import List

from flask import request, session

from server import hipparchia
from server.commandlineoptions import getcommandlineargs
from server.dbsupport.dblinefunctions import dblineintolineobject, makeablankline, worklinetemplate
from server.dbsupport.lexicaldbfunctions import findcountsviawordcountstable
from server.formatting.betacodetounicode import replacegreekbetacode
from server.formatting.wordformatting import badpucntwithbackslash, minimumgreek, removegravity
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.checksession import probeforsessionvariables, justtlg
from server.startup import lemmatadict


def cleaninitialquery(seeking: str) -> str:
	"""

	there is a problem: all of the nasty injection strings are also rexeg strings
	if you let people do regex, you also open the door for trouble
	the securty has to be instituted elsewhere: read-only db is 90% of the job?

	:param seeking:
	:return:
	"""

	# things you never need to see and are not part of a (for us) possible regex expression
	# a lot of this may be hard to type, but if you cut and paste a result to make a new search, this stuff is in there
	extrapunct = ',;#'

	seeking = re.sub(r'[{p}]'.format(p=re.escape(extrapunct + badpucntwithbackslash)), '', seeking)

	# split() later at ' ' means confusion if you have double spaces
	seeking = re.sub(r' {2,}', r' ', seeking)

	if hipparchia.config['HOBBLEREGEX']:
		seeking = re.sub(r'\d', '', seeking)
		allowedpunct = '[].^$\\\''
		badpunct = ''.join(set(punctuation) - set(allowedpunct))
		seeking = re.sub(r'[' + re.escape(badpunct) + ']', '', seeking)

	return seeking


def massagesearchtermsforwhitespace(query: str) -> str:
	"""

	fiddle with the query before execution to handle whitespace start/end of line issues

	:param query:
	:return:
	"""

	query = query.lower()
	prefix = None
	suffix = None

	if query[0] == ' ':
		# otherwise you will miss words that start lines because they do not have a leading whitespace
		prefix = r'(^|\s)'
		startfrom = 1
	elif query[0:1] == '\s':
		prefix = r'(^|\s)'
		startfrom = 2

	if query[-1] == ' ':
		# otherwise you will miss words that end lines because they do not have a trailing whitespace
		suffix = r'(\s|$)'
		endat = -1
	elif query[-2:] == '\s':
		suffix = r'(\s|$)'
		endat = -2

	if prefix:
		query = prefix + query[startfrom:]

	if suffix:
		query = query[:endat] + suffix

	return query


def atsignwhereclauses(uidwithatsign, operand, authors) -> List[tuple]:
	"""

	the '_AT_' syntax is used to restrict the scope of a search

	in order to restrict a search to a portion of a work, you will need a where clause
	this builds it out of something like 'gr0003w001_AT_3|12' (Thuc., Bk 3, Ch 12)

	sample output:
		[('level_02_value=%s ', '1'), ('level_01_value=%s ', '3')]

	:param uidwithatsign:
	:param operand:
	:param authors:
	:return:
	"""

	whereclausetuples = list()

	a = uidwithatsign[:6]
	locus = uidwithatsign[14:].split('|')

	ao = authors[a]
	for w in ao.listofworks:
		if w.universalid == uidwithatsign[0:10]:
			wk = w

	wklvls = list(wk.structure.keys())
	wklvls.reverse()

	index = -1
	for l in locus:
		index += 1
		lvstr = 'level_0{lvl}_value{o}%s '.format(lvl=wklvls[index], o=operand)
		whereclausetuples.append((lvstr, l))

	# print('whereclausetuples',whereclausetuples)

	return whereclausetuples


def buildbetweenwhereextension(authortable: str, searchobject: SearchObject) -> str:
	"""
	
	sample return if you are doing a 'between' search (typically a subset of a literary author):
	
		(index BETWEEN 1846 AND 2856) AND (index NOT BETWEEN 1846 AND 2061) AND
	
	ultimately this will turn into something like:

		q/d SELECT * FROM gr0032 WHERE (index BETWEEN 1846 AND 2856) AND (index NOT BETWEEN 1846 AND 2061) AND ( stripped_line ~* %s )  LIMIT 200 ('βαλλ',)
		[i.e., βαλλ in Xenophon, Hellenica 3 less Hellenica 3.1]
	
		SELECT * FROM gr0085 WHERE ( (index BETWEEN 1157 AND 2262) OR (index BETWEEN 1 AND 1156) OR (index BETWEEN 7440 AND 8548) OR (index BETWEEN 6281 AND 7439) OR (index BETWEEN 2263 AND 3416) OR (index BETWEEN 4562 AND 6280) OR (index BETWEEN 3417 AND 4561) ) AND  ( accented_line ~* %s )  LIMIT 200
		[searching 'Trag.' work genre w/in Aeschylus]
	
	:param authortable: 
	:param searchobject: 
	:return: 
	"""

	r = searchobject.indexrestrictions[authortable]
	whereclauseadditions = str()
	bds = str()
	oms = str()

	if not r['where']:
		return whereclauseadditions
	try:
		bounds = r['where']['listofboundaries']
	except KeyError:
		bounds = None

	template = '(index BETWEEN {min} AND {max})'
	# WHERE (index BETWEEN 2885 AND 4633) OR (index BETWEEN 7921 AND 9913)'
	if bounds:
		wheres = [template.format(min=b[0], max=b[1]) for b in bounds]
		bds = ' OR '.join(wheres)

	try:
		omits = r['where']['listofomissions']
	except KeyError:
		omits = None

	template = '(index NOT BETWEEN {min} AND {max})'
	if omits:
		wheres = [template.format(min=o[0], max=o[1]) for o in omits]
		oms = ' AND '.join(wheres)

	if bounds and omits:
		whereclauseadditions = '( {bds} ) AND ( {oms} ) AND'.format(bds=bds, oms=oms)
	elif bounds and not omits:
		whereclauseadditions = '( {bds} ) AND'.format(bds=bds)
	elif omits and not bounds:
		whereclauseadditions = '( {oms} ) AND'.format(oms=oms)

	return whereclauseadditions


def lookoutsideoftheline(linenumber: int, numberofextrawords: int, workid: str, searchobject: SearchObject, cursor) -> str:
	"""

	grab a line and add the N words at the tail and head of the previous and next lines
	this will let you search for phrases that fall along a line break "και δη | και"

	if you wanted to look for 'ἀείδων Ϲπάρτηϲ'
	you need this individual line:
		2.1.374  δεξιτερὴν γὰρ ἀνέϲχε μετάρϲιον, ὡϲ πρὶν ἀείδων
	to turn extend out to:
		ὑφαίνων δεξιτερὴν γὰρ ἀνέϲχε μετάρϲιον ὡϲ πρὶν ἀείδων ϲπάρτηϲ

	:param linenumber:
	:param numberofextrawords:
	:param workid:
	:param searchobject:
	:param cursor:
	:return:
	"""

	workdbname = workid[0:6]

	query = 'SELECT {wltmp} FROM {db} WHERE index BETWEEN %s AND %s ORDER BY index ASC'.format(wltmp=worklinetemplate, db=workdbname)
	data = (linenumber - 1, linenumber + 1)
	cursor.execute(query, data)
	results = cursor.fetchall()

	lines = [dblineintolineobject(r) for r in results]
	# will get key errors if there is no linenumber+/-1
	if len(lines) == 2:
		if lines[0].index == linenumber:
			lines = [makeablankline(workdbname, linenumber - 1)] + lines
		else:
			lines.append(makeablankline(workdbname, linenumber + 1))
	if len(lines) == 1:
		lines = [makeablankline(workdbname, linenumber - 1)] + lines
		lines.append(makeablankline(workdbname, linenumber + 1))

	text = list()
	for line in lines:
		wordsinline = line.wordlist(searchobject.usewordlist)
		if line.index == linenumber - 1:
			text = wordsinline[(numberofextrawords * -1):]
		elif line.index == linenumber:
			text += wordsinline
		elif line.index == linenumber + 1:
			text += wordsinline[0:numberofextrawords]

	aggregate = ' '.join(text)
	aggregate = re.sub(r'\s\s', r' ', aggregate)
	aggregate = ' ' + aggregate + ' '

	return aggregate


def findleastcommonterm(searchphrase: str, accentsneeded: bool) -> str:
	"""

	use the wordcounts to determine the best word to pick first

	sadly partial words are in the wordcounts so
		Sought "ϲτρατηγὸϲ" within 6 words of "φιλοτιμ"
	will give you a 'max' of
		max [(11, 'φιλοτιμ'), (4494, 'ϲτρατηγόϲ')]

	and that might not be the wises way to go

	might need to institute a check to make sure an accented letter is in a word, but is this starting to be
	too much trouble for too little gain?

	:param searchphrase:
	:param accentsneeded:
	:return:
	"""

	stillneedtofindterm = True
	searchterms = searchphrase.split(' ')
	searchterms = [x for x in searchterms if x]
	leastcommonterm = searchterms[0]

	if accentsneeded or re.search(r'^[a-z]', searchterms[0]):
		# note that graves have been eliminated from the wordcounts; so we have to do the same here
		# but we still need access to the actual search terms, hence the dict
		# a second issue: 'v' is not in the wordcounts, but you might be searching for it
		# third, whitespace means you might be passing '(^|\\s)κατὰ' instead of 'κατὰ'
		searchterms = [re.sub(r'\(.*?\)', '', t) for t in searchterms]
		searchterms = [re.sub(r'v', 'u', t) for t in searchterms]
		searchterms = {removegravity(t): t for t in searchterms}

		counts = [findcountsviawordcountstable(k) for k in searchterms.keys()]
		# counts [('βεβήλων', 84, 84, 0, 0, 0, 0), ('ὀλίγοϲ', 596, 589, 0, 3, 4, 0)]
		# counts [('imperatores', 307, 7, 275, 3, 4, 18), ('paucitate', 42, 0, 42, 0, 0, 0)]
		totals = [(c[1], c[0]) for c in counts if c]
		maxval = sorted(totals, reverse=False)
		try:
			leastcommonterm = searchterms[maxval[0][1]]
			stillneedtofindterm = False
		except:
			# failed so you will do plan b in a moment
			pass

	if stillneedtofindterm:
		try:
			longestterm = searchterms[0]
		except KeyError:
			# did you send me a bunch of regex that just got wiped?
			longestterm = [(len(t), t) for t in searchphrase.split(' ') if t]
			longestterm.sort(reverse=True)
			return longestterm[0][1]
		for term in searchterms:
			if len(term) > len(longestterm):
				longestterm = term
		leastcommonterm = longestterm

	return leastcommonterm


def findleastcommontermcount(searchphrase: str, accentsneeded: bool) -> int:
	"""

	use the wordcounts to determine the best word to pick first

	:param listofterms:
	:return:
	"""
	fewesthits = -1
	searchterms = searchphrase.split(' ')
	searchterms = [x for x in searchterms if x]
	if accentsneeded or re.search(r'^[a-z]', searchterms[0]):
		# note that graves have been eliminated from the wordcounts; so we have to do the same here
		# but we still need access to the actual search terms, hence the dict
		# a second issue: 'v' is not in the wordcounts, but you might be searching for it
		# third, whitespace means you might be passing '(^|\\s)κατὰ' instead of 'κατὰ'
		searchterms = [re.sub(r'\(.*?\)', '', t) for t in searchterms]
		searchterms = [re.sub(r'v', 'u', t) for t in searchterms]
		searchterms = {removegravity(t): t for t in searchterms}

		counts = [findcountsviawordcountstable(k) for k in searchterms.keys()]
		# counts [('βεβήλων', 84, 84, 0, 0, 0, 0), ('ὀλίγοϲ', 596, 589, 0, 3, 4, 0)]
		totals = [(c[1], c[0]) for c in counts if c]
		maxval = sorted(totals, reverse=False)
		try:
			fewesthits = maxval[0][0]
		except:
			# failed so you will do plan b in a moment
			pass

	return fewesthits


def dblooknear(index: int, distanceinlines: int, secondterm: str, workid: str, usecolumn: str, cursor) -> bool:
	"""

	search for a term within a range of lines

	return True or False if it is found

	:param index:
	:param distanceinlines:
	:param secondterm:
	:param workid:
	:param usecolumn:
	:param cursor:
	:return:
	"""

	table = workid[0:6]
	q = 'SELECT index FROM {db} WHERE ((index BETWEEN %s AND %s) AND wkuniversalid = %s AND {c} ~ %s)'.format(db=table, c=usecolumn)
	d = (index - distanceinlines, index + distanceinlines, workid, secondterm)
	cursor.execute(q, d)
	hit = cursor.fetchall()
	if hit:
		return True
	else:
		return False


def buildsearchobject(searchid: str, therequest: request, thesession: session) -> SearchObject:
	"""

	generic searchobject builder

	:param searchid:
	:param therequest:
	:param thesession:
	:return:
	"""

	if not searchid:
		searchid = str(int(time.time()))

	probeforsessionvariables()

	# a search can take 30s or more and the user might alter the session while the search is running
	# by toggling onehit, etc that can be a problem, so freeze the values now and rely on this instead
	# of some moving target
	frozensession = thesession.copy()

	# need to sanitize input at least a bit: remove digits and punctuation
	# dispatcher will do searchtermcharactersubstitutions() and massagesearchtermsforwhitespace() to take
	# care of lunate sigma, etc.

	seeking = cleaninitialquery(therequest.args.get('skg', ''))
	proximate = cleaninitialquery(therequest.args.get('prx', ''))
	inputlemma = cleaninitialquery(therequest.args.get('lem', ''))
	inputproximatelemma = cleaninitialquery(therequest.args.get('plm', ''))

	try:
		lemma = lemmatadict[inputlemma]
	except KeyError:
		lemma = None

	# print('lo forms', lemma.formlist)

	try:
		proximatelemma = lemmatadict[inputproximatelemma]
	except KeyError:
		proximatelemma = None

	replacebeta = False

	if hipparchia.config['UNIVERSALASSUMESBETACODE'] and re.search('[a-zA-Z]', seeking):
		# why the 'and' condition:
		#   sending unicode 'οὐθενὸϲ' to the betacode function will result in 0 hits
		#   this is something that could/should be debugged within that function,
		#   but in practice it is silly to allow hybrid betacode/unicode? this only
		#   makes the life of a person who wants unicode+regex w/ a betacode option more difficult
		replacebeta = True

	commandlineargs = getcommandlineargs()
	if commandlineargs.forceuniversalbetacode:
		replacebeta = True

	if hipparchia.config['TLGASSUMESBETACODE']:
		if justtlg() and (re.search('[a-zA-Z]', seeking) or re.search('[a-zA-Z]', proximate)) and not re.search(minimumgreek, seeking) and not re.search(minimumgreek, proximate):
			replacebeta = True

	if replacebeta:
		seeking = seeking.upper()
		seeking = replacegreekbetacode(seeking)
		seeking = seeking.lower()
		proximate = proximate.upper()
		proximate = replacegreekbetacode(proximate)
		proximate = proximate.lower()

	so = SearchObject(searchid, seeking, proximate, lemma, proximatelemma, frozensession)

	return so


def loadsearchqueue(iterable, workers):
	"""

	simple function to put our values into a queue

	:param iterable:
	:param workers:
	:return:
	"""
	q = JoinableQueue()
	for item in iterable:
		q.put(item)
	# poison pills to stop the queue
	for _ in range(workers):
		q.put(None)
	return q
