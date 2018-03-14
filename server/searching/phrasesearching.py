# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
from server.dbsupport.dbfunctions import connectioncleanup, setconnection
from server.dbsupport.dblinefunctions import dblineintolineobject, makeablankline
from server.hipparchiaobjects.helperobjects import QueryCombinator
from server.searching.searchfunctions import buildbetweenwhereextension, lookoutsideoftheline, substringsearch


def phrasesearch(wkid, activepoll, searchobject, cursor):
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
			wordset = lookoutsideoftheline(hit[0], phraselen - 1, wkid, so, cursor)
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


def subqueryphrasesearch(foundlineobjects, searchphrase, tablestosearch, activepoll, searchobject):
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

	DEBUGGING notes: SQL oddities

	TROUBLE:

		'ἐρρῶϲθαι ὑμᾶϲ' can't be found in BGU (Vol 1), 108 (dp0001w00b); but it is there:
			[  𝕔 17 ]μεν. ἐρρῶϲθαι ὑμᾶϲ εὔχο(μαι).

		you will return hits if you search for 'ἐρρῶϲθαι ὑμᾶϲ' in just dp0001:
			BGU (Vol 1), 332: r, line 13 (dp0001w076)
			BGU (Vol 1), 8 rp: line 18 (dp0001w09d)

		you will return hits if you search for 'ἐρρῶϲθαι ὑμᾶϲ' in just dp0001w076 or dp0001w09d

		there is nothing special in the original betacode:
			█⑧① [ &c `17 ]$MEN. E)RRW=SQAI U(MA=S EU)/XO[1MAI]1.

		set up a search just inside dp0001w00b

			this will produce a result:
				»ϲθαι ὑμᾶϲ εὔ«
				»ῶϲθαι ὑμᾶϲ«
				»ρῶϲθαι ὑ«
				»μεν ἐρρ«
				»ρῶϲθαι ὑμ«
				»ῶϲθαι ὑμᾶ«
			this fails to produce a result:
				»ρῶϲθαι ὑμᾶ«

		pgAdmin4 has trouble with the phrase too:
			can find it via '﻿WHERE secondpass.linebundle ~ 'ὑμᾶϲ εὔχομαι'' in a different papyrus
			can't find it in dp0001w00b
			but will find it if you ask for the equivalent:
			﻿'ἐρρῶϲθαι\sὑμᾶϲ'

		WTF?

		It looks like the problem goes away if you substitute '\s' for ' ' in the search phrase.
		BUT why was there a problem in the first place?

		Something about how the bundles are built? i.e., 'concat(accented_line, ' ', lead(accented_line)' That does
		not really make sense (since the phrases are not at the edges of the joins...) But that is the only unusual
		thing we are doing here...

		very disturbing until the root cause of the trouble is made clear.

	:return:
	"""

	so = searchobject

	# substringsearch() needs ability to CREATE TEMPORARY TABLE
	dbconnection = setconnection('autocommit', readonlyconnection=False)
	curs = dbconnection.cursor()

	qcomb = QueryCombinator(searchphrase)
	# the last time is the full phrase:  ('one two three four five', '')
	combinations = qcomb.combinations()
	combinations.pop()
	# lines start/end
	sp = re.sub(r'^\s', '(^|\s)', searchphrase)
	sp = re.sub(r'\s$', '(\s|$)', sp)
	# on the reasoning behind the following substitution see 'DEBUGGING notes: SQL oddities' above
	sp = re.sub(r' ', r'\s', sp)

	if not so.onehit:
		lim = ' LIMIT ' + str(so.cap)
	else:
		# the windowing problem means that '1' might be something that gets discarded
		lim = ' LIMIT 5'

	commitcount = 0
	while tablestosearch and activepoll.hitcount.value <= so.cap:
		commitcount += 1
		try:
			uid = tablestosearch.pop()
			activepoll.remain(len(tablestosearch))
		except IndexError:
			uid = None
			tablestosearch = None

		if uid:
			if commitcount % hipparchia.config['MPCOMMITCOUNT'] == 0:
				dbconnection.commit()

			qtemplate = """
				SELECT secondpass.index, secondpass.{co} FROM 
					(SELECT firstpass.index, firstpass.linebundle, firstpass.{co} FROM
							(SELECT index, {co}, concat({co}, ' ', lead({co}) OVER (ORDER BY index ASC)) AS linebundle
								FROM {db} {whr} ) firstpass
					) secondpass
				WHERE secondpass.linebundle ~ %s {lim}"""

			whr = ''
			r = so.indexrestrictions[uid]
			if r['type'] == 'between':
				indexwedwhere = buildbetweenwhereextension(uid, so)
				if indexwedwhere != '':
					# indexwedwhere will come back with an extraneous ' AND'
					indexwedwhere = indexwedwhere[:-4]
					whr = 'WHERE {iw}'.format(iw=indexwedwhere)
			elif r['type'] == 'temptable':
				q = r['where']['tempquery']
				curs.execute(q)
				whr = 'WHERE EXISTS (SELECT 1 FROM {tbl}_includelist incl WHERE incl.includeindex = {tbl}.index)'.format(tbl=uid)

			query = qtemplate.format(db=uid, co=so.usecolumn, whr=whr, lim=lim)
			data = (sp,)
			# print('subqueryphrasesearch() q,d:',query, data)
			curs.execute(query, data)
			indices = [i[0] for i in curs.fetchall()]
			# this will yield a bunch of windows: you need to find the centers; see 'while...' below

			locallineobjects = list()
			if indices:
				for i in indices:
					query = 'SELECT * FROM {tb} WHERE index=%s'.format(tb=uid)
					data = (i,)
					curs.execute(query, data)
					locallineobjects.append(dblineintolineobject(curs.fetchone()))

			locallineobjects.reverse()
			# debugging
			# for l in locallineobjects:
			#	print(l.universalid, l.locus(), getattr(l,so.usewordlist))

			gotmyonehit = False
			while locallineobjects and activepoll.hitcount.value <= so.cap and not gotmyonehit:
				# windows of indices come back: e.g., three lines that look like they match when only one matches [3131, 3132, 3133]
				# figure out which line is really the line with the goods
				# it is not nearly so simple as picking the 2nd element in any run of 3: no always runs of 3 + matches in
				# subsequent lines means that you really should check your work carefully; this is not an especially costly
				# operation relative to the whole search and esp. relative to the speed gains of using a subquery search
				lo = locallineobjects.pop()
				if re.search(sp, getattr(lo, so.usewordlist)):
					foundlineobjects.append(lo)
					activepoll.addhits(1)
					if so.onehit:
						gotmyonehit = True
				else:
					try:
						nextline = locallineobjects[0]
					except IndexError:
						nextline = makeablankline('gr0000w000', -1)

					if lo.wkuinversalid != nextline.wkuinversalid or lo.index != (nextline.index - 1):
						# you grabbed the next line on the pile (e.g., index = 9999), not the actual next line (e.g., index = 101)
						# usually you won't get a hit by grabbing the next db line, but sometimes you do...
						query = 'SELECT * FROM {tb} WHERE index=%s'.format(tb=uid)
						data = (lo.index + 1,)
						curs.execute(query, data)
						try:
							nextline = dblineintolineobject(curs.fetchone())
						except:
							nextline = makeablankline('gr0000w000', -1)

					for c in combinations:
						tail = c[0] + '$'
						head = '^' + c[1]
						# debugging
						# print('re',getattr(lo,so.usewordlist),tail, head, getattr(next,so.usewordlist))
						if re.search(tail, getattr(lo, so.usewordlist)) and re.search(head, getattr(nextline, so.usewordlist)):
							foundlineobjects.append(lo)
							activepoll.addhits(1)
							if so.onehit:
								gotmyonehit = True

	connectioncleanup(curs, dbconnection)

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

