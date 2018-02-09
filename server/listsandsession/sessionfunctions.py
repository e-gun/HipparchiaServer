# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server import hipparchia
from server.dbsupport.citationfunctions import prolixlocus
from server.dbsupport.dbfunctions import probefordatabases
from server.startup import authorgenresdict, authorlocationdict, workgenresdict, workprovenancedict


def sessionvariables():

	try:
		session['greekcorpus']
	except KeyError:
		# print('resetting session variables')
		session['agnexclusions'] = list()
		session['agnselections'] = list()
		session['alocexclusions'] = list()
		session['alocselections'] = list()
		session['auexclusions'] = list()
		session['auselections'] = list()
		session['authorssummary'] = hipparchia.config['DEFAULTSHOWLEXICALAUTHORS']
		session['available'] = probefordatabases()
		session['bracketangled'] = hipparchia.config['DEFAULTHIGHLIGHTANGLEDBRACKETS']
		session['bracketcurly'] = hipparchia.config['DEFAULTHIGHLIGHTCURLYBRACKETS']
		session['bracketround'] = hipparchia.config['DEFAULTHIGHLIGHTROUNDBRACKETS']
		session['bracketsquare'] = hipparchia.config['DEFAULTHIGHLIGHTSQUAREBRACKETS']
		session['browsercontext'] = str(int(hipparchia.config['DEFAULTBROWSERLINES']))
		session['christiancorpus'] = hipparchia.config['DEFAULTCHRISTIANCORPUSVALUE']
		session['cosdistbysentence'] = 'no'
		session['cosdistbylineorword'] = 'no'
		session['earliestdate'] = hipparchia.config['DEFAULTEARLIESTDATE']
		session['greekcorpus'] = hipparchia.config['DEFAULTGREEKCORPUSVALUE']
		session['headwordindexing'] = hipparchia.config['DEFAULTINDEXBYHEADWORDS']
		session['incerta'] = hipparchia.config['DEFAULTINCERTA']
		session['indexbyfrequency'] = hipparchia.config['DEFAULTINDEXBYFREQUENCY']
		session['inscriptioncorpus'] = hipparchia.config['DEFAULTINSCRIPTIONCORPUSVALUE']
		session['latestdate'] = hipparchia.config['DEFAULTLATESTDATE']
		session['latincorpus'] = hipparchia.config['DEFAULTLATINCORPUSVALUE']
		session['linesofcontext'] = int(hipparchia.config['DEFAULTLINESOFCONTEXT'])
		session['maxresults'] = str(int(hipparchia.config['DEFAULTMAXRESULTS']))
		session['nearestneighborsquery'] = 'no'
		session['nearornot'] = 'T'
		session['onehit'] = hipparchia.config['DEFAULTONEHIT']
		session['papyruscorpus'] = hipparchia.config['DEFAULTPAPYRUSCORPUSVALUE']
		session['proximity'] = '1'
		session['psgexclusions'] = list()
		session['psgselections'] = list()
		session['quotesummary'] = hipparchia.config['DEFAULTSHOWLEXICALQUOTES']
		session['searchscope'] = 'L'
		session['semanticvectorquery'] = 'no'
		session['sensesummary'] = hipparchia.config['DEFAULTSHOWLEXICALSENSES']
		session['sortorder'] = hipparchia.config['DEFAULTSORTORDER']
		session['spuria'] = hipparchia.config['DEFAULTSPURIA']
		session['varia'] = hipparchia.config['DEFAULTVARIA']
		session['wkexclusions'] = list()
		session['wkgnexclusions'] = list()
		session['wkgnselections'] = list()
		session['wkselections'] = list()
		session['wlocexclusions'] = list()
		session['wlocselections'] = list()
		session['xmission'] = 'Any'

	return


def modifysessionvar(param, val):
	"""

	set session variables after checking them for validity

	:param param:
	:param val:
	:return:
	"""

	availableoptions = [
		'authorssummary',
		'bracketangled',
		'bracketcurly',
		'bracketround',
		'bracketsquare',
		'browsercontext',
		'christiancorpus',
		'cosdistbylineorword',
		'cosdistbysentence',
		'earliestdate',
		'greekcorpus',
		'headwordindexing',
		'incerta',
		'indexbyfrequency',
		'inscriptioncorpus',
		'latestdate',
		'latincorpus',
		'linesofcontext',
		'maxresults',
		'nearestneighborsquery',
		'nearornot',
		'onehit',
		'papyruscorpus',
		'proximity',
		'quotesummary',
		'searchscope',
		'semanticvectorquery',
		'sensesummary',
		'sortorder',
		'spuria',
		'varia'
		]

	if param in availableoptions:
		session[param] = val
		# print('param = val:', param, session[param])
	else:
		# print('param not found:', param)
		pass

	# drop all selections/exclusions from any corpus that you just disabled
	if param in ['greekcorpus', 'latincorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus'] and session[param] != 'yes':
		corpora = {'greekcorpus': 'gr', 'latincorpus': 'lt', 'inscriptioncorpus': 'in', 'papyruscorpus': 'dp', 'christiancorpus': 'ch'}
		lists = ['auselections', 'psgselections', 'wkselections', 'auexclusions', 'psgexclusions', 'wkexclusions']
		for l in lists:
			session[l] = [item for item in session[l] if not re.search(r'^'+corpora[param], item)]

		# authorgenresdict, authorlocationdict, workgenresdict, workprovenancedict
		checkagainst = {'agnselections': authorgenresdict,
						'wkgnselections': workgenresdict,
						'alocselections': authorlocationdict,
						'wlocselections': workprovenancedict,
						'agnexclusions': authorgenresdict,
						'wkgnexclusions': workgenresdict,
						'alocexclusions': authorlocationdict,
						'wlocexclusions': workprovenancedict}
		for l in checkagainst.keys():
			session[l] = [item for item in session[l] if item in returnactivelist(checkagainst[l])]

	# our yes/no options
	for variable in ['greekcorpus', 'latincorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus',
					'varia', 'incerta', 'spuria', 'onehit', 'headwordindexing', 'sensesummary', 'authorssummary',
					'quotesummary', 'bracketsquare', 'bracketround', 'bracketangled', 'bracketcurly',
					'indexbyfrequency', 'cosdistbysentence', 'cosdistbylineorword', 'semanticvectorquery',
					'nearestneighborsquery']:
		if session[variable] not in ['yes', 'no']:
			session[variable] = 'no'

	# only one of these can be active at one time
	if param == 'cosdistbysentence' and val == 'yes':
		session['cosdistbylineorword'] = 'no'
		session['semanticvectorquery'] = 'no'
		session['nearestneighborsquery'] = 'no'

	if param == 'cosdistbylineorword' and val == 'yes':
		session['cosdistbysentence'] = 'no'
		session['semanticvectorquery'] = 'no'
		session['nearestneighborsquery'] = 'no'

	if param == 'semanticvectorquery' and val == 'yes':
		session['cosdistbysentence'] = 'no'
		session['cosdistbylineorword'] = 'no'
		session['nearestneighborsquery'] = 'no'

	if param == 'nearestneighborsquery' and val == 'yes':
		session['cosdistbysentence'] = 'no'
		session['cosdistbylineorword'] = 'no'
		session['semanticvectorquery'] = 'no'

	if session['nearornot'] not in ['T', 'F']:
		session['nearornot'] = 'T'

	try:
		int(session['maxresults'])
	except:
		session['maxresults'] = '500'

	try:
		if int(session['proximity']) > 15:
			session['proximity'] = '15'
	except ValueError:
		# ValueError: invalid literal for int() with base 10: 'null'
		session['proximity'] = '5'

	if int(session['proximity']) < 1:
		session['proximity'] = '1'

	try:
		int(session['linesofcontext'])
	except ValueError:
		# you probably had 'null' because you were clearing/typing rather than spinning the value
		session['linesofcontext'] = int(hipparchia.config['DEFAULTLINESOFCONTEXT'])

	if int(session['linesofcontext']) > 20:
		session['linesofcontext'] = '20'

	if int(session['linesofcontext']) < 0:
		session['linesofcontext'] = '0'

	try:
		# if you edit the box you can easily generate a null which will turn into an error
		if int(session['earliestdate']) < -850 or int(session['earliestdate']) > 1500:
			session['earliestdate'] = '-850'
	except ValueError:
		session['earliestdate'] = '-850'
	try:
		if int(session['latestdate']) < -850 or int(session['latestdate']) > 1500:
			session['latestdate'] = '1500'
	except ValueError:
		session['latestdate'] = '1500'

	# skip this check because as you are typing into the spinner you will generate intermediate values that will ruin things
	# if int(session['earliestdate']) > int(session['latestdate']):
	# 	session['earliestdate'] = session['latestdate']
	if int(session['maxresults']) < 1:
		session['maxresults'] = '1'

	if session['sortorder'] not in ['universalid', 'shortname', 'genres', 'converted_date', 'location']:
		session['sortorder'] = 'shortname'

	if session['searchscope'] not in ['L', 'W']:
		session['searchscope'] = 'L'

	if int(session['browsercontext']) < 5 or int(session['browsercontext']) > 100:
		session['browsercontext'] = '20'

	# print('set',param,'to',session[param])
	session.modified = True

	return


def modifysessionselections(cookiedict, authorgenreslist, workgenreslist, authorlocationlist, workprovenancelist):
	"""
	set session selections after checking them for validity
	i'm not sure how many people will take the trouble to build evil cookies, but...
	:param cookiedict:
	:return:
	"""

	categories = {
		'au': {'validformat': re.compile(r'(lt|gr|in|dp)\w\w\w\w'), 'unacceptable': r'[!@#$|%()*\'\"]', 'checkagainst': None},
		'wk': {'validformat': re.compile(r'(lt|gr|in|dp)\w\w\w\ww\w\w\w'), 'unacceptable': r'[!@#$|%()*\'\"]', 'checkagainst': None},
		'psg': {'validformat': re.compile(r'(lt|gr|in|dp)\w\w\w\ww\w\w\w_AT_'), 'unacceptable': r'[!@#$%()*\'\"]', 'checkagainst': None},
		'agn': {'validformat': None, 'unacceptable': r'[!@#$%*\'\"]', 'checkagainst': authorgenreslist},
		'wkgn': {'validformat': None, 'unacceptable': r'[!@#$%*\'\"]', 'checkagainst': workgenreslist},
		'aloc': {'validformat': None, 'unacceptable': r'[!@#$%*\'\"]', 'checkagainst': authorlocationlist},
		'wloc': {'validformat': None, 'unacceptable': r'[!@#$%*\'\"]', 'checkagainst': workprovenancelist}
	}

	for option in ['selections', 'exclusions']:
		for cat in categories:
			cookievals = cookiedict[cat+option]
			for item in cookievals:
				if len(item) == 0:
					cookievals.remove(item)
				elif categories[cat]['validformat']:
					if re.search(categories[cat]['validformat'],item) is None:
						cookievals.remove(item)
				elif categories[cat]['unacceptable']:
					if re.search(categories[cat]['unacceptable'], item):
						cookievals.remove(item)
				elif categories[cat]['checkagainst']:
					if item not in categories[cat]['checkagainst']:
						cookievals.remove(item)

			session[cat+option] = cookievals

	session.modified = True

	return


def parsejscookie(cookiestring):
	"""
	turn the string into a dict
	a shame this has to be written
	
	example cookies:
		{%22searchsyntax%22:%22R%22%2C%22linesofcontext%22:6%2C%22agnselections%22:[%22Alchemistae%22%2C%22Biographi%22]%2C%22corpora%22:%22G%22%2C%22proximity%22:%221%22%2C%22sortorder%22:%22shortname%22%2C%22maxresults%22:%22250%22%2C%22auselections%22:[%22gr0116%22%2C%22gr0199%22]%2C%22xmission%22:%22Any%22%2C%22browsercontext%22:%2220%22%2C%22latestdate%22:%221500%22%2C%22psgselections%22:[]%2C%22searchscope%22:%22L%22%2C%22wkselections%22:[%22gr1908w003%22%2C%22gr2612w001%22]%2C%22authenticity%22:%22Any%22%2C%22earliestdate%22:%22-850%22%2C%22wkgnselections%22:[%22Caten.%22%2C%22Doxogr.%22]}	:return:
	"""
	try:
		cookiestring = cookiestring[1:-1]
	except:
		# must have tried to load a cookie that was not really there
		cookiestring = ''
	
	selectioncategories = ['auselections', 'wkselections', 'agnselections', 'wkgnselections', 'psgselections',
						   'auexclusions', 'wkexclusions', 'agnexclusions', 'wkgnexclusions', 'psgexclusions',
						   'alocselections', 'alocexclusions', 'wlocselections', 'wlocexclusions' ]

	selectiondictionary = {}
	for sel in selectioncategories:
		try:
			selectiondictionary[sel] = re.search(r'%22' + sel + r'%22:\[(.*?)\]', cookiestring).group(1)
		except:
			selectiondictionary[sel] = ''

	# found; but mangled entries still:
	# {'agnselections': '%22Alchemistae%22%2C%22Biographi%22', 'wkselections': '%22gr1908w003%22%2C%22gr2612w001%22', 'psgselections': '', 'auselections': '%22gr0116%22%2C%22gr0199%22', 'wkgnselections': '%22Caten.%22%2C%22Doxogr.%22'}
	
	for sel in selectiondictionary:
		selectiondictionary[sel] = re.sub(r'%20', '', selectiondictionary[sel])
		selectiondictionary[sel] = re.sub(r'%22', '', selectiondictionary[sel])
		selectiondictionary[sel] = selectiondictionary[sel].split('%2C')
	
	nonselections = cookiestring
	for sel in selectioncategories:
		try:
			nonselections = re.sub(re.escape(re.search(r'%22' + sel + r'%22:\[(.*?)\]', nonselections).group(0)), '', nonselections)
		except:
			nonselections = ''
			
	nonselections = re.sub(r'%22', '', nonselections)
	allotheroptions = nonselections.split('%2C')
	allotheroptions[:] = [x for x in allotheroptions if x != '']
	
	optiondict = {}
	for o in allotheroptions:
		halves = o.split(':')
		if halves[0] != 'selections':
			optiondict[halves[0]] = halves[1]
		else:
			pass
	
	optiondict.update(selectiondictionary)
	
	return optiondict


def sessionselectionsashtml(authordict, workdict):
	"""
	assemble the html to be fed into the json that goes to the js that fills #selectionstable
	three chunks: time; selections; exclusions
	:param authordict, workdict:
	:return:
	"""

	selectioninfo = dict()
	
	selectioninfo['timeexclusions'] = sessiontimeexclusionsinfo()
	sxhtml = sessionselectionsinfo(authordict, workdict)
	
	selectioninfo['selections'] = sxhtml['selections']
	selectioninfo['exclusions'] = sxhtml['exclusions']
	# selectioninfo['scount'] = sxhtml['scount']
	# selectioninfo['xcount'] = sxhtml['xcount']
	selectioninfo['newjs'] = sessionselectionsjs(sxhtml['jstuples'])

	# numberofselections is -1 if there were no selections
	# returning this will hide the selections table; but it should not be hidden if there are time restrictions or spuria restrictions
	# so say '0' instead
	if sxhtml['numberofselections'] == -1 and (selectioninfo['timeexclusions'] != '' or session['spuria'] == 'no'):
		selectioninfo['numberofselections'] = 0
	else:
		selectioninfo['numberofselections'] = sxhtml['numberofselections']
	
	return selectioninfo


def sessionselectionsjs(labeltupleslist):
	"""
	
	build js out of something like:
	
		[('agnselections', 0), ('auselections', 0), ('auselections', 1)]
	
	:param labeltuples: 
	:return: 
	"""

	template = """
		$( '#{label}_0{number}' ).dblclick(function() lbrk
			$.getJSON('/clearselections?cat={label}&id={number}', function (selectiondata) lbrk 
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
	timerestrictions = ''
	
	# managing to get here without dates already set: KeyError: 'latestdate'
	try:
		session['latestdate']
	except:
		session['latestdate'] = '1500'
		session['earliestdate'] = '-850'
		
	if session['latestdate'] != '1500' or session['earliestdate'] != '-850':
		if int(session['earliestdate']) < 0:
			e = session['earliestdate'][1:] + ' B.C.E'
		else:
			e = session['earliestdate'] + ' C.E'
		if int(session['latestdate']) < 0:
			l = session['latestdate'][1:] + ' B.C.E'
		else:
			l = session['latestdate'] + ' C.E'
			
		timerestrictions ='Unless specifically listed, authors/works must come from {e}&nbspto&nbsp;{l}'.format(e=e, l=l)

	return timerestrictions


def sessionselectionsinfo(authordict, workdict):
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
		sessionvariables()

	sessionsearchlist = session['auselections'] + session['agnselections'] + session['wkgnselections'] + \
	                    session['psgselections'] + session['wkselections'] + session['alocselections'] + \
	                    session['wlocselections']

	for selectionorexclusion in ['selections', 'exclusions']:
		thehtml = list()
		# if there are no explicit selections, then
		if len(sessionsearchlist) == 0 and selectionorexclusion == 'selections':
			thehtml.append('<span class="picklabel">Authors</span><br />')
			thehtml.append('[All in active corpora less exclusions]<br />')

		if selectionorexclusion == 'exclusions' and len(sessionsearchlist) == 0 and session['spuria'] == 'Y' and len(
				session['wkgnexclusions']) == 0 and len(session['agnexclusions']) == 0 and len(
			session['auexclusions']) == 0:
			thehtml.append('<span class="picklabel">Authors</span><br />')
			thehtml.append('[No exclusions]<br />')

		# [a] author classes
		v = 'agn'
		var = v + selectionorexclusion
		if len(session[var]) > 0:
			thehtml.append('<span class="picklabel">Author categories</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [b] work genres
		v = 'wkgn'
		var = v + selectionorexclusion
		if len(session[var]) > 0:
			thehtml.append('<span class="picklabel">Work genres</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [c] author location
		v = 'aloc'
		var = v + selectionorexclusion
		if len(session[var]) > 0:
			thehtml.append('<span class="picklabel">Author location</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [d] work provenance
		v = 'wloc'
		var = v + selectionorexclusion
		if len(session[var]) > 0:
			thehtml.append('<span class="picklabel">Work provenance</span><br />')
			htmlandjs = selectionlinehtmlandjs(v, selectionorexclusion, session)
			thehtml += htmlandjs['html']
			thejs += htmlandjs['js']

		# [e] authors
		v = 'au'
		var = v + selectionorexclusion
		if len(session[var]) > 0:
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
		if len(session[var]) == 0 and selectionorexclusion == 'exclusions' and session['spuria'] == 'N':
			thehtml.append('<span class="picklabel">Works</span><br />')
			thehtml.append('[All non-selected spurious works]<br />')

		if len(session[var]) > 0:
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
		if len(session[var]) > 0:
			thehtml.append('<span class="picklabel">Passages</span><br />')
			localval = -1
			for s in session[var]:
				localval += 1
				locus = s[14:].split('|')
				# print('l', s, s[:6], s[7:10], s[14:], locus)
				locus.reverse()
				citationtuple = tuple(locus)
				uid = s[:6]
				ao = authordict[uid]
				for w in ao.listofworks:
					if w.universalid == s[0:10]:
						wk = w
				loc = prolixlocus(wk, citationtuple)
				thehtml.append('<span class="{v}{soe} selection" id="{var}_0{lv}" {tit}>{au}, '
				               '<span class="pickedwork">{wk}</span>&nbsp;'
				               '<span class="pickedsubsection">{loc}</span></span><br />'
				               ''.format(v=v, var=var, soe=selectionorexclusion, lv=localval, au=ao.akaname,
				                           wk=wk.title, loc=loc, tit=tit))
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


def selectionlinehtmlandjs(v, selectionorexclusion, session):
	"""
	
	generate something like:
	
		<span class="agnselections" id="agnselections_00" listval="0">Alchemistae</span>
	
	:param v: 
	:param selectionorexclusion: 
	:param localval: 
	:param session: 
	:return: 
	"""

	var = v + selectionorexclusion
	thehtml = list()
	thejs = list()
	localval = -1
	tit = 'title="Double-click to remove this item"'

	for s in session[var]:
		localval += 1
		thehtml.append('<span class="{v}{soe} selection" id="{var}_0{lv}" {tit}>{s}</span>' \
		               '<br />'.format(v=v, soe=selectionorexclusion, var=var, lv=localval, tit=tit, s=s))
		thejs.append((var, localval))

	returndict = {'html': thehtml, 'js': thejs}

	return returndict


def rationalizeselections(newselectionuid, selectorexclude):
	"""
	tidy up things after 'makeselection'
	toggle choices based on other choices
	if you choose an author whose work is already chosen, then drop the work from the relevant list: just search the author
	if you choose a work whose author is already chosen, then drop the author from the relevant list: just search the work
	etc
	
	selectorexclude should be either 'selections' or 'exclusions'

	TODO: locations are not in here yet

	"""
	
	suffix = selectorexclude
	if suffix == 'selections':
		other = 'exclusions'
	else:
		other = 'selections'
	
	# the uid (and the len) of the new selection implies the category of the selection
	if len(newselectionuid) == 6:
		# add an author --> clean works, passages; clean opposed authorlist, worklist, passagelist
		for item in session['wk'+suffix]:
			if newselectionuid in item:
				session['wk'+suffix].remove(item)
		for item in session['psg'+suffix]:
			if newselectionuid in item:
				session['psg'+suffix].remove(item)
		# others
		for item in session['au'+other]:
			if newselectionuid in item:
				session['au'+other].remove(item)
		for item in session['wk'+other]:
			if newselectionuid in item:
				session['wk'+other].remove(item)
		for item in session['psg'+other]:
			if newselectionuid in item:
				session['psg'+other].remove(item)
	elif len(newselectionuid) == 10:
		# add a work --> clean authors, passages; clean opposed worklist, opposed passagelist
		for item in session['psg'+suffix]:
			if newselectionuid in item:
				session['psg'+suffix].remove(item)
		for item in session['au'+suffix]:
			if newselectionuid[0:6] in item:
				session['au'+suffix].remove(item)
		# others
		for item in session['au'+other]:
			if newselectionuid in item:
				session['au'+other].remove(item)
		for item in session['wk'+other]:
			if newselectionuid in item:
				session['wk'+other].remove(item)
		for item in session['psg'+other]:
			if newselectionuid in item:
				session['psg'+other].remove(item)
	elif len(newselectionuid) > 10:
		# add a passage --> clean authors, works; clean opposed passagelist
		for item in session['wk'+suffix]:
			if newselectionuid[0:10] in item:
				session['wk'+suffix].remove(item)
		for item in session['au'+suffix]:
			if newselectionuid[0:6] in item:
				session['au'+suffix].remove(item)
		# others
		for item in session['psg'+other]:
			if newselectionuid in item:
				session['psg'+other].remove(item)
	else:
		# impossible, right?
		pass
	
	session.modified = True

	return


def corpusselectionsasavalue():
	"""

	represent the active corpora as a pseudo-binary value: '10101' for ON/OFF/ON/OFF/ON

		l g i p c
		1 2 3 4 5

	:return: 24, etc
	"""
	binarystring = '0b'

	for s in ['latincorpus', 'greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus']:
		if session[s] == 'yes':
			binarystring += '1'
		else:
			binarystring += '0'

	binaryvalue = int(binarystring,2)

	return binaryvalue


def corpusselectionsaspseudobinarystring():
	"""

	represent the active corpora as a pseudo-binary value: '10101' for ON/OFF/ON/OFF/ON

		l g i p c
		1 2 3 4 5

	:return: '11100', etc
	"""
	binarystring = ''

	for s in ['latincorpus', 'greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus']:
		if session[s] == 'yes':
			binarystring += '1'
		else:
			binarystring += '0'

	return binarystring


def justlatin():
	"""

	probe the session to see if we are working in a latin-only environment: '10000' = 16

	:return: True or False
	"""

	if corpusselectionsasavalue() == 16:
		return True
	else:
		return False


def justtlg():
	"""

	probe the session to see if we are working in a tlg authors only environment: '01000' = 8

	:return: True or False
	"""

	if corpusselectionsasavalue() == 8:
		return True
	else:
		return False


def justinscriptions():
	"""

	probe the session to see if we are working in a inscriptions-only environment: '00100' = 2
	useful in as much as the inscriptions data leaves certain columns empty every time

	:return: True or False
	"""

	if corpusselectionsasavalue() == 4:
		return True
	else:
		return False


def justpapyri():
	"""

	probe the session to see if we are working in a papyrus-only environment: '00010' = 2
	useful in as much as the papyrus data leaves certain columns empty every time

	:return: True or False
	"""

	if corpusselectionsasavalue() == 2:
		return True
	else:
		return False


def justlit():
	"""

	probe the session to see if we are working in a TLG + LAT environment: '11000' = 24

	:return: True or False
	"""

	if corpusselectionsasavalue() == 24:
		return True
	else:
		return False


def justdoc():
	"""

	probe the session to see if we are working in a DDP + INS environment: '00110' = 6

	:return: True or False
	"""

	if corpusselectionsasavalue() == 6:
		return True
	else:
		return False


def reducetosessionselections(listmapper, criterion):
	"""

	drop the full universe of possibilities and include only those that meet the active session criteria

	listmapper = {
		'gr': {'a': tlgauthors, 'w': tlgworks},
		'lt': {'a': latauthors, 'w': latworks},
		'in': {'a': insauthors, 'w': insworks},
		'dp': {'a': ddpauthors, 'w': ddpworks},
		'ch': {'a': chrauthors, 'w': chrworks}
	}

	criterion: 'a' or 'w'

	:param:
	:return: a relevant dictionary
	"""

	# the order here has to match the order in corpusselectionsasavalue()
	# a nice source of bugs if you try to refactor elsewhere

	corpora = ('lt', 'gr', 'in', 'dp', 'ch')
	
	active = corpusselectionsaspseudobinarystring()

	toactivate = list()
	position = -1

	for a in active:
		# example: 11001 = lt + gr - in - dp + ch
		position += 1
		if a == '1':
			toactivate.append(corpora[position])

	d = {}

	# print('active corpora',toactivate)

	for a in toactivate:
		d.update(listmapper[a][criterion])

	return d


def returnactivedbs():
	"""

	what dbs are currently active?
	return a list of keys to a target dict

	:return:
	"""

	keys = list()
	if session['latincorpus'] == 'yes':
		keys.append('lt')
	if session['greekcorpus'] == 'yes':
		keys.append('gr')
	if session['inscriptioncorpus'] == 'yes':
		keys.append('in')
	if session['papyruscorpus'] == 'yes':
		keys.append('dp')
	if session['christiancorpus'] == 'yes':
		keys.append('ch')

	return keys


def findactivebrackethighlighting(s=session):
	"""

	what kinds of brackets are we highlighting

	:return:
	"""

	brackets = list()

	if s['bracketsquare'] == 'yes':
		brackets.append('square')
	if s['bracketround'] == 'yes':
		brackets.append('round')
	if s['bracketangled'] == 'yes':
		brackets.append('angled')
	if s['bracketcurly'] == 'yes':
		brackets.append('curly')
	return brackets


def selectionisactive(selected):
	"""

	if you disable a corpus with an something still in the selction box, it remains possible to request that author, work, etc.
	make it impossible to add an author or work that will not get searched

	this function will cover authors/works/passages; genres and locations gets handled via calls to returnactivelist()

	:param selected:
	:return:
	"""

	active = returnactivedbs()
	try:
		prefix = selected[0:2]
	except:
		prefix = ''

	if prefix not in active:
		selected = ''

	return selected


def returnactivelist(selectiondict):
	"""

	what author categories, etc can you pick at the moment?

	selectiondict is something like authorgenresdict or workgenresdict

	:return:
	"""

	activedbs = returnactivedbs()

	activelist = list()
	for db in activedbs:
		activelist += selectiondict[db]

	activelist = list(set(activelist))

	return activelist

