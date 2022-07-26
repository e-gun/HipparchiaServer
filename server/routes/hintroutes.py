# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json

from flask import request

try:
	from rich import print
except ImportError:
	pass

from server import hipparchia
from server.formatting.wordformatting import depunct, stripaccents
from server.listsandsession.genericlistfunctions import polytonicsort
from server.listsandsession.sessionfunctions import reducetosessionselections, returnactivelist
from server.startup import authorgenresdict, authorlocationdict, keyedlemmata, listmapper, workgenresdict, \
	workprovenancedict

JSON_STR = str


@hipparchia.route('/hints/<category>/<_>')
def supplyhints(category, _) -> JSON_STR:
	"""
	return JSON to fill a hint box with constantly updated values

	the json encodes a list of strings

	from https://api.jqueryui.com/autocomplete/

		The Autocomplete plugin does not filter the results, instead a query string is added with a term field,
		which the server-side script should use for filtering the results.

		if the source option is set to "https://example.com" and the user types foo,
		a GET request would be made to https://example.com?term=foo

	so you you have to have '?term='

	you also can't do a bare '/?term='. Instead you need an anchor: '/h?term='

	and this '?term=' has to be read via request.args.get()

	:return:
	"""

	query = request.args.get('term', str())

	functionmapper = {
		'author': offerauthorhints,
		'authgenre': augenrelist,
		'workgenre': wkgenrelist,
		'authlocation': offeraulocationhints,
		'worklocation': offerprovenancehints,
		'lemmata': offerlemmatahints,
	}

	try:
		fnc = functionmapper[category]
	except KeyError:
		return json.dumps(list())

	if category == 'author':
		allowedpunctuationsting = '['
	else:
		allowedpunctuationsting = None

	strippedquery = depunct(query, allowedpunctuationsting)

	hintlist = fnc(strippedquery)

	if hipparchia.config['JSONDEBUGMODE']:
		print('/hints/{f}\n\t{j}'.format(f=category, j=hintlist))

	return json.dumps(hintlist)


def offerauthorhints(query) -> list:
	"""

	author list lookup

	:return:
	"""

	ad = reducetosessionselections(listmapper, 'a')

	authorlist = ['{nm} [{id}]'.format(nm=ad[a].cleanname, id=ad[a].universalid) for a in ad]
	authorlist.sort()

	hintlist = buildhintlist(query, authorlist)

	return hintlist


def generichintlist(query, lookupdict, errortext):
	"""

	DRY abstraction of repeated list lookup code used by augenrelist(), etc.

	"""

	activelist = returnactivelist(lookupdict)
	activelist.sort()
	if len(activelist) > 0:
		hintlist = buildhintlist(query, activelist)
	else:
		hintlist = ['(no {e} data available inside of your active database(s))'.format(e=errortext)]

	return hintlist


def augenrelist(query) -> list:
	"""

	author genre list lookup

	:return:
	"""

	lookupdict = authorgenresdict
	errortext = 'author category'

	return generichintlist(query, lookupdict, errortext)


def wkgenrelist(query) -> list:
	"""

	work genre list lookup

	:return:
	"""

	lookupdict = workgenresdict
	errortext = 'work category'

	return generichintlist(query, lookupdict, errortext)


def offeraulocationhints(query) -> list:
	"""

	author location list lookup

	:return:
	"""

	lookupdict = authorlocationdict
	errortext = 'author location'

	return generichintlist(query, lookupdict, errortext)


def offerprovenancehints(query) -> list:
	"""

	work location list lookup

	TODO: these should be pruned so as to exclude locations that are meaningless relative to the currently active DBs
		e.g., if you have only Latin active, location is meaningless; and many TLG places do not match INS locations

	:return:
	"""

	lookupdict = workprovenancedict
	errortext = 'work provenance'

	return generichintlist(query, lookupdict, errortext)


def buildhintlist(seeking: str, listofposiblities: list) -> list:
	"""

	:param seeking:
	:param listofposiblities:
	:return:
	"""

	query = seeking.lower()
	qlen = len(query)

	listofposiblities = [l for l in listofposiblities if l]
	canonhints = [{'value': p} for p in listofposiblities if query == p.lower()[0:qlen]]
	pseudo = [x for x in listofposiblities if x[0] == '[']
	pseudohints = [{'value': p} for p in pseudo if '[{q}'.format(q=query) == p.lower()[0:qlen + 1]]
	hintlist = canonhints + pseudohints

	return hintlist


def offerlemmatahints(query) -> list:
	"""

	fill in the hint box with eligible values

	since there are a crazy number of words, don't update until you are beyond 3 chars

	:return:
	"""

	hintlist = list()

	invals = u'jvσς'
	outvals = u'iuϲϲ'

	if len(query) > 1:
		# query = stripaccents(term.lower())
		query = stripaccents(query)
		qlen = len(query)
		bag = query[0:2]
		key = stripaccents(bag.translate(str.maketrans(invals, outvals)))
		try:
			wordlist = keyedlemmata[key]
		except KeyError:
			wordlist = list()

		wordlist = polytonicsort(wordlist)

		# print('offerlemmatahints() wordlist', wordlist)

		if qlen > 2:
			# always true, but what if you changed 'len(term) > 2'?
			q = key + query[2:]
		else:
			q = key
		#hintlist = [{'value': w} for w in wordlist if q == stripaccents(w.lower()[0:qlen])]
		hintlist = [{'value': w} for w in wordlist if q == stripaccents(w[0:qlen])]

	if len(hintlist) > 50:
		hintlist = hintlist[0:50]
		hintlist = ['(>50 items: list was truncated)'] + hintlist

	return hintlist
