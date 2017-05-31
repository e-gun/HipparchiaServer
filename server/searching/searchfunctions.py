# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from string import punctuation

from server import hipparchia
from server.dbsupport.dbfunctions import dblineintolineobject, makeablankline
from server.helperfunctions import removegravity
from server.lexica.lexicalookups import findcountsviawordcountstable


def cleaninitialquery(seeking):
	"""

	there is a problem: all of the nasty injection strings are also rexeg strings
	if you let people do regex, you also open the door for trouble
	the securty has to be instituted elsewhere: read-only db is 90% of the job?

	:param query:
	:return:
	"""

	# things you never need to see and are not part of a (for us) possible regex expression
	badpunct = ',;#'
	extrapunct = """‵’‘·“”„'"—†⌈⌋⌊⟫⟪❵❴⟧⟦«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓"""

	seeking = re.sub(r'[' + re.escape(badpunct + extrapunct) + ']', '', seeking)

	if hipparchia.config['HOBBLEREGEX'] == 'yes':
		seeking = re.sub(r'\d', '', seeking)
		allowedpunct = '[].^$\''
		badpunct = ''.join(set(punctuation) - set(allowedpunct))
		seeking = re.sub(r'[' + re.escape(badpunct) + ']', '', seeking)

	return seeking


def massagesearchtermsforwhitespace(query):
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


def atsignwhereclauses(uidwithatsign, operand, authors):
	"""
	in order to restrict a search to a portion of a work, you will need a where clause
	this builds it out of something like 'gr0003w001_AT_3|12' (Thuc., Bk 3, Ch 12)

	sample output:
		[('level_02_value=%s ', '1'), ('level_01_value=%s ', '3')]

	:param uidwithatsign:
	:param operand: this should be either '=' or '!='
	:return: a tuple consisting of the SQL string and the value to be passed via %s
	"""

	whereclausetuples = []

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
		lvstr = 'level_0' + str(wklvls[index]) + '_value' + operand + '%s '
		whereclausetuples.append((lvstr, l))

	# print('whereclausetuples',whereclausetuples)

	return whereclausetuples


def substringsearch(seeking, authortable, searchobject, cursor, templimit=None):
	"""

	actually one of the most basic search types: look for a string/substring
	this is brute force: you wade through the full text of the work

	note that we are not pulling seeking from the searchobject

	the whereclause is built conditionally:
	
	sample 'unrestricted':
		SELECT * FROM gr0059 WHERE  ( stripped_line ~* %s )  LIMIT 200 ('βαλλ',)
	sample 'between':
		SELECT * FROM gr0032 WHERE (index BETWEEN 1846 AND 2856) AND (index NOT BETWEEN 1846 AND 2061) AND ( stripped_line ~* %s )  LIMIT 200 ('βαλλ',)
	sample 'temptable':
		[create the temptable]
		SELECT * FROM in1204 WHERE EXISTS (SELECT 1 FROM in1204_includelist incl WHERE incl.includeindex = in1204.index AND in1204.accented_line ~* %s)  LIMIT 200 ('τούτου',)
			
	:param seeking:
	:param cursor:
	:param workdbname:
	:param authors:
	:return:
	"""

	so = searchobject

	if templimit:
		lim = str(templimit)
	else:
		lim = str(so.cap)

	if so.onehit:
		mylimit = ' LIMIT 1'
	else:
		mylimit = ' LIMIT ' + lim

	mysyntax = '~*'
	found = []

	r = so.indexrestrictions[authortable]
	whereextensions = ''

	if r['type'] == 'temptable':
		# make the table
		q = r['where']['tempquery']
		cursor.execute(q)
		# now you can work with it
		whereextensions = 'EXISTS (SELECT 1 FROM {tbl}_includelist incl WHERE incl.includeindex = {tbl}.index'.format(
			tbl=authortable)
		whr = 'WHERE {xtn} AND {au}.{col} {sy} %s)'.format(au=authortable, col=so.usecolumn, sy=mysyntax, xtn=whereextensions)
	elif r['type'] == 'between':
		whereextensions = buildbetweenwhereextension(authortable, so)
		whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
	elif r['type'] == 'unrestricted':
		whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
	else:
		# should never see this
		print('error in substringsearch(): unknown whereclause type',r['type'])
		whr = 'WHERE ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax)

	qtemplate = 'SELECT * FROM {db} {whr} {l}'
	q = qtemplate.format(db=authortable, whr=whr, l=mylimit)
	d = (seeking,)

	try:
		cursor.execute(q, d)
		found = cursor.fetchall()
	except:
		print('could not execute', q, d)

	return found


def buildbetweenwhereextension(authortable, searchobject):
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
	whereclauseadditions = ''
	bds = ''
	oms = ''

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


def lookoutsideoftheline(linenumber, numberofextrawords, workid, searchobject, cursor):
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
	:param workdbname:
	:param cursor:
	:return:
	"""

	workdbname = workid[0:6]

	query = 'SELECT * FROM {db} WHERE index >= %s AND index <= %s ORDER BY index ASC'.format(db=workdbname)
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

	text = []
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


def findleastcommonterm(searchphrase, accentsneeded):
	"""

	use the wordcounts to determine the best word to pick first

	sadly partial words are in the wordcounts so
		Sought "ϲτρατηγὸϲ" within 6 words of "φιλοτιμ"
	will give you a 'max' of
		max [(11, 'φιλοτιμ'), (4494, 'ϲτρατηγόϲ')]

	and that might not be the wises way to go

	might need to institute a check to make sure an accented letter is in a word, but is this starting to be
	too much trouble for too little gain?

	:param listofterms:
	:return:
	"""
	stillneedtofindterm = True
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
		# counts [('imperatores', 307, 7, 275, 3, 4, 18), ('paucitate', 42, 0, 42, 0, 0, 0)]
		totals = [(c[1], c[0]) for c in counts if c]
		max = sorted(totals, reverse=False)
		try:
			leastcommonterm = searchterms[max[0][1]]
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


def findleastcommontermcount(searchphrase, accentsneeded):
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
		max = sorted(totals, reverse=False)
		try:
			fewesthits = max[0][0]
		except:
			# failed so you will do plan b in a moment
			pass

	return fewesthits


def dblooknear(index, distanceinlines, secondterm, workid, usecolumn, cursor):
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
	q = 'SELECT index FROM {db} WHERE (index > %s AND index < %s AND wkuniversalid = %s AND {c} ~ %s)'.format(db=table, c=usecolumn)
	d = (index - distanceinlines, index + distanceinlines, workid, secondterm)
	cursor.execute(q, d)
	hit = cursor.fetchall()
	if hit:
		return True
	else:
		return False
