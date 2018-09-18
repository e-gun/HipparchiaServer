# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json

from flask import request

from server import hipparchia
from server.formatting.wordformatting import depunct, stripaccents
from server.listsandsession.searchlistmanagement import buildhintlist
from server.listsandsession.genericlistfunctions import polytonicsort
from server.listsandsession.sessionfunctions import reducetosessionselections, returnactivelist
from server.startup import authorgenresdict, authorlocationdict, keyedlemmata, listmapper, workgenresdict, \
	workprovenancedict


@hipparchia.route('/getauthorhint', methods=['GET'])
def offerauthorhints():
	"""
	fill the hint box with constantly updated values
	:return:
	"""

	query = request.args.get('term', '')
	strippedquery = depunct(query)

	ad = reducetosessionselections(listmapper, 'a')

	authorlist = ['{nm} [{id}]'.format(nm=ad[a].cleanname, id=ad[a].universalid) for a in ad]

	authorlist.sort()

	hint = list()

	if strippedquery:
		hint = buildhintlist(strippedquery, authorlist)

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getgenrehint', methods=['GET'])
def augenrelist():
	"""
	populate the author genres autocomplete box with constantly updated values
	:return:
	"""

	query = request.args.get('term', '')
	strippedquery = depunct(query)

	activegenres = returnactivelist(authorgenresdict)
	activegenres.sort()

	hint = list()

	if len(activegenres) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activegenres)
	else:
		hint = ['(no author category data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getworkgenrehint', methods=['GET'])
def wkgenrelist():
	"""
	populate the work genres autocomplete box with constantly updated values
	:return:
	"""

	query = request.args.get('term', '')
	strippedquery = depunct(query)

	activegenres = returnactivelist(workgenresdict)
	activegenres.sort()

	hint = list()

	if len(activegenres) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activegenres)
	else:
		hint = ['(no work category data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getaulocationhint', methods=['GET'])
def offeraulocationhints():
	"""
	fill the hint box with constantly updated values

	:return:
	"""

	query = request.args.get('term', '')
	strippedquery = depunct(query)

	activelocations = returnactivelist(authorlocationdict)
	activelocations.sort()

	hint = list()

	if len(activelocations) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activelocations)
		else:
			hint = ['(no author location data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getwkprovenancehint', methods=['GET'])
def offerprovenancehints():
	"""
	fill the hint box with constantly updated values
	TODO: these should be pruned so as to exclude locations that are meaningless relative to the currently active DBs
		e.g., if you have only Latin active, location is meaningless; and many TLG places do not match INS locations

	:return:
	"""

	query = request.args.get('term', '')
	strippedquery = depunct(query)

	activelocations = returnactivelist(workprovenancedict)
	activelocations.sort()

	hint = list()

	if len(activelocations) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activelocations)
		else:
			hint = ['(no work provenance data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getlemmahint', methods=['GET'])
def offerlemmatahints():
	"""

	fill in the hint box with eligible values

	since there are a crazy number of words, don't update until you are beyond 3 chars

	:return:
	"""

	term = request.args.get('term', '')

	hintlist = list()

	invals = u'jvσς'
	outvals = u'iuϲϲ'

	if len(term) > 2:
		query = stripaccents(term.lower())
		qlen = len(query)
		a = query[0].translate(str.maketrans(invals, outvals))
		b = query[1].translate(str.maketrans(invals, outvals))
		try:
			wordlist = keyedlemmata[a][b]
		except KeyError:
			wordlist = list()

		wordlist = polytonicsort(wordlist)

		if qlen > 2:
			# always true, but what if you changed 'len(term) > 2'?
			q = a+b+query[2:]
		else:
			q = a+b
		hintlist = [{'value': w} for w in wordlist if q == stripaccents(w.lower()[0:qlen])]

	if len(hintlist) > 50:
		hintlist = hintlist[0:50]
		hintlist = ['(>50 items: list was truncated)'] + hintlist

	hint = json.dumps(hintlist)

	return hint
