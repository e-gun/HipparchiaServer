# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import session

from server import hipparchia
from server.browsing.browserfunctions import getandformatbrowsercontext
from server.dbsupport.citationfunctions import finddblinefromlocus, finddblinefromincompletelocus, perseusdelabeler
from server.dbsupport.dbfunctions import setconnection, makeanemptyauthor, makeanemptywork, perseusidmismatch, \
	returnfirstlinenumber
from server.formatting.lexicaformatting import dbquickfixes
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

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	workdb = re.sub('[\W_|]+', '', locus)[:10]

	try: ao = authordict[workdb[:6]]
	except: ao = makeanemptyauthor('gr0000')

	try:
		wo = workdict[workdb]
	except KeyError:
		if ao.universalid == 'gr0000':
			wo = makeanemptywork('gr0000w000')
		else:
			# you have only selected an author, but not a work: 'gr7000w_AT_1' will fail fecause we need 'wNNN'
			# so send line 1 of work 1
			wo = ao.listofworks[0]
			locus = wo.universalid + '_LN_' + str(wo.starts)

	ctx = int(session['browsercontext'])
	numbersevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	resultmessage = 'success'

	passage = locus[10:]

	if passage[0:4] == '_LN_':
		# you were sent here either by the hit list or a forward/back button in the passage browser
		passage = re.sub('[\D]', '', passage[4:])
	elif passage[0:4] == '_AT_':
		# you were sent here by the citation builder autofill boxes
		p = locus[14:].split('|')
		cleanedp = [re.sub('[\W_|]+', '',level) for level in p]
		cleanedp = tuple(cleanedp[:5])
		if len(cleanedp) == wo.availablelevels:
			passage = finddblinefromlocus(wo.universalid, cleanedp, cur)
		else:
			p = finddblinefromincompletelocus(wo, cleanedp, cur)
			resultmessage = p['code']
			passage = p['line']
	elif passage[0:4] == '_PE_':
		# you came here via a perseus dictionary xref: all sorts of crazy ensues
		# nasty kludge with eur: should build the fixes into the db
		# euripides
		if 'gr0006' in workdb:
			remapper = dbquickfixes([workdb])
			workid = remapper[workdb]
			wo = workdict[workid]

		try:
			# dict does not always agree with our ids...
			# do an imperfect test for this by inviting the exception
			# you can still get a valid but wrong work, of course,
			# but if you ask for w001 and only w003 exists, this is supposed to take care of that
			returnfirstlinenumber(workdb, cur)
		except:
			# dict did not agree with our ids...: euripides, esp
			# what follows is a 'hope for the best' approach
			workid = perseusidmismatch(workdb, cur)
			wo = workdict[workid]
			# print('dictionary lookup id remap',workdb,workid,wo.title)

		citation = passage[4:].split(':')
		citation.reverse()

		# life=cal. or section=32
		needscleaning = [True for c in citation if len(c.split('=')) > 1]
		if True in needscleaning:
			citation = perseusdelabeler(citation, wo)

		# another problem 'J. ' in sallust <bibl id="lt0631w001_PE_J. 79:3" default="NO" valid="yes"><author>Sall.</author> J. 79, 3</bibl>
		# lt0631w002_PE_79:3 is what you need to send to finddblinefromincompletelocus()
		# note that the work number is wrong, so the next is only a partial fix and valid only if wNNN has been set right

		if ' ' in citation[-1]:
			citation[-1] = citation[-1].split(' ')[-1]

		p = finddblinefromincompletelocus(wo, citation, cur)
		resultmessage = p['code']
		passage = p['line']

	if passage and ao.universalid != 'gr0000':
		browserdata = getandformatbrowsercontext(ao, wo, int(passage), ctx, numbersevery, cur)
	else:
		browserdata = {}
		browserdata['browseforwards'] = wo.ends
		browserdata['browseback'] = wo.starts
		viewing = '<p class="currentlyviewing">error in fetching the browser data.<br />I was sent a citation that returned nothing: {c}</p><br /><br />'.format(c=locus)
		if not passage:
			passage = ''
		try:
			table = [passage, workdb, citation]
		except:
			table = [passage, workdb]
		browserdata['browserhtml'] = viewing + '\n'.join(table)
		browserdata['authornumber'] = ao.universalid
		browserdata['workid'] = wo.universalid
		browserdata['authorboxcontents'] = ao.cleanname + ' [' + ao.universalid + ']'
		browserdata['workboxcontents'] = wo.title + ' (' + wo.universalid[-4:] + ')'

	if resultmessage != 'success':
		resultmessage = '<span class="small">({rc})</span>'.format(rc=resultmessage)
		browserdata['browserhtml'] = '{rc}<br />{bd}'.format(rc=resultmessage, bd=browserdata['browserhtml'])

	browserdata = json.dumps(browserdata)

	cur.close()

	return browserdata

