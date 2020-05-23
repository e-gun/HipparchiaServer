# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from typing import List

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork, makeablankline, grablistoflines
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.hipparchiaobjects.searchobjects import SearchObject
from server.searching.searchfunctions import dblooknear
from server.searching.substringsearching import substringsearch


def withinxlines(workdbname: str, searchobject: SearchObject, dbconnection) -> List[tuple]:
	"""

	after finding x, look for y within n lines of x

	people who send phrases to both halves and/or a lot of regex will not always get what they want

	:param workdbname:
	:param searchobject:
	:return:
	"""

	so = searchobject
	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 2000000

	if so.lemma:
		chunksize = hipparchia.config['LEMMACHUNKSIZE']
		terms = so.lemma.formlist
		chunked = [terms[i:i + chunksize] for i in range(0, len(terms), chunksize)]
		chunked = [wordlistintoregex(c) for c in chunked]
		hitlist = list()
		for c in chunked:
			hitlist += list(substringsearch(c, workdbname, so, dbcursor, templimit))
	else:
		hitlist = list(substringsearch(so.termone, workdbname, so, dbcursor, templimit))

	fullmatches = lemmatizedwithinxlines(searchobject, hitlist, dbcursor)

	# if so.lemmaone or so.lemmatwo:
	# 	fullmatches = lemmatizedwithinxlines(searchobject, hitlist, dbcursor)
	# else:
	# 	fullmatches = simplewithinxlines(searchobject, hitlist, dbcursor)

	return fullmatches


def lemmatizedwithinxlines(searchobject, hitlist, dbcursor):
	"""

	the newer way of doing withinxlines

	this will ask regex to do the heavy lifting

	nasty edge case 'fire' near 'burn' in Homer:
	simplewithinxlines()
	  Sought all 5 known forms of »πῦρ« within 1 lines of all 359 known forms of »καίω«
	  Searched 3 texts and found 24 passages (621.25s)

	lemmatizedwithinxlines()
	   Sought all 5 known forms of »πῦρ« within 1 lines of all 359 known forms of »καίω«
	   Searched 3 texts and found 24 passages (2.82s)

	:param hitlist:
	:return:
	"""

	so = searchobject

	columconverter = {'marked_up_line': 'markedup', 'accented_line': 'polytonic', 'stripped_line': 'stripped'}
	col = columconverter[so.usecolumn]

	prox = int(so.session['proximity'])

	flatten = lambda l: [item for sublist in l for item in sublist]

	# note that at the moment we arrive here with a one-work per worker policy
	# that is all of the hits will come from the same table
	# this means extra/useless sifting below, but perhaps it is safer to be wasteful now lest we break later

	fullmatches = list()
	hitlinelist = list()
	linesintheauthors = dict()

	testing = True
	if testing:
		hitlinelist = [dblineintolineobject(h) for h in hitlist]
		for l in hitlinelist:
			wkid = l.universalid
			# prox = 2
			# l = 100
			# list(range(l-prox, l+prox+1))
			# [98, 99, 100, 101, 102]
			environs = set(range(l.index - prox, l.index + prox + 1))
			environs = ['{w}_ln_{x}'.format(w=wkid, x=e) for e in environs]
			try:
				linesintheauthors[wkid[0:6]]
			except KeyError:
				linesintheauthors[wkid[0:6]] = set()
			linesintheauthors[wkid[0:6]].update(environs)

	# now grab all of the lines you might need
	linecollection = set()
	for l in linesintheauthors:
		if linesintheauthors[l]:
			# example: {'lt0803': {952, 953, 951}}
			linecollection = grablistoflines(l, list(linesintheauthors[l]), dbcursor)
			linecollection = {'{w}_ln_{x}'.format(w=l.wkuinversalid, x=l.index): l for l in linecollection}

	# then associate all of the surrounding words with those lines
	wordbundles = dict()
	for l in hitlinelist:
		wkid = l.universalid
		environs = set(range(l.index - prox, l.index + prox + 1))
		mylines = list()
		for e in environs:
			try:
				mylines.append(linecollection['{w}_ln_{x}'.format(w=wkid, x=e)])
			except KeyError:
				# you went out of bounds and tried to grab something that is not really there
				# KeyError: 'lt1515w001_ln_1175'
				# line 1175 is actually the first line of lt1515w002...
				pass

		mywords = [getattr(l, col) for l in mylines]
		mywords = [w.split(' ') for w in mywords if mywords]
		mywords = flatten(mywords)
		mywords = ' '.join(mywords)
		wordbundles[l] = mywords

	# then see if we have any hits...
	while True:
		for provisionalhitline in wordbundles:
			if len(fullmatches) > so.cap:
				break
			if so.near and re.search(so.termtwo, wordbundles[provisionalhitline]):
				fullmatches.append(provisionalhitline)
			elif not so.near and not re.search(so.termtwo, wordbundles[provisionalhitline]):
				fullmatches.append(provisionalhitline)
		break

	fullmatches = [m.decompose() for m in fullmatches]

	return fullmatches


def simplewithinxlines(searchobject, hitlist, dbcursor):
	"""

	the older and potentially very slow way of doing withinxlines

	this will ask postgres to do the heavy lifting

	nasty edge case 'fire' near 'burn' in Homer:
	  Sought all 5 known forms of »πῦρ« within 1 lines of all 359 known forms of »καίω«
	  Searched 3 texts and found 24 passages (621.25s)

	170 initial hits in Homer then take *aeons* to find the rest
	as each of the 170 itself takes several seconds to check

	:param hitlist:
	:return:
	"""

	so = searchobject

	fullmatches = list()

	while True:
		for hit in hitlist:
			if len(fullmatches) > so.cap:
				break
			# this bit is BRITTLE because of the paramater order vs the db field order
			#   dblooknear(index: int, distanceinlines: int, secondterm: str, workid: str, usecolumn: str, cursor)
			# see "worklinetemplate" for the order in which the elements will return from a search hit
			# should use lineobjects, but it is 'premature' given that the returned 'fullmatches' should look
			# like a dbline
			hitindex = hit[1]
			hitwkid = hit[0]
			isnear = dblooknear(hitindex, so.distance, so.termtwo, hitwkid, so.usecolumn, dbcursor)
			if so.near and isnear:
				fullmatches.append(hit)
			elif not so.near and not isnear:
				fullmatches.append(hit)
		break

	return fullmatches


def withinxwords(workdbname: str, searchobject: SearchObject, dbconnection) -> List[dbWorkLine]:
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
	dbcursor = dbconnection.cursor()
	dbconnection.setautocommit()

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
			hits += list(substringsearch(c, workdbname, so, dbcursor, templimit))
		so.usewordlist = 'polytonic'
	else:
		hits = list(substringsearch(so.termone, workdbname, so, dbcursor, templimit))

	fullmatches = list()

	for hit in hits:
		hitline = dblineintolineobject(hit)

		leadandlag = grableadingandlagging(hitline, so, dbcursor)
		lagging = leadandlag['lag']
		leading = leadandlag['lead']
		# print(hitline.universalid, so.termtwo, '\n\t[lag] ', lagging, '\n\t[lead]', leading)

		if so.near and (re.search(so.termtwo, leading) or re.search(so.termtwo, lagging)):
			fullmatches.append(hit)
		elif not so.near and not re.search(so.termtwo, leading) and not re.search(so.termtwo, lagging):
			fullmatches.append(hit)

	return fullmatches


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
