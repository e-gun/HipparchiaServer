# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import request

from server import hipparchia
from server.listsandsession.listmanagement import buildhintlist
from server.listsandsession.sessionfunctions import reducetosessionselections, returnactivedbs
from server.startup import authorgenresdict, authorlocationdict, workgenresdict, workprovenancedict, listmapper


@hipparchia.route('/getauthorhint', methods=['GET'])
def offerauthorhints():
	"""
	fill the hint box with constantly updated values
	:return:
	"""

	strippedquery = re.sub(r'[!@#$|%()*\'\"]','',request.args.get('term', ''))

	ad = reducetosessionselections(listmapper, 'a')

	authorlist = ['{nm} [{id}]'.format(nm=ad[a].cleanname, id=ad[a].universalid) for a in ad]

	authorlist.sort()

	hint = []

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

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activegenres = []
	for key in activedbs:
		activegenres += authorgenresdict[key]

	activegenres = list(set(activegenres))
	activegenres.sort()

	hint = []

	if len(activegenres) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activegenres)
	else:
		hint = ['(no author genre data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getworkgenrehint', methods=['GET'])
def wkgenrelist():
	"""
	populate the work genres autocomplete box with constantly updated values
	:return:
	"""

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activegenres = []
	for key in activedbs:
		activegenres += workgenresdict[key]

	activegenres = list(set(activegenres))
	activegenres.sort()

	hint = []

	if len(activegenres) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activegenres)
	else:
		hint = ['(no work genre data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getaulocationhint', methods=['GET'])
def offeraulocationhints():
	"""
	fill the hint box with constantly updated values

	:return:
	"""

	strippedquery = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activelocations = []

	for key in activedbs:
		activelocations += authorlocationdict[key]

	activelocations = list(set(activelocations))
	activelocations.sort()

	hint = []

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

	strippedquery = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activelocations = []

	for key in activedbs:
		activelocations += workprovenancedict[key]

	activelocations = list(set(activelocations))
	activelocations.sort()

	hint = []

	if len(activelocations) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activelocations)
		else:
			hint = ['(no work provenance data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint
