# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server import hipparchia
from server.dbsupport import citationfunctions


def sessionvariables():

	try:
		session['greekcorpus']
	except:
		# print('resetting session variables')
		session['auselections'] = []
		session['wkselections'] = []
		session['agnselections'] = []
		session['wkgnselections'] = []
		session['psgselections'] = []
		session['auexclusions'] = []
		session['wkexclusions'] = []
		session['agnexclusions'] = []
		session['wkgnexclusions'] = []
		session['psgexclusions'] = []
		session['alocselections'] = []
		session['alocexclusions'] = []
		session['wlocselections'] = []
		session['wlocexclusions'] = []
		session['greekcorpus'] = hipparchia.config['DEFAULTGREEKCORPUSVALUE']
		session['latincorpus'] = hipparchia.config['DEFAULTLATINCORPUSVALUE']
		session['inscriptioncorpus'] = hipparchia.config['DEFAULTINSCRIPTIONCORPUSVALUE']
		session['papyruscorpus'] = hipparchia.config['DEFAULTPAPYRUSCORPUSVALUE']
		session['christiancorpus'] = hipparchia.config['DEFAULTCHRISTIANCORPUSVALUE']
		session['accentsmatter'] = 'N'
		session['proximity'] = '1'
		session['nearornot'] = 'T'
		session['searchscope'] = 'L'
		session['linesofcontext'] = int(hipparchia.config['DEFAULTLINESOFCONTEXT'])
		session['browsercontext'] = str(int(hipparchia.config['DEFAULTBROWSERLINES']))
		session['maxresults'] = str(int(hipparchia.config['DEFAULTMAXRESULTS']))
		session['sortorder'] = hipparchia.config['DEFAULTSORTORDER']
		session['earliestdate'] = hipparchia.config['DEFAULTEARLIESTDATE']
		session['latestdate'] = hipparchia.config['DEFAULTLATESTDATE']
		session['xmission'] = 'Any'
		session['spuria'] = 'Y'

	return


def modifysessionvar(param,val):
	"""
	set session varaibles after checking them for validity

	:param param:
	:param val:
	:return:
	"""

	availableoptions = [
		'accentsmatter',
		'proximity',
		'searchscope',
		'maxresults',
		'linesofcontext',
		'browsercontext',
		'sortorder',
		'nearornot',
		'earliestdate',
		'latestdate',
		'spuria',
		'greekcorpus',
		'latincorpus',
		'inscriptioncorpus',
		'papyruscorpus',
		'christiancorpus'
		]

	if param in availableoptions:
		session[param] = val
		# print('param = val:',param,session[param])

	for corpus in ['greekcorpus', 'latincorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus']:
		if session[corpus] not in ['yes', 'no']:
			session[corpus] = 'no'

	# may need to kill off old selections from the 'other' language
	# do this after sorting out corpus shifts
	if justlatin():
		session['auselections'] = []
		session['wkselections'] = []
		session['agnselections'] = []
		session['wkgnselections'] = []
		session['psgselections'] = []
		session['auexclusions'] = []
		session['wkexclusions'] = []
		session['agnexclusions'] = []
		session['wkgnexclusions'] = []
		session['psgexclusions'] = []

	if session['nearornot'] not in ['T', 'F']:
		session['nearornot'] = 'T'
	
	if session['spuria'] not in ['Y', 'N']:
		session['spuria'] = 'Y'
		
	try:
		int(session['maxresults'])
	except:
		session['maxresults'] = '500'

	if session['accentsmatter'] not in ['Y','N']:
		session['accentsmatter'] = 'N'

	if int(session['proximity']) > 10:
		session['proximity'] = '9'

	if int(session['linesofcontext']) > 20:
		session['linesofcontext'] = '20'

	try:
		# if you edit the box you can easily generate a null which will turn into an error
		if int(session['earliestdate']) < -850 or int(session['earliestdate']) > 1500:
			session['earliestdate'] = '-850'
	except:
		session['earliestdate'] = '-850'
	try:
		if int(session['latestdate']) < -850 or int(session['latestdate']) > 1500:
			session['latestdate'] = '1500'
	except:
		session['latestdate'] = '1500'

	# skip this check because as you are typing into the spinner you will generate intermediate values that will ruin things
	# if int(session['earliestdate']) > int(session['latestdate']):
	# 	session['earliestdate'] = session['latestdate']
	if int(session['maxresults']) < 1:
		session['maxresults'] = '1'

	if session['sortorder'] not in ['universalid', 'shortname', 'genres', 'converted_date', 'location']:
		session['sortorder'] = 'shortname'

	if session['searchscope'] not in ['L','W']:
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
				elif categories[cat]['validformat'] is not None:
					if re.search(categories[cat]['validformat'],item) is None:
						cookievals.remove(item)
				elif categories[cat]['unacceptable'] is not None:
					if re.search(categories[cat]['unacceptable'], item) is not None:
						cookievals.remove(item)
				elif categories[cat]['checkagainst'] is not None:
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
		{%22searchsyntax%22:%22R%22%2C%22linesofcontext%22:6%2C%22agnselections%22:[%22Alchemistae%22%2C%22Biographi%22]%2C%22corpora%22:%22G%22%2C%22proximity%22:%221%22%2C%22sortorder%22:%22shortname%22%2C%22maxresults%22:%22250%22%2C%22auselections%22:[%22gr0116%22%2C%22gr0199%22]%2C%22xmission%22:%22Any%22%2C%22browsercontext%22:%2220%22%2C%22accentsmatter%22:%22N%22%2C%22latestdate%22:%221500%22%2C%22psgselections%22:[]%2C%22searchscope%22:%22L%22%2C%22wkselections%22:[%22gr1908w003%22%2C%22gr2612w001%22]%2C%22authenticity%22:%22Any%22%2C%22earliestdate%22:%22-850%22%2C%22wkgnselections%22:[%22Caten.%22%2C%22Doxogr.%22]}	:return:
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

	selectioninfo = {}
	
	selectioninfo['timeexclusions'] = sessiontimeexclusionsinfo()
	sxhtml = sessionselectionsinfo(authordict, workdict)
	
	selectioninfo['selections'] = sxhtml['selections']
	selectioninfo['exclusions'] = sxhtml['exclusions']
	
	# numberofselections is -1 if there were no selections
	# and this will hide the selections table; but it should not be hidden if there are time restrictions or spuria restrictions
	# so say '0' instead
	if sxhtml['numberofselections'] == -1 and (selectioninfo['timeexclusions'] != '' or session['spuria'] == 'N'):
		selectioninfo['numberofselections'] = 0
	else:
		selectioninfo['numberofselections'] = sxhtml['numberofselections']
	
	return selectioninfo


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
			
		timerestrictions ='Unless specifically listed, authors/works must come from</br />' + e + '&nbspto&nbsp;' + l + ''

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

	id numbers need to be attached to the selections so that they can be clicked-and-dragged to the trash by id
	this needs to be a sequential list and so we do both selections and exclusions in one go to keep one unified 'selcount'
	the selcount is used to generate a collection of jQuery .droppable()s

	:param authordict:
	:return: dictionary of html: {'selections':selhtml, 'exclusions':exclhtml, 'numberofselections': selcount}
	"""
	
	returndict = {}
	selcount = -1
	
	sessionsearchlist = session['auselections'] + session['agnselections'] + session['wkgnselections'] + \
	                    session['psgselections'] + session['wkselections'] + session['alocselections'] + \
						session['wlocselections']
	
	for selectionorexclusion in ['selections', 'exclusions']:
		thehtml = ''
		
		# if there are no explicit selections, then
		if len(sessionsearchlist) == 0 and selectionorexclusion == 'selections':
			thehtml += '<span class="picklabel">Authors</span><br />'
			thehtml += '[Full corpus less exclusions]<br />\n'
		
		if selectionorexclusion == 'exclusions' and len(sessionsearchlist) == 0 and session['spuria'] == 'Y' and len(
				session['wkgnexclusions']) == 0 and len(session['agnexclusions']) == 0 and len(session['auexclusions']) == 0:
			thehtml += '<span class="picklabel">Authors</span><br />'
			thehtml += '[No exclusions]<br />\n'
		
		# [a] author classes
		if len(session['agn' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Author categories</span><br />'
			localval = -1
			for s in session['agn' + selectionorexclusion]:
				selcount += 1
				localval += 1
				thehtml += '<span class="agn' + selectionorexclusion + '" id="searchselection_0' + str(selcount) + \
				           '" listval="' + str(localval) + '">' + s + '</span><br />\n'
		
		# [b] work genres
		if len(session['wkgn' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Work genres</span><br />'
			localval = -1
			for s in session['wkgn' + selectionorexclusion]:
				selcount += 1
				localval += 1
				thehtml += '<span class="wkgn' + selectionorexclusion + '" id="searchselection_0' + str(selcount) + \
				           '" listval="' + str(localval) + '">' + s + '</span><br />\n'

		# [c] author location
		if len(session['aloc' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Author location</span><br />'
			localval = -1
			for s in session['aloc' + selectionorexclusion]:
				selcount += 1
				localval += 1
				thehtml += '<span class="aloc' + selectionorexclusion + '" id="searchselection_0' + str(selcount) + \
				           '" listval="' + str(localval) + '">' + s + '</span><br />\n'

		# [d] work provenance
		if len(session['wloc' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Work provenance</span><br />'
			localval = -1
			for s in session['wloc' + selectionorexclusion]:
				selcount += 1
				localval += 1
				thehtml += '<span class="wloc' + selectionorexclusion + '" id="searchselection_0' + str(selcount) + \
				           '" listval="' + str(localval) + '">' + s + '</span><br />\n'

		# [e] authors
		if len(session['au' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Authors</span><br />'
			localval = -1
			for s in session['au' + selectionorexclusion]:
				selcount += 1
				localval += 1
				ao = authordict[s]
				thehtml += '<span class="au' + selectionorexclusion + '" id="searchselection_0' + str(
					selcount) + '" listval="' + \
				           str(localval) + '">' + ao.akaname + '</span><br />\n'
		
		# [f] works
		if len(session['wk' + selectionorexclusion]) == 0 and selectionorexclusion == 'exclusions' and session[
			'spuria'] == 'N':
			thehtml += '<span class="picklabel">Works</span><br />'
			thehtml += '[All non-selected spurious works]<br />'
		
		if len(session['wk' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Works</span><br />'
			if selectionorexclusion == 'exclusions' and session['spuria'] == 'N':
				thehtml += '[Non-selected spurious works]<br />'
			localval = -1
			for s in session['wk' + selectionorexclusion]:
				selcount += 1
				localval += 1
				uid = s[:6]
				ao = authordict[uid]
				wk = workdict[s]
				thehtml += '<span class="wk' + selectionorexclusion + '" id="searchselection_0' + str(
					selcount) + '" listval="' \
				           + str(localval) + '">' + ao.akaname + ', <span class="pickedwork">' + wk.title + '</span></span><br />'
		
		# [g] passages
		if len(session['psg' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Passages</span><br />'
			localval = -1
			for s in session['psg' + selectionorexclusion]:
				selcount += 1
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
				loc = citationfunctions.prolixlocus(wk, citationtuple)
				thehtml += '<span class="psg' + selectionorexclusion + '" id="searchselection_0' + str(
					selcount) + '" listval="' \
				           + str(localval) + '">' + ao.shortname + ', <span class="pickedwork">' + wk.title + \
				           '</span>&nbsp;<span class="pickedsubsection">' + loc + '</span></span><br />'
		
		returndict[selectionorexclusion] = thehtml
	
	returndict['numberofselections'] = selcount
	
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

	corpora = ('lt', 'gr', 'dp', 'in', 'ch')
	
	active = corpusselectionsaspseudobinarystring()

	toactivate = []
	position = -1

	for a in active:
		# example: 11001 = lt + gr - in - dp + ch
		position += 1
		if a == '1':
			toactivate.append(corpora[position])

	d = {}

	for a in toactivate:
		d.update(listmapper[a][criterion])

	return d


def returnactivedbs():
	"""

	what dbs are currently active?
	return a list of keys to a target dict

	:return:
	"""

	keys = []
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



