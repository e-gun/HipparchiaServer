# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork, makeablankline
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.searching.searchfunctions import dblooknear, substringsearch


def withinxlines(workdbname, searchobject):
	"""

	after finding x, look for y within n lines of x

	people who send phrases to both halves and/or a lot of regex will not always get what they want

	it might be possible to do this more cleverly with a JOIN or a subquery, but this brute force way seems
	to be 'fast enough' and those solutions seem to be quite tangled

		Sought »ϲαφῶϲ« within 5 lines of »πάντα«
		Searched 6,625 texts and found 1,428 passages (8.04s)
		Sorted by name

	:param workdbname:
	:param searchobject:
	:return:
	"""

	so = searchobject

	# substringsearch() needs ability to CREATE TEMPORARY TABLE
	dbconnection = ConnectionObject('autocommit', readonlyconnection=False)
	cursor = dbconnection.cursor()

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 2000000

	if so.lemma:
		chunksize = hipparchia.config['LEMMACHUNKSIZE']
		terms = so.lemma.formlist
		chunked = [terms[i:i + chunksize] for i in range(0, len(terms), chunksize)]
		chunked = [wordlistintoregex(c) for c in chunked]
		hits = list()
		for c in chunked:
			hits += list(substringsearch(c, workdbname, so, cursor, templimit))
	else:
		hits = list(substringsearch(so.termone, workdbname, so, cursor, templimit))

	fullmatches = list()

	while True:
		for hit in hits:
			if len(fullmatches) > so.cap:
				break
			isnear = dblooknear(hit[0], so.distance, so.termtwo, hit[1], so.usecolumn, cursor)
			if so.near and isnear:
				fullmatches.append(hit)
			elif not so.near and not isnear:
				fullmatches.append(hit)
		break

	dbconnection.connectioncleanup()

	return fullmatches


def withinxwords(workdbname, searchobject):
	"""

	int(session['proximity']), searchingfor, proximate, curs, wkid, whereclauseinfo

	after finding x, look for y within n words of x

	getting to y:
		find the search term x and slice it out of its line
		then build forwards and backwards within the requisite range
		then see if you get a match in the range

	if looking for 'paucitate' near 'imperator' you will find:
		'romani paucitate seruorum gloriatos itane tandem ne'
	this will become:
		'romani' + 'seruorum gloriatos itane tandem ne'

	:param workdbname:
	:param searchobject:
	:return:
	"""
	so = searchobject

	# substringsearch() needs ability to CREATE TEMPORARY TABLE
	dbconnection = ConnectionObject('autocommit', readonlyconnection=False)
	cursor = dbconnection.cursor()

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 9999

	if so.lemma:
		chunksize = hipparchia.config['LEMMACHUNKSIZE']
		terms = so.lemma.formlist
		chunked = [terms[i:i + chunksize] for i in range(0, len(terms), chunksize)]
		chunked = [wordlistintoregex(c) for c in chunked]
		hits = list()
		for c in chunked:
			hits += list(substringsearch(c, workdbname, so, cursor, templimit))
		so.usewordlist = 'polytonic'
	else:
		hits = list(substringsearch(so.termone, workdbname, so, cursor, templimit))

	fullmatches = list()

	for hit in hits:
		hitline = dblineintolineobject(hit)

		leadandlag = grableadingandlagging(hitline, so, cursor)
		lagging = leadandlag['lag']
		leading = leadandlag['lead']

		if so.near and (re.search(so.termtwo, leading) or re.search(so.termtwo, lagging)):
			fullmatches.append(hit)
		elif not so.near and not re.search(so.termtwo, leading) and not re.search(so.termtwo, lagging):
			fullmatches.append(hit)

	dbconnection.connectioncleanup()

	return fullmatches


def grableadingandlagging(hitline, searchobject, cursor):
	"""

	take a dbline and grab the N words in front of it and after it

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
	past = searchzone[match.end():]
	while past and past[0] != ' ':
		past = past[1:]

	upto = searchzone[:match.start()]
	while upto and upto[-1] != ' ':
		upto = upto[:-1]

	ucount = len([x for x in upto.split(' ') if x])
	pcount = len([x for x in past.split(' ') if x])

	atline = hitline.index
	lagging = [x for x in upto.split(' ') if x]
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

	leading = [x for x in past.split(' ') if x]
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
