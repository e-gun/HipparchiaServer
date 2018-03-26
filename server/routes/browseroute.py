# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json

from flask import session

from server import hipparchia
from server.browsing.browserfunctions import findlinenumberfromlocus, getandformatbrowsercontext
from server.dbsupport.miscdbfunctions import makeanemptyauthor, makeanemptywork
from server.formatting.lexicaformatting import dbquickfixes
from server.formatting.wordformatting import depunct
from server.hipparchiaobjects.browserobjects import BrowserOutputObject
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.startup import authordict, workdict


@hipparchia.route('/browse/<locus>')
def grabtextforbrowsing(locus):
	"""
	you want to browse something
	there are two standard ways to get results here: tell me a line or tell me a citation
		sample input: '/browseto/gr0059w030_LN_48203'
		sample input: '/browseto/gr0008w001_AT_23|3|3'
	alternately you can sent me a perseus ref from a dictionary entry ('_PE_') and I will *try* to convert it into a '_LN_'
	sample output: [could probably use retooling...]
		[{'forwardsandback': ['gr0199w010_LN_55', 'gr0199w010_LN_5']}, {'value': '<currentlyviewing><span class="author">Bacchylides</span>, <span class="work">Dithyrambi</span><br />Dithyramb 1, line 42<br /><span class="pubvolumename">Bacchylide. Dithyrambes, épinicies, fragments<br /></span><span class="pubpress">Les Belles Lettres , </span><span class="pubcity">Paris , </span><span class="pubyear">1993. </span><span class="pubeditor"> (Irigoin, J. )</span></currentlyviewing><br /><br />'}, {'value': '<table>\n'}, {'value': '<tr class="browser"><td class="browsedline"><observed id="[–⏑–––⏑–––⏑–]δ̣ουϲ">[–⏑–––⏑–––⏑–]δ̣ουϲ</observed> </td><td class="browsercite"></td></tr>\n'}, ...]

	:return:
	"""

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	workdb = depunct(locus)[:10]

	ao = makeanemptyauthor('gr0000')
	wo = makeanemptywork('gr0000w000')

	perseusauthorneedsfixing = ['gr0006']
	if '_PE_' in locus and workdb[:6] in perseusauthorneedsfixing:
		# perseus has mis-mapped id numbers for the works relative to tlg-e
		remapper = dbquickfixes([workdb])
		workdb = remapper[workdb]

	try:
		ao = authordict[workdb[:6]]
	except KeyError:
		pass

	try:
		wo = workdict[workdb]
	except KeyError:
		if ao.universalid == 'gr0000':
			pass
		else:
			# you have only selected an author, but not a work: 'gr7000w_AT_1' will fail because we need 'wNNN'
			# so send line 1 of work 1
			wo = ao.listofworks[0]
			locus = '{w}_LN_{s}'.format(w=wo.universalid, s=wo.starts)

	ctx = int(session['browsercontext'])
	numbersevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	passage, resultmessage = findlinenumberfromlocus(locus, wo, dbcursor)

	if passage and ao.universalid != 'gr0000':
		passageobject = getandformatbrowsercontext(ao, wo, int(passage), ctx, numbersevery, dbcursor)
	else:
		passageobject = BrowserOutputObject(ao, wo, passage)
		viewing = '<p class="currentlyviewing">error in fetching the browser data.<br />I was sent a citation that returned nothing: {c}</p><br /><br />'.format(c=locus)
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
