# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json

from server import hipparchia
from server.authentication.authenticationwrapper import requireauthentication
from server.browsing.browserfunctions import browserfindlinenumberfromcitation, buildbrowseroutputobject
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dblinefunctions import returnfirstorlastlinenumber
from server.formatting.miscformatting import consolewarning
from server.hipparchiaobjects.browserobjects import BrowserOutputObject
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.parsingobjects import BrowserInputParsingObject
from server.listsandsession.checksession import probeforsessionvariables

JSON_STR = str

@hipparchia.route('/browse/<method>/<author>/<work>')
@hipparchia.route('/browse/<method>/<author>/<work>/<location>')
@requireauthentication
def grabtextforbrowsing(method, author, work, location=None) -> JSON_STR:
	"""

	you want to browse something

	there are multiple ways to get results here & different methods entail different location styles

		sample input: '/browse/linenumber/lt0550/001/1855'
		sample input: '/browse/locus/lt0550/001/3|100'
		sample input: '/browse/perseus/lt0550/001/2:717'

	:return:
	"""

	if method not in ['linenumber', 'locus', 'perseus']:
		method = 'linenumber'

	delimiterdict = {'linenumber': None, 'locus': '|', 'perseus': ':'}
	delimiter = delimiterdict[method]

	po = BrowserInputParsingObject(author, work, location, delimiter=delimiter)
	po.supplementalvalidcitationcharacters = '_|,:'
	po.updatepassagelist()

	ao = po.authorobject
	wo = po.workobject

	if not po.authorobject:
		# Might as well sing of anger: Μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆοϲ...
		return grabtextforbrowsing('locus', 'gr0012', '001', '1')

	probeforsessionvariables()

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	if not location or location == '|_0':
		locationval = returnfirstorlastlinenumber(wo.universalid, dbcursor)
		return grabtextforbrowsing('linenumber', author, work, str(locationval))

	if ao and not wo:
		try:
			wo = ao.grabfirstworkobject()
		except KeyError:
			# you are in some serious trouble: time to abort
			consolewarning('bad data fed to grabtextforbrowsing(): {m} / {a} / {w} / {l}'.format(m=method, a=author, w=work, l=location))
			ao = None

	thelocation, resultmessage = browserfindlinenumberfromcitation(method, po.passageaslist, wo, dbcursor)

	if thelocation and ao:
		passageobject = buildbrowseroutputobject(ao, wo, int(thelocation), dbcursor)
	else:
		passageobject = BrowserOutputObject(ao, wo, thelocation)
		viewing = '<p class="currentlyviewing">error in fetching the browser data.<br />I was sent a citation that returned nothing: {c}</p><br /><br />'.format(c=location)
		if not thelocation:
			thelocation = str()
		table = [str(thelocation), wo.universalid]
		passageobject.browserhtml = viewing + '\n'.join(table)

	if resultmessage != 'success':
		resultmessage = '<span class="small">({rc})</span>'.format(rc=resultmessage)
		passageobject.browserhtml = '{rc}<br />{bd}'.format(rc=resultmessage, bd=passageobject.browserhtml)

	browserdata = json.dumps(passageobject.generateoutput())

	dbconnection.connectioncleanup()

	return browserdata


@hipparchia.route('/browserawlocus/<author>/<work>')
@hipparchia.route('/browserawlocus/<author>/<work>/<location>')
@requireauthentication
def rawcitationgrabtextforbrowsing(author: str, work: str, location=None) -> JSON_STR:
	"""

	the raw input version of grabtextforbrowsing()

		/browserawlocus/lt0550/001/3.100

	:param author:
	:param work:
	:param location:
	:return:
	"""

	po = BrowserInputParsingObject(author, work, location, delimiter='.')
	ao = po.authorobject
	wo = po.workobject

	if not location and wo:
		return grabtextforbrowsing('locus', wo.authorid, wo.worknumber, '_0')
	elif not location and not wo:
		wo = ao.grabfirstworkobject()
		return grabtextforbrowsing('locus', wo.authorid, wo.worknumber, '_0')

	emptycursor = None

	targetlinedict = finddblinefromincompletelocus(wo, po.passageaslist, emptycursor)

	if targetlinedict['code'] == 'success':
		targetline = str(targetlinedict['line'])
		return grabtextforbrowsing('linenumber', wo.authorid, wo.worknumber, targetline)
	else:
		return grabtextforbrowsing('locus', wo.authorid, wo.worknumber, '_0')
