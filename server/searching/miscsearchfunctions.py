# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re
import subprocess
import sys
import time
from multiprocessing import JoinableQueue
from os import path
from string import punctuation
from typing import List

from flask import request, session

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject, makeablankline, worklinetemplate, grabonelinefromwork
from server.dbsupport.lexicaldbfunctions import findcountsviawordcountstable, querytotalwordcounts
from server.formatting.betacodetounicode import replacegreekbetacode
from server.formatting.miscformatting import debugmessage, consolewarning
from server.formatting.wordformatting import badpucntwithbackslash, minimumgreek, removegravity, wordlistintoregex
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.listsandsession.checksession import probeforsessionvariables, justtlg
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.startup import lemmatadict
from server.threading.mpthreadcount import setthreadcount

JSONDICT = str


def cleaninitialquery(seeking: str) -> str:
	"""

	there is a problem: all of the nasty injection strings are also rexeg strings
	if you let people do regex, you also open the door for trouble
	the securty has to be instituted elsewhere: read-only db is 90% of the job?

	:param seeking:
	:return:
	"""

	seeking = seeking[:hipparchia.config['MAXIMUMQUERYLENGTH']]

	# things you never need to see and are not part of a (for us) possible regex expression
	# a lot of this may be hard to type, but if you cut and paste a result to make a new search, this stuff is in there
	extrapuncttostrip = ',;#'

	if hipparchia.config['FOOLISHLYALLOWREGEX']:
		stripset = {x for x in extrapuncttostrip}.union({x for x in badpucntwithbackslash})
		stripset = stripset - {x for x in hipparchia.config['FOOLISHLYALLOWREGEX']}
	else:
		stripset = extrapuncttostrip + badpucntwithbackslash

	strippunct = str().join(list(stripset))

	seeking = re.sub(r'[{p}]'.format(p=re.escape(strippunct)), '', seeking)

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

	whitespace = ' '

	query = query.lower()
	prefix = None
	suffix = None
	startfrom = 0
	endat = 0

	if query[0] == whitespace:
		# otherwise you will miss words that start lines because they do not have a leading whitespace
		prefix = r'(^|\s)'
		startfrom = 1
	elif query[0:1] == '\s':
		prefix = r'(^|\s)'
		startfrom = 2

	if query[-1] == whitespace:
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
	wk = None

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
	whitespace = ' '
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

	aggregate = whitespace.join(text)
	aggregate = re.sub(r'\s\s', whitespace, aggregate)
	aggregate = ' {a} '.format(a=aggregate)

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

	whitespace = ' '
	stillneedtofindterm = True
	searchterms = searchphrase.split(whitespace)
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
			longestterm = [(len(t), t) for t in searchphrase.split(whitespace) if t]
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


def dblooknear(index: int, distanceinlines: int, secondterm: str, workid: str, usecolumn: str, dbcursor) -> bool:
	"""

	search for a term within a range of lines

	return True or False if it is found

	:param index:
	:param distanceinlines:
	:param secondterm:
	:param workid:
	:param usecolumn:
	:param dbcursor:
	:return:
	"""

	table = workid[0:6]
	q = 'SELECT index FROM {db} WHERE ((index BETWEEN %s AND %s) AND wkuniversalid = %s AND {c} ~ %s)'.format(db=table, c=usecolumn)
	d = (index - distanceinlines, index + distanceinlines, workid, secondterm)
	dbcursor.execute(q, d)
	hit = dbcursor.fetchall()
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

	whitespace = ' '

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

	if seeking == whitespace:
		seeking = str()

	if proximate == whitespace:
		proximate = str()

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


def rebuildsearchobjectviasearchorder(so: SearchObject) -> SearchObject:
	"""

	rewrite the searchobject so that you look for the less common things first

	"""

	if so.lemmaone and so.lemmatwo:
		hwone = querytotalwordcounts(so.lemmaone.dictionaryentry)
		hwtwo = querytotalwordcounts(so.lemmatwo.dictionaryentry)
		# from server.hipparchiaobjects.wordcountobjects import dbWordCountObject
		# print('{a}: {b}, {c}: {d}'.format(a=so.lemmaone.dictionaryentry, b=hwone.t, c=so.lemmatwo.dictionaryentry, d=hwtwo.t))
		if hwtwo.t < hwone.t:
			tmp = so.lemmaone
			so.lemmaone = so.lemmatwo
			so.lemmatwo = tmp
	elif so.lemma or so.proximatelemma:
		pass
	elif so.accented or re.search(r'^[a-z]', so.termone) and so.near:
		# choose the necessarily faster option
		unomdifiedskg = massagesearchtermsforwhitespace(so.seeking)
		unmodifiedprx = so.proximate
		leastcommon = findleastcommonterm(unomdifiedskg + ' ' + unmodifiedprx, so.accented)
		if leastcommon != unomdifiedskg:
			tmp = so.termone
			so.termone = so.termtwo
			so.termtwo = tmp
	elif len(so.termtwo) > len(so.termone) and so.near:
		# look for the longest word first since that is probably the quicker route
		# but you can't swap searchingfor and proximate this way in a 'is not near' search without yielding the wrong focus
		tmp = so.termone
		so.termone = so.termtwo
		so.termtwo = tmp

	return so


def grableadingandlagging(hitline: dbWorkLine, searchobject: SearchObject, cursor) -> dict:
	"""

	take a dbline and grab the N words in front of it and after it

	it would be a good idea to have an autocommit connection here?

	:param hitline:
	:param searchobject:
	:param cursor:
	:return:
	"""

	so = searchobject
	# look out for off-by-one errors
	distance = so.distance + 1

	if so.lemma:
		seeking = wordlistintoregex(so.lemma.formlist)
		so.usewordlist = 'polytonic'
	else:
		seeking = so.termone

	searchzone = getattr(hitline, so.usewordlist)

	match = re.search(r'{s}'.format(s=seeking), searchzone)
	# but what if you just found 'paucitate' inside of 'paucitatem'?
	# you will have 'm' left over and this will throw off your distance-in-words count
	past = None
	upto = None
	lagging = list()
	leading = list()
	ucount = 0
	pcount = 0

	try:
		past = searchzone[match.end():].strip()
	except AttributeError:
		# AttributeError: 'NoneType' object has no attribute 'end'
		pass

	try:
		upto = searchzone[:match.start()].strip()
	except AttributeError:
		pass

	if upto:
		ucount = len([x for x in upto.split(' ') if x])
		lagging = [x for x in upto.split(' ') if x]

	if past:
		pcount = len([x for x in past.split(' ') if x])
		leading = [x for x in past.split(' ') if x]

	atline = hitline.index

	while ucount < distance + 1:
		atline -= 1
		try:
			previous = dblineintolineobject(grabonelinefromwork(hitline.authorid, atline, cursor))
		except TypeError:
			# 'NoneType' object is not subscriptable
			previous = makeablankline(hitline.authorid, -1)
			ucount = 999
		lagging = previous.wordlist(so.usewordlist) + lagging
		ucount += previous.wordcount()
	lagging = lagging[-1 * (distance - 1):]
	lagging = ' '.join(lagging)

	atline = hitline.index
	while pcount < distance + 1:
		atline += 1
		try:
			nextline = dblineintolineobject(grabonelinefromwork(hitline.authorid, atline, cursor))
		except TypeError:
			# 'NoneType' object is not subscriptable
			nextline = makeablankline(hitline.authorid, -1)
			pcount = 999
		leading += nextline.wordlist(so.usewordlist)
		pcount += nextline.wordcount()
	leading = leading[:distance - 1]
	leading = ' '.join(leading)

	returndict = {'lag': lagging, 'lead': leading}

	return returndict


def redishitintodbworkline(redisresult: JSONDICT) -> dbWorkLine:
	"""

	convert a golang struct stored as json in the redis server into dbWorkLine objects

	"""

	# type DbWorkline struct {
	# 	WkUID		string
	# 	TbIndex		int
	# 	Lvl5Value	string
	# 	Lvl4Value	string
	# 	Lvl3Value	string
	# 	Lvl2Value	string
	# 	Lvl1Value	string
	# 	Lvl0Value	string
	# 	MarkedUp	string
	# 	Accented	string
	# 	Stripped	string
	# 	Hypenated	string
	# 	Annotations	string
	# }

	ln = json.loads(redisresult)
	lineobject = dbWorkLine(ln['WkUID'], ln['TbIndex'], ln['Lvl5Value'], ln['Lvl4Value'], ln['Lvl3Value'],
							ln['Lvl2Value'], ln['Lvl1Value'], ln['Lvl0Value'], ln['MarkedUp'], ln['Accented'],
							ln['Stripped'], ln['Hypenated'], ln['Annotations'])
	return lineobject


def getexternalhelperpath(theprogram=hipparchia.config['EXTERNALBINARYNAME']):
	"""

	find the path

	"""
	if not hipparchia.config['EXTERNALWSGI']:
		basepath = sys.path[0]
	else:
		basepath = path.abspath(hipparchia.config['HARDCODEDPATH'])

	thepath = '{b}/server/{e}/{p}'.format(b=basepath, e=hipparchia.config['EXTERNALBINARYDIR'], p=theprogram)
	return thepath


def haveexternalhelper(thepath):
	"""

	is it there?

	"""
	if path.isfile(thepath):
		return True
	else:
		return False


def genericexternalcliexecution(theprogram: str, formatterfunction, so: SearchObject) -> str:
	"""

	call a golang cli helper; report the result key

	this basically sets you up for either GOLANGCLIBINARYNAME or GOLANGVECTORBINARYNAME

	and you will need the relevant formatgolangXXXarguments() too

	note that the last line of the output of the binary is super-important: it needs to be the result key

	"""
	resultrediskey = str()

	command = getexternalhelperpath(theprogram)
	commandandarguments = formatterfunction(command, so)

	try:
		result = subprocess.run(commandandarguments, capture_output=True)
	except FileNotFoundError:
		consolewarning('cannot find the golang executable "{x}'.format(x=command), color='red')
		return resultrediskey

	if result.returncode == 0:
		stdo = result.stdout.decode('UTF-8')
		outputlist = stdo.split('\n')
		for o in outputlist:
			debugmessage(o)
		resultrediskey = [o for o in outputlist if o]
		resultrediskey = resultrediskey[-1]
		# but this looks like: 'results sent to redis as ff128837_results'
		# so you need a little more work
		resultrediskey = resultrediskey.split()[-1]
	else:
		e = repr(result)
		e = re.sub(r'\\n', '\n', e)
		e = re.sub(r'\\t', '\t', e)
		consolewarning('{c} returned an error'.format(c=hipparchia.config['EXTERNALBINARYNAME']), color='red')
		consolewarning('{e}'.format(e=e), color='yellow')
		# debugmessage(repr(result))

	return resultrediskey


def formatexternalgrabberarguments(command: str, so: SearchObject) -> list:
	"""
	Usage of ./HipparchiaGoDBHelper:
	  -c int
			max hit count (default 200)
	  -k string
			redis key to use (default "go")
	  -l int
			logging level: 0 is silent; 5 is very noisy (default 1)
	  -p string
			psql logon information (as a JSON string) (default "{\"Host\": \"localhost\", \"Port\": 5432, \"User\": \"hippa_wr\", \"Pass\": \"\", \"DBName\": \"hipparchiaDB\"}")
	  -r string
			redis logon information (as a JSON string) (default "{\"Addr\": \"localhost:6379\", \"Password\": \"\", \"DB\": 0}")
	  -sv
			[vectors] assert that this is a vectorizing run
	  -svb string
			[vectors] the bagging method: choices are alternates, flat, unlemmatized, winnertakesall (default "winnertakesall")
	  -svdb string
			[vectors][for manual debugging] db to grab from (default "lt0448")
	  -sve int
			[vectors][for manual debugging] last line to grab (default 26)
	  -svs int
			[vectors][for manual debugging] first line to grab (default 1)
	  -t int
			number of goroutines to dispatch (default 5)
	  -v    print version and exit

	"""
	if 'Rust' not in hipparchia.config['EXTERNALBINARYNAME']:
		# irritating '--x' vs '-x' issue...
		prefix = '-'
	else:
		prefix = '--'

	arguments = dict()

	arguments['k'] = so.searchid
	arguments['c'] = so.cap
	arguments['t'] = setthreadcount()
	arguments['l'] = hipparchia.config['EXTERNALCLILOGLEVEL']

	rld = {'Addr': '{a}:{b}'.format(a=hipparchia.config['REDISHOST'], b=hipparchia.config['REDISPORT']),
		   'Password': str(),
		   'DB': hipparchia.config['REDISDBID']}
	arguments['r'] = json.dumps(rld)

	# rw user by default atm; can do this smarter...
	psd = {'Host': hipparchia.config['DBHOST'],
		   'Port': hipparchia.config['DBPORT'],
		   'User': hipparchia.config['DBWRITEUSER'],
		   'Pass': hipparchia.config['DBWRITEPASS'],
		   'DBName': hipparchia.config['DBNAME']}

	if hipparchia.config['EXTERNALBINARYKNOWSLOGININFO']:
		pass
	else:
		arguments['p'] = json.dumps(psd)

	argumentlist = [['{p}{k}'.format(k=k, p=prefix), '{v}'.format(v=arguments[k])] for k in arguments]
	argumentlist = flattenlistoflists(argumentlist)
	commandandarguments = [command] + argumentlist

	return commandandarguments
