# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.dbsupport.dbfunctions import setconnection, makeablankline, dblineintolineobject
from server.hipparchiaclasses import QueryCombinator
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, whereclauses, \
	lookoutsideoftheline


def phrasesearch(maxhits, wkid, activepoll, searchobject, cursor):
	"""
	a whitespace might mean things are on a new line
	note how horrible something like και δη και is: you will search και first and then...
	subqueryphrasesearch() takes a more or less fixed amount of time; this function is
	faster if you call it with an uncommon word; if you call it with a common word, then
	you will likely search much more slowly than you would with subqueryphrasesearch()

	:param searchphrase:
	:param cursor:
	:param wkid:
	:param authorswheredict:
	:param activepoll:
	:return:
	"""

	s = searchobject
	searchphrase = s.termone

	if 'x' not in wkid:
		hits = substringsearch(s.leastcommon, wkid, s, cursor, templimit=maxhits)
	else:
		wkid = re.sub('x', 'w', wkid)
		hits = simplesearchworkwithexclusion(s.leastcommon, wkid, s, cursor, templimit=maxhits)
	
	fullmatches = []
	while hits and len(fullmatches) < s.cap:
		hit = hits.pop()
		phraselen = len(searchphrase.split(' '))
		wordset = lookoutsideoftheline(hit[0], phraselen - 1, wkid, s, cursor)
		if not s.accented:
			wordset = re.sub(r'[\.\?\!;:,·’]', r'', wordset)
		else:
			# the difference is in the apostrophe: δ vs δ’
			wordset = re.sub(r'[\.\?\!;:,·]', r'', wordset)

		if s.near and re.search(searchphrase, wordset):
			fullmatches.append(hit)
			activepoll.addhits(1)
		elif not s.near and re.search(searchphrase, wordset) is None:
			fullmatches.append(hit)
			activepoll.addhits(1)
	
	return fullmatches


def subqueryphrasesearch(foundlineobjects, searchphrase, workstosearch, count, commitcount, activepoll, searchobject):
	"""
	foundlineobjects, searchingfor, searchlist, commitcount, whereclauseinfo, activepoll

	use subquery syntax to grab multi-line windows of text for phrase searching

	line ends and line beginning issues can be overcome this way, but then you have plenty of
	bookkeeping to do to to get the proper results focussed on the right line

	workstosearch:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	authorswheredict: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	seeking:
		'si tu non'

	:return:
	"""

	s = searchobject

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	qcomb = QueryCombinator(searchphrase)
	# the last time is the full phrase:  ('one two three four five', '')
	combinations = qcomb.combinations()
	combinations.pop()
	# lines start/end
	sp = re.sub(r'^\s', '(^| )', searchphrase)
	sp = re.sub(r'\s$', '( |$)', sp)

	if not s.onehit:
		lim = ' LIMIT ' + str(s.cap)
	else:
		# the windowing problem means that '1' might be something that gets discarded
		lim = ' LIMIT 5'

	while len(workstosearch) > 0 and count.value <= s.cap:
		try:
			wkid = workstosearch.pop()
			activepoll.remain(len(workstosearch))
		except:
			wkid = 'gr0000w000'

		if wkid != 'gr0000w000':
			commitcount.increment()
			if commitcount.value % 400 == 0:
				dbconnection.commit()
			indices = None
			db = wkid[0:6]
			qtemplate = """SELECT secondpass.index, secondpass.{ln}
				FROM (SELECT firstpass.index, firstpass.linebundle, firstpass.{ln} FROM
					(SELECT index, {ln},
						concat({ln}, ' ', lead({ln}) OVER (ORDER BY index ASC)) as linebundle
						FROM {db} WHERE {whr} ) firstpass
					) secondpass
				WHERE secondpass.linebundle ~ %s {lim}"""

			if re.search(r'x', wkid):
				# we have exclusions
				wkid = re.sub(r'x', 'w', wkid)
				restrictions = [whereclauses(p, '<>', s.authorswheredict) for p in s.psgexclusions if wkid in p]
				whr = '( wkuniversalid = %s) AND ('
				data = [wkid[0:10]]
				for r in restrictions:
					# build both the query data and the where-clause in tandem
					for i in range(0, len(r)):
						whr += r[i][0] + 'OR '
						data.append(r[i][1])
					# drop the trailing ' OR'
					whr = whr[0:-4] + ') AND ('
				# drop the trailing ') AND ('
				data.append(sp)
				whr = whr[0:-6]
				query = qtemplate.format(db=db, ln=s.usecolumn, whr=whr, lim=lim)
			else:
				if '_AT_' not in wkid:
					whr = '( wkuniversalid ~ %s )'
					wkid = re.sub(r'x', 'w', wkid)
					if len(wkid) == 6:
						# we are searching the whole author
						d = wkid
					else:
						# we are searching an individual work
						d = wkid[0:10]
					query = qtemplate.format(db=db, ln=s.usecolumn, whr=whr, lim=lim)
					data = (d, sp)
				else:
					wkid = re.sub(r'x', 'w', wkid)
					data = [wkid[0:10]]
					whr = ''
					w = whereclauses(wkid, '=', s.authorswheredict)
					for i in range(0, len(w)):
						whr += 'AND (' + w[i][0] + ') '
						data.append(w[i][1])
					# strip extra ANDs
					whr = '( wkuniversalid = %s) ' + whr
					query = qtemplate.format(db=db, ln=s.usecolumn, whr=whr, lim=lim)
					data.append(sp)

			curs.execute(query, tuple(data))
			indices = [i[0] for i in curs.fetchall()]
			# this will yield a bunch of windows: you need to find the centers; see 'while...' below

			locallineobjects = []
			if indices:
				for i in indices:
					query = 'SELECT * FROM {tb} WHERE index=%s'.format(tb=wkid[0:6])
					data = (i,)
					curs.execute(query, data)
					locallineobjects.append(dblineintolineobject(curs.fetchone()))

			locallineobjects.reverse()
			# debugging
			# for l in locallineobjects:
			#	print(l.universalid, l.locus(), getattr(l,s.usewordlist))
			gotmyonehit = False
			while locallineobjects and count.value <= s.cap and not gotmyonehit:
				# windows of indices come back: e.g., three lines that look like they match when only one matches [3131, 3132, 3133]
				# figure out which line is really the line with the goods
				# it is not nearly so simple as picking the 2nd element in any run of 3: no always runs of 3 + matches in
				# subsequent lines means that you really should check your work carefully; this is not an especially costly
				# operation relative to the whole search and esp. relative to the speed gains of using a subquery search
				lo = locallineobjects.pop()
				if re.search(sp, getattr(lo,s.usewordlist)):
					foundlineobjects.append(lo)
					count.increment(1)
					activepoll.sethits(count.value)
					if s.onehit:
						gotmyonehit = True
				else:
					try:
						next = locallineobjects[0]
					except:
						next = makeablankline('gr0000w000', -1)

					if lo.wkuinversalid != next.wkuinversalid or lo.index != (next.index - 1):
						# you grabbed the next line on the pile (e.g., index = 9999), not the actual next line (e.g., index = 101)
						# usually you won't get a hit by grabbing the next db line, but sometimes you do...
						query = 'SELECT * FROM {tb} WHERE index=%s'.format(tb=wkid[0:6])
						data = (lo.index + 1,)
						curs.execute(query, data)
						try:
							next = dblineintolineobject(curs.fetchone())
						except:
							next = makeablankline('gr0000w000', -1)

					for c in combinations:
						tail = c[0] + '$'
						head = '^' + c[1]
						# debugging
						# print('re',getattr(lo,s.usewordlist),tail, head, getattr(next,s.usewordlist))
						if re.search(tail, getattr(lo,s.usewordlist)) and re.search(head, getattr(next,s.usewordlist)):
							foundlineobjects.append(lo)
							count.increment(1)
							activepoll.sethits(count.value)
							if s.onehit:
								gotmyonehit = True

	curs.close()
	del dbconnection

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

[d] peeking at the windows: ﻿119174 is where you will find:
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

