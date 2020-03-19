# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from flask import session

from server import hipparchia
from server.commandlineoptions import getcommandlineargs
from server.listsandsession.checksession import corpusselectionsaspseudobinarystring
from server.semanticvectors.vectorhelpers import vectordefaults, vectorranges
from server.startup import authorgenresdict, authorlocationdict, workgenresdict, workprovenancedict


def modifysessionvariable(parameter, value):
	"""

	set session variables after checking them for validity

	:param parameter:
	:param value:
	:return:
	"""

	# y/n ==> t/f
	if value == 'yes':
		value = True
	if value == 'no':
		value = False

	availableoptions = list()
	blocakabledebugoptions = ['debughtml', 'debuglex', 'debugparse', 'debugdb', 'indexskipsknownwords', 'searchinsidemarkup']

	commandlineargs = getcommandlineargs()

	if hipparchia.config['ALLOWUSERTOSETDEBUGMODES'] or commandlineargs.enabledebugui:
		availableoptions.extend(blocakabledebugoptions)

	trueorfalse = [
		'authorssummary',
		'bracketangled',
		'bracketcurly',
		'bracketround',
		'bracketsquare',
		'christiancorpus',
		'collapseattic',
		'cosdistbylineorword',
		'cosdistbysentence',
		'debugdb',
		'debughtml',
		'debuglex',
		'debugparse',
		'greekcorpus',
		'headwordindexing',
		'incerta',
		'indexbyfrequency',
		'indexskipsknownwords',
		'inscriptioncorpus',
		'latincorpus',
		'morphdialects',
		'morphduals',
		'morphemptyrows',
		'morphimper',
		'morphinfin',
		'morphfinite',
		'morphpcpls',
		'morphtables',
		'nearestneighborsquery',
		'onehit',
		'papyruscorpus',
		'principleparts',
		'quotesummary',
		'rawinputstyle',
		'searchinsidemarkup',
		'semanticvectorquery',
		'sensesummary',
		'sentencesimilarity',
		'showwordcounts',
		'simpletextoutput',
		'spuria',
		'suppresscolors',
		'topicmodel',
		'varia',
		'zaplunates',
		'zapvees',
	]

	vectoroptions = [
		'ldacomponents',
		'ldaiterations',
		'ldamaxfeatures',
		'ldamaxfreq',
		'ldaminfreq',
		'ldamustbelongerthan'
		'vcutlem',
		'vcutloc',
		'vcutneighb',
		'vdim',
		'vdsamp',
		'viterat',
		'vminpres',
		'vnncap',
		'vsentperdoc',
		'vwindow'
	]

	miscoptions = [
		'browsercontext',
		'earliestdate',
		'fontchoice',
		'latestdate',
		'linesofcontext',
		'maxresults',
		'nearornot',
		'proximity',
		'searchscope',
		'sortorder',
		'tensorflowgraph',
		'baggingmethod'
		]

	baggingmethods = [
		'alternates',
		'flat',
		'winnertakesall',
		'unlemmatized'
	]

	for o in [miscoptions, trueorfalse]:
		availableoptions.extend(o)

	# special case because we are dealing with collections of numbers
	if parameter in vectoroptions:
		validatevectorvalue(parameter, value)
		return

	# first set; then check to see if you need to reset an invalid value
	if parameter in availableoptions:
		session[parameter] = value
	else:
		pass

	if session['baggingmethod'] not in baggingmethods:
		# session['baggingmethod'] = 'flat'
		session['baggingmethod'] = hipparchia.config['DEFAULTBAGGINGMETHOD']

	# drop all selections/exclusions from any corpus that you just disabled
	cc = ['greekcorpus', 'latincorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus']
	if parameter in cc and not session[parameter]:
		corpora = {'greekcorpus': 'gr', 'latincorpus': 'lt', 'inscriptioncorpus': 'in', 'papyruscorpus': 'dp', 'christiancorpus': 'ch'}
		lists = ['auselections', 'psgselections', 'wkselections', 'auexclusions', 'psgexclusions', 'wkexclusions']
		for l in lists:
			session[l] = [item for item in session[l] if not re.search(r'^' + corpora[parameter], item)]

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

	if parameter in trueorfalse:
		if session[parameter] not in [True, False]:
			session[parameter] = False

	# A implies B
	if session['indexskipsknownwords']:
		session['headwordindexing'] = True

	# only one of these can be active at one time
	exclusive = {'cosdistbysentence', 'cosdistbylineorword', 'semanticvectorquery', 'nearestneighborsquery', 'tensorflowgraph', 'sentencesimilarity', 'topicmodel', 'analogyfinder'}

	for e in exclusive:
		if parameter == e and value:
			others = exclusive - {e}
			for o in others:
				session[o] = False

	if session['nearornot'] not in ['near', 'notnear']:
		session['nearornot'] = 'near'

	try:
		int(session['maxresults'])
	except ValueError:
		session['maxresults'] = '200'

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

	if session['searchscope'] not in ['lines', 'words']:
		session['searchscope'] = 'lines'

	if int(session['browsercontext']) < 5 or int(session['browsercontext']) > 100:
		session['browsercontext'] = '20'

	if hipparchia.config['ENBALEFONTPICKER'] and session['fontchoice'] in hipparchia.config['FONTPICKERLIST']:
		# print('chose', session['fontchoice'])
		pass
	else:
		session['fontchoice'] = hipparchia.config['HOSTEDFONTFAMILY']

	# print('"{v}" caused "{p}" to become "{q}"'.format(v=value, p=parameter, q=session[parameter]))

	session.modified = True

	return


def validatevectorvalue(parameter, value):
	"""

	make sure a vector setting makes sense

	vectorranges & vectordefaults are imported from vectorhelpers.py

	:param parameter:
	:param value:
	:return:
	"""

	try:
		value = int(value)
	except ValueError:
		value = vectordefaults[parameter]

	if value not in vectorranges[parameter]:
		value = vectordefaults[parameter]

	session[parameter] = value

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


def parsejscookie(cookiestring: str) -> dict:
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

	selectiondictionary = dict()
	for sel in selectioncategories:
		try:
			selectiondictionary[sel] = re.search(r'%22' + sel + r'%22:\[(.*?)\]', cookiestring).group(1)
		except AttributeError:
			# AttributeError: 'NoneType' object has no attribute 'group'
			selectiondictionary[sel] = str()

	# found; but mangled entries still:
	# {'agnselections': '%22Alchemistae%22%2C%22Biographi%22', 'wkselections': '%22gr1908w003%22%2C%22gr2612w001%22', 'psgselections': '', 'auselections': '%22gr0116%22%2C%22gr0199%22', 'wkgnselections': '%22Caten.%22%2C%22Doxogr.%22'}
	
	for sel in selectiondictionary:
		selectiondictionary[sel] = re.sub(r'%20', ' ', selectiondictionary[sel])
		selectiondictionary[sel] = re.sub(r'%22', '', selectiondictionary[sel])
		selectiondictionary[sel] = selectiondictionary[sel].strip()
		selectiondictionary[sel] = selectiondictionary[sel].split('%2C')
	
	nonselections = cookiestring
	for sel in selectioncategories:
		try:
			nonselections = re.sub(re.escape(re.search(r'%22' + sel + r'%22:\[(.*?)\]', nonselections).group(0)), '', nonselections)
		except AttributeError:
			# AttributeError: 'NoneType' object has no attribute 'group'
			nonselections = str()
			
	nonselections = re.sub(r'%22', '', nonselections)
	allotheroptions = nonselections.split('%2C')
	allotheroptions[:] = [x for x in allotheroptions if x != '']
	
	optiondict = dict()
	for o in allotheroptions:
		halves = o.split(':')
		if halves[0] != 'selections':
			optiondict[halves[0]] = halves[1]
		else:
			pass
	
	optiondict.update(selectiondictionary)
	
	return optiondict


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


def reducetosessionselections(listmapper: dict, criterion: str) -> dict:
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

	d = dict()

	# print('active corpora',toactivate)

	for a in toactivate:
		d.update(listmapper[a][criterion])

	return d


def returnactivedbs(thesession=None) -> List[str]:
	"""

	what dbs are currently active?
	return a list of keys to a target dict

	:return:
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	activedbs = list()

	if thesession['latincorpus']:
		activedbs.append('lt')
	if thesession['greekcorpus']:
		activedbs.append('gr')
	if thesession['inscriptioncorpus']:
		activedbs.append('in')
	if thesession['papyruscorpus']:
		activedbs.append('dp')
	if thesession['christiancorpus']:
		activedbs.append('ch')

	return activedbs


def findactivebrackethighlighting(thesession=None) -> List[str]:
	"""

	what kinds of brackets are we highlighting

	:return:
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session
		
	brackets = list()

	if thesession['bracketsquare']:
		brackets.append('square')
	if thesession['bracketround']:
		brackets.append('round')
	if thesession['bracketangled']:
		brackets.append('angled')
	if thesession['bracketcurly']:
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


def returnactivelist(selectiondict: dict) -> List[str]:
	"""

	what author categories, etc can you pick at the moment?

	selectiondict is something like authorgenresdict or workgenresdict

	:param selectiondict:
	:return:
	"""

	activedbs = returnactivedbs()

	activelist = list()
	for db in activedbs:
		activelist += selectiondict[db]

	activelist = list(set(activelist))

	return activelist
