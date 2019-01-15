# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json

from server import hipparchia
from server.browsing.browserfunctions import buildbrowseroutputobject, findlinenumberfromcitation
from server.dbsupport.miscdbfunctions import makeanemptyauthor, makeanemptywork
from server.formatting.lexicaformatting import lexicaldbquickfixes
from server.hipparchiaobjects.browserobjects import BrowserOutputObject
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.listsandsession.checksession import probeforsessionvariables
from server.startup import authordict, workdict


@hipparchia.route('/browse/<method>/<workdb>/<location>')
def grabtextforbrowsing(method, workdb, location):
	"""

	you want to browse something

	there are multiple ways to get results here & different methods entail different location styles

		sample input: '/browse/linenumber/lt1254w001/4877'
		sample input: '/browse/locus/lt1254w001/15|13|4|_0'
		sample input: '/browse/perseus/lt1254w001/4:9:12'

	:return:
	"""

	probeforsessionvariables()

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	knownmethods = ['linenumber', 'locus', 'perseus']
	if method not in knownmethods:
		method = 'linenumber'

	perseusauthorneedsfixing = ['gr0006']
	if method == 'perseus' and workdb[:6] in perseusauthorneedsfixing:
		remapper = lexicaldbquickfixes([workdb])
		workdb = remapper[workdb]

	try:
		wo = workdict[workdb]
	except KeyError:
		wo = makeanemptywork('gr0000w000')

	try:
		ao = authordict[workdb[:6]]
	except KeyError:
		ao = makeanemptyauthor('gr0000')

	if ao.universalid != 'gr0000' and ao.universalid != wo.universalid[:6]:
		# you have only selected an author, but not a work: 'lt0474w_firstwork'
		wo = ao.listofworks[0]

	passage, resultmessage = findlinenumberfromcitation(method, location, wo, dbcursor)

	if passage and ao.universalid != 'gr0000':
		passageobject = buildbrowseroutputobject(ao, wo, int(passage), dbcursor)
	else:
		passageobject = BrowserOutputObject(ao, wo, passage)
		viewing = '<p class="currentlyviewing">error in fetching the browser data.<br />I was sent a citation that returned nothing: {c}</p><br /><br />'.format(c=location)
		if not passage:
			passage = ''
		table = [str(passage), workdb]
		passageobject.browserhtml = viewing + '\n'.join(table)

	if resultmessage != 'success':
		resultmessage = '<span class="small">({rc})</span>'.format(rc=resultmessage)
		passageobject.browserhtml = '{rc}<br />{bd}'.format(rc=resultmessage, bd=passageobject.browserhtml)

	browserdata = json.dumps(passageobject.generateoutput())

	dbconnection.connectioncleanup()

	return browserdata
