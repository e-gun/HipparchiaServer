# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing.managers import ListProxy
from typing import List

from server.dbsupport.dblinefunctions import dblineintolineobject, makeablankline, worklinetemplate
from server.dbsupport.tablefunctions import assignuniquename
from server.hipparchiaobjects.dbtextobjects import dbWorkLine
from server.hipparchiaobjects.helperobjects import QueryCombinator
from server.hipparchiaobjects.searchfunctionobjects import returnsearchfncobject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.searching.searchfunctions import buildbetweenwhereextension, lookoutsideoftheline
from server.searching.substringsearching import substringsearch


def phrasesearch(wkid: str, searchobject: SearchObject, cursor) -> List[dbWorkLine]:
	"""

	a whitespace might mean things are on a new line
	note how horrible something like και δη και is: you will search και first and then...
	subqueryphrasesearch() takes a more or less fixed amount of time; this function is
	faster if you call it with an uncommon word; if you call it with a common word, then
	you will likely search much more slowly than you would with subqueryphrasesearch()

	:param wkid:
	:param activepoll:
	:param searchobject:
	:param cursor:
	:return:
	"""

	so = searchobject
	searchphrase = so.termone
	activepoll = so.poll

	# print('so.leastcommon', so.leastcommon)

	# need a high templimit because you can actually fool "leastcommon"
	# "πλῶϲ θανατώδη" will not find "ἁπλῶϲ θανατώδη": you really wanted the latter (presumably), but
	# "πλῶϲ" is going to be entered as leastcommon, and a search for it will find "ἁπλῶϲ" many, many times
	# as the latter is a common term...

	hits = substringsearch(so.leastcommon, wkid, so, cursor, templimit=999999)

	fullmatches = list()

	while True:
		# since hits is now a generator you can no longer pop til you drop
		for hit in hits:
			# print('hit', hit)
			if len(fullmatches) > so.cap:
				break
			phraselen = len(searchphrase.split(' '))
			# wordklinetemplate in dblinefunctions.py governs the order of things here...
			hitindex = hit[1]
			wordset = lookoutsideoftheline(hitindex, phraselen - 1, wkid, so, cursor)
			if not so.accented:
				wordset = re.sub(r'[.?!;:,·’]', r'', wordset)
			else:
				# the difference is in the apostrophe: δ vs δ’
				wordset = re.sub(r'[.?!;:,·]', r'', wordset)

			if so.near and re.search(searchphrase, wordset):
				fullmatches.append(hit)
				activepoll.addhits(1)
			elif not so.near and re.search(searchphrase, wordset) is None:
				fullmatches.append(hit)
				activepoll.addhits(1)
		break

	return fullmatches


def subqueryphrasesearch(workerid, foundlineobjects: ListProxy, searchphrase: str, listofplacestosearch: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""

	foundlineobjects, searchingfor, searchlist, commitcount, whereclauseinfo, activepoll

	use subquery syntax to grab multi-line windows of text for phrase searching

	line ends and line beginning issues can be overcome this way, but then you have plenty of
	bookkeeping to do to to get the proper results focussed on the right line

	tablestosearch:
		['lt0400', 'lt0022', ...]

	a search inside of Ar., Eth. Eud.:

		SELECT secondpass.index, secondpass.accented_line
				FROM (SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
					(SELECT index, accented_line,
						concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
						FROM gr0086 WHERE ( (index BETWEEN 15982 AND 18745) ) ) firstpass
					) secondpass
				WHERE secondpass.linebundle ~ %s  LIMIT 200

	a search in x., hell and x., mem less book 3 of hell and book 2 of mem:
		SELECT secondpass.index, secondpass.accented_line
				FROM (SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
					(SELECT index, accented_line,
						concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
						FROM gr0032 WHERE ( (index BETWEEN 1 AND 7918) OR (index BETWEEN 7919 AND 11999) ) AND ( (index NOT BETWEEN 1846 AND 2856) AND (index NOT BETWEEN 8845 AND 9864) ) ) firstpass
					) secondpass
				WHERE secondpass.linebundle ~ %s  LIMIT 200

	:return:
	"""

	querytemplate = """
		SELECT secondpass.index, secondpass.{co} FROM 
			(SELECT firstpass.index, firstpass.linebundle, firstpass.{co} FROM
					(SELECT index, {co}, concat({co}, ' ', lead({co}) OVER (ORDER BY index ASC)) AS linebundle
						FROM {db} {whr} ) firstpass
			) secondpass
		WHERE secondpass.linebundle ~ %s {lim}"""

	wheretempate = """
	WHERE EXISTS
		(SELECT 1 FROM {tbl}_includelist_{a} incl WHERE incl.includeindex = {tbl}.index)
	"""

	so = searchobject
	activepoll = so.poll

	# substringsearch() needs ability to CREATE TEMPORARY TABLE
	dbconnection.setreadonly(False)
	cursor = dbconnection.cursor()

	qcomb = QueryCombinator(searchphrase)
	# the last time is the full phrase:  ('one two three four five', '')
	combinations = qcomb.combinations()
	combinations.pop()
	# lines start/end
	sp = re.sub(r'^\s', r'(^|\\s)', searchphrase)
	sp = re.sub(r'\s$', r'(\\s|$)', sp)
	# on the reasoning behind the following substitution see 'DEBUGGING notes: SQL oddities' above
	# sp = re.sub(r' ', r'\\s', sp)

	if not so.onehit:
		lim = ' LIMIT ' + str(so.cap)
	else:
		# the windowing problem means that '1' might be something that gets discarded
		lim = ' LIMIT 5'

	# build incomplete sfo that will handle everything other than iteratethroughsearchlist()
	sfo = returnsearchfncobject(workerid, foundlineobjects, listofplacestosearch, so, dbconnection, None)

	if so.redissearchlist:
		listofplacestosearch = True

	while listofplacestosearch and activepoll.gethits() <= so.cap:
		# sfo.getnextfnc() also takes care of the commitcount
		authortable = sfo.getnextfnc()
		sfo.updatepollremaining()

		if authortable:
			whr = str()
			r = so.indexrestrictions[authortable]
			if r['type'] == 'between':
				indexwedwhere = buildbetweenwhereextension(authortable, so)
				if indexwedwhere != '':
					# indexwedwhere will come back with an extraneous ' AND'
					indexwedwhere = indexwedwhere[:-4]
					whr = 'WHERE {iw}'.format(iw=indexwedwhere)
			elif r['type'] == 'temptable':
				avoidcollisions = assignuniquename()
				q = r['where']['tempquery']
				q = re.sub('_includelist', '_includelist_{a}'.format(a=avoidcollisions), q)
				cursor.execute(q)
				whr = wheretempate.format(tbl=authortable, a=avoidcollisions)

			query = querytemplate.format(db=authortable, co=so.usecolumn, whr=whr, lim=lim)
			data = (sp,)
			# print('subqueryphrasesearch() q,d:',query, data)
			cursor.execute(query, data)
			indices = [i[0] for i in cursor.fetchall()]
			# this will yield a bunch of windows: you need to find the centers; see 'while...' below

			locallineobjects = list()
			if indices:
				for i in indices:
					query = 'SELECT {wtmpl} FROM {tb} WHERE index=%s'.format(wtmpl=worklinetemplate, tb=authortable)
					data = (i,)
					cursor.execute(query, data)
					locallineobjects.append(dblineintolineobject(cursor.fetchone()))

			locallineobjects.reverse()
			# debugging
			# for l in locallineobjects:
			#	print(l.universalid, l.locus(), getattr(l,so.usewordlist))

			gotmyonehit = False
			while locallineobjects and activepoll.gethits() <= so.cap and not gotmyonehit:
				# windows of indices come back: e.g., three lines that look like they match when only one matches [3131, 3132, 3133]
				# figure out which line is really the line with the goods
				# it is not nearly so simple as picking the 2nd element in any run of 3: no always runs of 3 + matches in
				# subsequent lines means that you really should check your work carefully; this is not an especially costly
				# operation relative to the whole search and esp. relative to the speed gains of using a subquery search
				lineobject = locallineobjects.pop()
				if re.search(sp, getattr(lineobject, so.usewordlist)):
					sfo.addnewfindstolistoffinds([lineobject])
					activepoll.addhits(1)
					if so.onehit:
						gotmyonehit = True
				else:
					try:
						nextline = locallineobjects[0]
					except IndexError:
						nextline = makeablankline('gr0000w000', -1)

					if lineobject.wkuinversalid != nextline.wkuinversalid or lineobject.index != (nextline.index - 1):
						# you grabbed the next line on the pile (e.g., index = 9999), not the actual next line (e.g., index = 101)
						# usually you won't get a hit by grabbing the next db line, but sometimes you do...
						query = 'SELECT {wtmpl} FROM {tb} WHERE index=%s'.format(wtmpl=worklinetemplate, tb=authortable)
						data = (lineobject.index + 1,)
						cursor.execute(query, data)
						try:
							nextline = dblineintolineobject(cursor.fetchone())
						except:
							nextline = makeablankline('gr0000w000', -1)

					for c in combinations:
						tail = c[0] + '$'
						head = '^' + c[1]
						# debugging
						# print('re',getattr(lo,so.usewordlist),tail, head, getattr(next,so.usewordlist))

						t = False
						h = False
						try:
							t = re.search(tail, getattr(lineobject, so.usewordlist))
						except re.error:
							pass
						try:
							h = re.search(head, getattr(nextline, so.usewordlist))
						except re.error:
							pass

						if t and h:
							sfo.addnewfindstolistoffinds([lineobject])
							activepoll.addhits(1)
							if so.onehit:
								gotmyonehit = True
		else:
			# redis will return None for authortable if the set is now empty
			listofplacestosearch = None

	sfo.listcleanup()

	return foundlineobjects


"""

notes on lead and lag: examining the next row and the previous row

lead and lag example
	https://fle.github.io/detect-value-changes-between-successive-lines-with-postgresql.html

partitions: [over clauses]
	http://tapoueh.org/blog/2013/08/20-Window-Functions


[a] a span is generated by the subquery clause SQ
select SQ.index, SQ.stripped_line, SQ.nextline
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline
	from lt1212
	where (index > 9000 and index < 9010)
	) SQ

[b] searching within it
select SQ.index, SQ.stripped_line, SQ.nextline
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline
	from lt1212
	where (index > 9000 and index < 9010)
	) SQ
where SQ.stripped_line ~ 'quidam' and SQ.nextline ~ 'ae '

[c] returning a linebundle before and after a hit:

select SQ.index, concat(SQ.prevline, SQ.stripped_line, SQ.nextline) as linebundle
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline,
    lag(stripped_line) over (ORDER BY index asc) as prevline
	from lt1212
	where (index > 0)
	) SQ
where SQ.stripped_line ~ 'et tamen'

[d] peeking at the windows: ﻿
	119174 is where you will find:
		index: 119174
		linebundle: ἆρά γ ἄξιον τῇ χάριτι ταύτῃ παραβαλεῖν τὰϲ τρίτον ἔφη τῷ φίλῳ μου τούτῳ χαριζόμενοϲ πόλεωϲ καὶ διὰ τὸν οἰκιϲτὴν ἀλέξανδρον καὶ
		accented_line: τρίτον ἔφη τῷ φίλῳ μου τούτῳ χαριζόμενοϲ

				SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
					(SELECT index, accented_line,
						concat(lag(accented_line) OVER (ORDER BY index ASC), ' ', accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
						FROM gr0007 WHERE ( wkuniversalid ~ 'gr0007' ) ) firstpass
				where firstpass.index < 119176 and firstpass.index > 119172


[e] putting it all together and dispensing with lag:

SELECT secondpass.index, secondpass.accented_line
				FROM (SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
					(SELECT index, accented_line,
						concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
						FROM gr0007 WHERE ( wkuniversalid ~ 'gr0007' ) ) firstpass
					) secondpass
				WHERE secondpass.linebundle ~ 'τῷ φίλῳ μου' LIMIT 3000


"""

