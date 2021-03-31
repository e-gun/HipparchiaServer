# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List, Tuple

from flask import session

from server.dbsupport.citationfunctions import prolixlocus
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.listsandsession.checksession import probeforsessionvariables


def sessionselectionsashtml(authordict: dict, workdict: dict) -> dict:
	"""

	assemble the html to be fed into the json that goes to the js that fills #selectionstable
	three chunks: time; selections; exclusions

	:param authordict:
	:param workdict:
	:return:
	"""

	selectioninfo = dict()

	selectioninfo['timeexclusions'] = sessiontimeexclusionsinfo()
	sxhtml = sessionselectionsinfo(authordict, workdict)

	selectioninfo['selections'] = sxhtml['selections']
	selectioninfo['exclusions'] = sxhtml['exclusions']
	selectioninfo['newjs'] = sessionselectionsjs(sxhtml['jstuples'])

	# numberofselections is -1 if there were no selections
	# returning this will hide the selections table; but it should not be hidden if there are time restrictions or spuria restrictions
	# so say '0' instead
	if sxhtml['numberofselections'] == -1 and (selectioninfo['timeexclusions'] != '' or not session['spuria']):
		selectioninfo['numberofselections'] = 0
	else:
		selectioninfo['numberofselections'] = sxhtml['numberofselections']

	return selectioninfo


def sessionselectionsjs(labeltupleslist: List[Tuple[str, int]]) -> str:
	"""

	build js out of something like:

		[('agnselections', 0), ('auselections', 0), ('auselections', 1)]

	:param labeltupleslist:
	:return:
	"""

	template = """
		$( '#{label}_0{number}' ).dblclick(function() lbrk
			$.getJSON('/selection/clear/{label}/{number}', function (selectiondata) lbrk 
				reloadselections(selectiondata); rbrk);
		rbrk);
	"""

	js = [template.format(label=j[0], number=j[1]) for j in labeltupleslist]
	js = '\n'.join(js)
	js = '<script>\n{j}\n</script>'.format(j=js)
	js = re.sub(r'lbrk', r'{',js)
	js = re.sub(r'rbrk', r'}', js)

	return js


def sessiontimeexclusionsinfo():
	"""
	build time exlusion html for #selectionstable + #timerestrictions
	:return:
	"""

	try:
		# it is possible to hit this function before the session has been set, so...
		session['latestdate']
	except KeyError:
		probeforsessionvariables()

	info = 'Unless specifically listed, authors/works must come from {early}&nbspto&nbsp;{late}'
	timerestrictions = ''

	if session['latestdate'] != '1500' or session['earliestdate'] != '-850':
		if int(session['earliestdate']) < 0:
			early = session['earliestdate'][1:] + ' B.C.E'
		else:
			early = session['earliestdate'] + ' C.E'
		if int(session['latestdate']) < 0:
			late = session['latestdate'][1:] + ' B.C.E'
		else:
			late = session['latestdate'] + ' C.E'

		timerestrictions = info.format(early=early, late=late)

	return timerestrictions


def sessionselectionsinfo(authordict: dict, workdict: dict) -> dict:
	"""
	build the selections html either for a or b:
		#selectionstable + #selectioninfocell
		#selectionstable + #exclusioninfocell
	there are seven headings to populate
		[a] author classes
		[b] work genres
		[c] author location
		[d] work provenance
		[e] author selections
		[f] work selections
		[g] passage selections

	id numbers need to be attached to the selections so that they can be double-clicked so as to delete them

	:param authordict:
	:return:
	"""

	returndict = dict()
	thejs = list()

	tit = 'title="Double-click to remove this item"'

	try:
		# it is possible to hit this function before the session has been set, so...
		session['auselections']
	except KeyError:
		probeforsessionvariables()

	sessionsearchlist = session['auselections'] + session['agnselections'] + session['wkgnselections'] + \
	                    session['psgselections'] + session['wkselections'] + session['alocselections'] + \
	                    session['wlocselections']

	for selectionorexclusion in ['selections', 'exclusions']:
		thehtml = list()
		# if there are no explicit selections, then
		if not sessionsearchlist and selectionorexclusion == 'selections':
			thehtml.append('<span class="picklabel">Authors</span><br />')
			thehtml.append('[All in active corpora less exclusions]<br />')

		if selectionorexclusion == 'exclusions' and not sessionsearchlist and session['spuria'] == 'Y' and \
				not session['wkgnexclusions'] and not session['agnexclusions'] and not session['auexclusions']:
			thehtml.append('<span class="picklabel">Authors</span><br />')
			thehtml.append('[No exclusions]<br />')

		# [a] author classes
		v = 'agn'
		var = v + selectionorexclusion
		if session[var]:
			thehtml.append('<span class="picklabel">Author categories</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [b] work genres
		v = 'wkgn'
		var = v + selectionorexclusion
		if session[var]:
			thehtml.append('<span class="picklabel">Work genres</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [c] author location
		v = 'aloc'
		var = v + selectionorexclusion
		if session[var]:
			thehtml.append('<span class="picklabel">Author location</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [d] work provenance
		v = 'wloc'
		var = v + selectionorexclusion
		if session[var]:
			thehtml.append('<span class="picklabel">Work provenance</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [e] authors
		v = 'au'
		var = v + selectionorexclusion
		if session[var]:
			thehtml.append('<span class="picklabel">Authors</span><br />')
			localval = -1
			for s in session[var]:
				localval += 1
				ao = authordict[s]
				thehtml.append('<span class="{v}{soe} selection" id="{var}_0{lv}" {tit}>{s}</span>'
				               '<br />'.format(v=v, soe=selectionorexclusion, var=var, lv=localval, s=ao.akaname, tit=tit))
				thejs.append((var, localval))

		# [f] works
		v = 'wk'
		var = v + selectionorexclusion
		if session[var] and selectionorexclusion == 'exclusions' and session['spuria'] == 'N':
			thehtml.append('<span class="picklabel">Works</span><br />')
			thehtml.append('[All non-selected spurious works]<br />')

		if session[var]:
			thehtml.append('<span class="picklabel">Works</span><br />')
			if selectionorexclusion == 'exclusions' and session['spuria'] == 'N':
				thehtml.append('[Non-selected spurious works]<br />')
			localval = -1
			for s in session[var]:
				localval += 1
				uid = s[:6]
				ao = authordict[uid]
				wk = workdict[s]
				thehtml.append('<span class="{v}{soe} selection" id="{var}_0{lv}" {tit}>{au}, '
			               '<span class="pickedwork">{wk}</span></span>' 
				           '<br />'.format(v=v, var=var, soe=selectionorexclusion, lv=localval, au=ao.akaname,
				                           tit=tit, wk=wk.title))
				thejs.append((var, localval))

		# [g] passages
		v = 'psg'
		var = v + selectionorexclusion
		if session[var]:
			psgtemplate = '<span class="{v}{soe} selection" id="{var}_0{lv}" {tit}>{au}, <span class="pickedwork">{wk}</span>&nbsp; <span class="pickedsubsection">{loc}</span></span><br />'
			spantemplate = 'from {a} to {b}'
			thehtml.append('<span class="picklabel">Passages</span><br />')
			localval = -1
			for s in session[var]:
				localval += 1
				uid = s[:6]
				ao = authordict[uid]
				loc = str()
				# watch out for heterogenous passage selection formats; only _AT_ and _FROM_ exist ATM
				# session[psgselections] = ['lt0474w005_FROM_4501_TO_11915', 'lt2806w002_AT_3|4|5']
				if '_AT_' in s:
					locus = s.split('_AT_')[1].split('|')
					locus.reverse()
					citationtuple = tuple(locus)
					for w in ao.listofworks:
						if w.universalid == s[0:10]:
							wk = w
					loc = prolixlocus(wk, citationtuple)
				elif '_FROM_' in s:
					dbconnection = ConnectionObject()
					dbcursor = dbconnection.cursor()
					wk = workdict[s[0:10]]
					locus = s.split('_FROM_')[1]
					start = locus.split('_TO_')[0]
					stop = locus.split('_TO_')[1]
					startln = dblineintolineobject(grabonelinefromwork(uid, start, dbcursor))
					stopln = dblineintolineobject(grabonelinefromwork(uid, stop, dbcursor))
					dbconnection.connectioncleanup()
					# print('_FROM_', start, stop, startln.uncleanlocustuple(), stopln.uncleanlocustuple())
					loc = spantemplate.format(a=startln.prolixlocus(), b=stopln.prolixlocus())

				thehtml.append(psgtemplate.format(v=v, var=var, soe=selectionorexclusion, lv=localval, au=ao.akaname, wk=wk.title, loc=loc, tit=tit))
				thejs.append((var, localval))

		returndict[selectionorexclusion] = '\n'.join(thehtml)

	scount = len(session['auselections'] + session['wkselections'] + session['agnselections'] +
	                           session['wkgnselections'] + session['psgselections'] + session['alocselections'] +
	                           session['wlocselections'])
	scount += len(session['auexclusions'] + session['wkexclusions'] + session['agnexclusions'] +
	                           session['wkgnexclusions'] + session['psgexclusions'] + session['alocexclusions'] +
	                           session['wlocexclusions'])

	returndict['numberofselections'] = -1
	if scount > 0:
		returndict['numberofselections'] = scount

	returndict['jstuples'] = thejs

	return returndict


def selectionlinehtmlandjs(v: str, selectionorexclusion: str, thesession: session) -> dict:
	"""

	generate something like:

		<span class="agnselections" id="agnselections_00" listval="0">Alchemistae</span>

	:param v:
	:param selectionorexclusion:
	:param localval:
	:param thesession:
	:return:
	"""

	var = v + selectionorexclusion
	thehtml = list()
	thejs = list()
	localval = -1
	tit = 'title="Double-click to remove this item"'

	for s in thesession[var]:
		localval += 1
		thehtml.append('<span class="{v}{soe} selection" id="{var}_0{lv}" {tit}>{s}</span>' \
		               '<br />'.format(v=v, soe=selectionorexclusion, var=var, lv=localval, tit=tit, s=s))
		thejs.append((var, localval))

	returndict = {'html': thehtml, 'js': thejs}

	return returndict
