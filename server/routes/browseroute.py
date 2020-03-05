# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from server import hipparchia
from server.browsing.browserfunctions import buildbrowseroutputobject, browserfindlinenumberfromcitation
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dblinefunctions import returnfirstorlastlinenumber
from server.dbsupport.miscdbfunctions import buildauthorworkandpassage, returnfirstwork
from server.formatting.miscformatting import consolewarning
from server.formatting.lexicaformatting import lexicaldbquickfixes
from server.formatting.wordformatting import depunct
from server.hipparchiaobjects.browserobjects import BrowserOutputObject
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.listsandsession.checksession import probeforsessionvariables
from server.startup import authordict, workdict


@hipparchia.route('/browse/<method>/<author>/<work>')
@hipparchia.route('/browse/<method>/<author>/<work>/<location>')
def grabtextforbrowsing(method, author, work, location=None):
	"""

	you want to browse something

	there are multiple ways to get results here & different methods entail different location styles

		sample input: '/browse/linenumber/lt0550/001/1855'
		sample input: '/browse/locus/lt0550/001/3|100'
		sample input: '/browse/perseus/lt0550/001/2:717'

	:return:
	"""

	try:
		wo = workdict[author+'w'+work]
		ao = authordict[author]
	except KeyError:
		# Might as well sing of anger: Μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆοϲ...
		return grabtextforbrowsing('locus', 'gr0012', '001', '1')

	probeforsessionvariables()

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	allowed = '_|,:'
	location = depunct(location, allowedpunctuationsting=allowed)

	if not location or location == '|_0':
		locationval = returnfirstorlastlinenumber(wo.universalid, dbcursor)
		return grabtextforbrowsing('linenumber', author, work, str(locationval))

	knownmethods = ['linenumber', 'locus', 'perseus']
	if method not in knownmethods:
		method = 'linenumber'

	perseusauthorneedsfixing = ['gr0006']
	if method == 'perseus' and author in perseusauthorneedsfixing:
		remapper = lexicaldbquickfixes([author+'w'+work])
		try:
			wo = workdict[remapper[author]]
		except KeyError:
			consolewarning('grabtextforbrowsing() failed to remap {a} + {w}'.format(a=author, w=work))

	if ao and not wo:
		try:
			wo = workdict[returnfirstwork(ao.universalid, dbcursor)]
		except KeyError:
			# you are in some serious trouble: time to abort
			consolewarning('bad data fed to grabtextforbrowsing(): {m} / {a} / {w} / {l}'.format(m=method, a=author, w=work, l=location))
			ao = None

	passage, resultmessage = browserfindlinenumberfromcitation(method, location, wo, dbcursor)

	if passage and ao:
		passageobject = buildbrowseroutputobject(ao, wo, int(passage), dbcursor)
	else:
		passageobject = BrowserOutputObject(ao, wo, passage)
		viewing = '<p class="currentlyviewing">error in fetching the browser data.<br />I was sent a citation that returned nothing: {c}</p><br /><br />'.format(c=location)
		if not passage:
			passage = str()
		table = [str(passage), wo.universalid]
		passageobject.browserhtml = viewing + '\n'.join(table)

	if resultmessage != 'success':
		resultmessage = '<span class="small">({rc})</span>'.format(rc=resultmessage)
		passageobject.browserhtml = '{rc}<br />{bd}'.format(rc=resultmessage, bd=passageobject.browserhtml)

	browserdata = json.dumps(passageobject.generateoutput())

	dbconnection.connectioncleanup()

	return browserdata


@hipparchia.route('/browserawlocus/<author>/<work>')
@hipparchia.route('/browserawlocus/<author>/<work>/<location>')
def rawcitationgrabtextforbrowsing(author: str, work: str, location=None):
	"""

	the raw input version of grabtextforbrowsing()

		/browserawlocus/lt0550/001/3.100

	:param author:
	:param work:
	:param location:
	:return:
	"""

	try:
		wo = workdict[author+'w'+work]
	except KeyError:
		wo = None

	try:
		ao = authordict[author]
	except KeyError:
		ao = None

	if not wo and not ao:
		return grabtextforbrowsing('locus', 'unknownauthor', 'unknownwork', '_0')
	elif not wo:
		wo = ao.grabfirstworkobject()

	if not location:
		return grabtextforbrowsing('locus', wo.authorid, wo.worknumber, '_0')

	location = re.sub(r'\.', '|', location)
	allowed = '_|,:'
	location = depunct(location, allowedpunctuationsting=allowed)
	if not location:
		return grabtextforbrowsing('locus', author, work, '_0')

	emptycursor = None

	start = location.split('|')
	start.reverse()
	targetlinedict = finddblinefromincompletelocus(wo, start, emptycursor)
	if targetlinedict['code'] == 'success':
		targetline = str(targetlinedict['line'])
		return grabtextforbrowsing('linenumber', wo.authorid, wo.worknumber, targetline)
	else:
		return grabtextforbrowsing('locus', author, work, '_0')
