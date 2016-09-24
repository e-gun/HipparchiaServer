# -*- coding: utf-8 -*-
import re
from flask import session
from server import formatting_helper_functions
from server.dbsupport import dbfunctions, citationfunctions

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
		'corpora']

	# note that 'selections' remains unhandled

	if param in availableoptions:
		session[param] = val

	if session['corpora'] not in ['B', 'L', 'G']:
		session['corpora'] = 'B'
		
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
	if session['sortorder'] not in ['shortname','genres', 'floruit', 'location']:
		session['sortorder'] = 'shortname'
	if session['searchscope'] not in ['L','W']:
		session['searchscope'] = 'L'
	if int(session['browsercontext']) < 5 or int(session['browsercontext']) > 100:
		session['browsercontext'] = '20'


	# print('set',param,'to',session[param])
	session.modified = True

	return


def modifysessionselections(cookiedict, cursor):
	"""
	set session selections after checking them for validity
	i'm not sure how many people will take the trouble to build evil cookies, but...
	:param cookiedict:
	:return:
	"""
	
	# selectioncategories = ['auselections', 'wkselections', 'agnselections', 'wkgnselections', 'psgselections']
	
	validauth = re.compile(r'(lt|gr)\d\d\d\d')
	aus = cookiedict['auselections']
	for item in aus:
		if re.search(validauth,item) is None:
			aus.remove(item)
	session['auselections'] = aus
	
	validwk = re.compile(r'(lt|gr)\d\d\d\dw\d\d\d')
	wks = cookiedict['wkselections']
	for item in wks:
		if re.search(validwk,item) is None:
			wks.remove(item)
	session['wkselections'] = wks
	
	validpsg = re.compile(r'(lt|gr)\d\d\d\dw\d\d\d_AT_')
	badchars = re.compile(r'[!@#$|%()*\'\"]')
	psg = cookiedict['psgselections']
	for item in psg:
		if (re.search(validpsg, item) is None) or re.search(badchars, item):
			psg.remove(item)
	session['psgselections'] = psg
	
	try:
		# but how could we possibly get here without having this on hand...
		session['genres']
		session['workgenres']
	except:
		session['genres'] = setsessionvarviadb('genres', 'authors', cursor)
		session['workgenres'] = setsessionvarviadb('workgenre', 'works', cursor)
	
	ags = cookiedict['agnselections']
	for item in ags:
		if item not in session['genres']:
			ags.remove(item)
	session['agnselections'] = ags
	
	wgs = cookiedict['wkgnselections']
	for item in wgs:
		if item not in session['workgenres']:
			wgs.remove(item)
	session['wkgnselections'] = wgs
	
	session.modified = True
	return


def parsejscookie(cookiestring):
	"""
	turn the string into a dict
	a shame this has to be written
	
	example cookies:
		{%22searchsyntax%22:%22R%22%2C%22linesofcontext%22:6%2C%22agnselections%22:[%22Alchemistae%22%2C%22Biographi%22]%2C%22corpora%22:%22G%22%2C%22proximity%22:%221%22%2C%22sortorder%22:%22shortname%22%2C%22maxresults%22:%22250%22%2C%22auselections%22:[%22gr0116%22%2C%22gr0199%22]%2C%22xmission%22:%22Any%22%2C%22browsercontext%22:%2220%22%2C%22accentsmatter%22:%22N%22%2C%22latestdate%22:%221500%22%2C%22psgselections%22:[]%2C%22searchscope%22:%22L%22%2C%22wkselections%22:[%22gr1908w003%22%2C%22gr2612w001%22]%2C%22authenticity%22:%22Any%22%2C%22earliestdate%22:%22-850%22%2C%22wkgnselections%22:[%22Caten.%22%2C%22Doxogr.%22]}	:return:
	"""
	cookiestring = cookiestring[1:-1]

	selectioncategories = ['auselections', 'wkselections', 'agnselections', 'wkgnselections', 'psgselections', 'auexclusions', 'wkexclusions', 'agnexclusions', 'wgnexclusions', 'psgexclusions']
	selectiondictionary = {}
	for sel in selectioncategories:
		selectiondictionary[sel] = re.search(r'%22' + sel + r'%22:\[(.*?)\]', cookiestring).group(1)
	
	# found; but mangled entries still:
	# {'agnselections': '%22Alchemistae%22%2C%22Biographi%22', 'wkselections': '%22gr1908w003%22%2C%22gr2612w001%22', 'psgselections': '', 'auselections': '%22gr0116%22%2C%22gr0199%22', 'wkgnselections': '%22Caten.%22%2C%22Doxogr.%22'}
	
	for sel in selectiondictionary:
		selectiondictionary[sel] = re.sub(r'%20', '', selectiondictionary[sel])
		selectiondictionary[sel] = re.sub(r'%22', '', selectiondictionary[sel])
		selectiondictionary[sel] = selectiondictionary[sel].split('%2C')
	
	nonselections = cookiestring
	for sel in selectioncategories:
		nonselections = re.sub(re.escape(re.search(r'%22' + sel + r'%22:\[(.*?)\]', nonselections).group(0)), '', nonselections)
	
	allotheroptions = []
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


def setsessionvarviadb(column, table, cursor):
	"""
	generate a list of values to feed to a session variable
	:param column:
	:param cursor:
	:return:
	"""
	
	query = 'SELECT '+column+' FROM '+table+' WHERE '+column+' != %s'
	data = ('',)
	cursor.execute(query, data)
	results = cursor.fetchall()
	tuples = set(results)
	found = []
	for f in tuples:
		found.append(f[0])
	sv = []
	for s in found:
		ss = s.split(',')
		for item in ss:
			sv.append(item)
	sv = formatting_helper_functions.tidyuplist(sv)
	
	return sv


def sessionvariables(cursor):

	try:
		session['corpora']
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
		session['corpora'] = 'G'
		session['accentsmatter'] = 'N'
		session['proximity'] = '1'
		session['nearornot'] = 'T'
		session['searchscope'] = 'L'
		session['linesofcontext'] = 6
		session['browsercontext'] = '20'
		session['maxresults'] = '250'
		session['sortorder'] = 'name'
		session['earliestdate'] = '-850'
		session['latestdate'] = '1500'
		session['xmission'] = 'Any'
		session['spuria'] = 'Y'

		# if you try to store all of the authors in the session you will have problems: the cookie gets too big
		session['genres'] = setsessionvarviadb('genres', 'authors', cursor)
		session['workgenres'] = setsessionvarviadb('workgenre', 'works', cursor)

	return

def sessionselectionsashtml(cursor):
	"""
	assemble the html to be fed into the json that goes to the js that fills #selectionstable
	three chunks: time; selections; exclusions
	:param cursor:
	:return:
	"""

	selectioninfo = {}
	
	selectioninfo['timeexclusions'] = sessiontimeexclusionsinfo()
	sxhtml = sessionselectionsinfo(cursor)
	
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
	:param cursor:
	:return:
	"""
	timerestrictions = ''
	
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


def sessionselectionsinfo(cursor):
	"""
	build the selections html either for a or b:
		#selectionstable + #selectioninfocell
		#selectionstable + #exclusioninfocell
	there are five headings to populate
		[a] author classes
		[b] work genres
		[c] author selections
		[d] work selections
		[e] passage selections
		
	id numbers need to be attached to the selections so that they can be clicked-and-dragged to the trash by id
	this needs to be a sequential list and so we do both selections and exclusions in one go to keep one unified 'selcount'
	the selcount is used to generate a collection of jQuery .droppable()s
	
	:param cursor:
	:return: dictionary of html: {'selections':selhtml, 'exclusions':exclhtml, 'numberofselections': selcount}
	"""
	
	returndict = {}
	selcount = -1
	
	sessionsearchlist = session['auselections'] + session['agnselections'] + session['wkgnselections'] + \
	                    session['psgselections'] + session['wkselections']
	
	for selectionorexclusion in ['selections', 'exclusions']:
		thehtml = ''
		
		# if there are no explicit selections, then
		if len(sessionsearchlist) == 0 and selectionorexclusion == 'selections':
			thehtml += '<span class="picklabel">Authors</span><br />'
			thehtml += '[Full corpus less exclusions]<br />\n'
		
		if selectionorexclusion == 'exclusions' and len(sessionsearchlist) == 0 and session['spuria'] == 'Y' and len(session['wkgnexclusions']) == 0 and len(session['agnexclusions']) == 0:
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
		
		# [c] authors
		if len(session['au' + selectionorexclusion]) > 0:
			thehtml += '<span class="picklabel">Authors</span><br />'
			localval = -1
			for s in session['au' + selectionorexclusion]:
				selcount += 1
				localval += 1
				query = 'SELECT akaname from authors WHERE universalid = %s'
				data = (s,)
				cursor.execute(query, data)
				result = cursor.fetchone()
				thehtml += '<span class="au' + selectionorexclusion + '" id="searchselection_0' + str(selcount) + '" listval="' + \
				           str(localval) + '">' + result[0] + '</span><br />\n'
	
		# [d] works
		if len(session['wk' + selectionorexclusion]) == 0 and selectionorexclusion == 'exclusions' and session['spuria'] == 'N':
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
				ao = dbfunctions.dbauthorandworkmaker(uid, cursor)
				query = 'SELECT title from works WHERE universalid = %s'
				data = (s,)
				cursor.execute(query, data)
				result = cursor.fetchone()
				thehtml += '<span class="wk'+selectionorexclusion+'" id="searchselection_0' + str(selcount)+'" listval="' \
					+str(localval)+'">'+ ao.akaname + ', <span class="pickedwork">' + result[0] + '</span></span><br />'
		
		# [e] passages
		if len(session['psg'+selectionorexclusion]) > 0:
			# none of this should be on right now
			thehtml += '<span class="picklabel">Passages</span><br />'
			localval = -1
			for s in session['psg'+selectionorexclusion]:
				selcount += 1
				localval += 1
				locus = s[14:].split('|')
				# print('l', s, s[:6], s[7:10], s[14:], locus)
				locus.reverse()
				citationtuple = tuple(locus)
				uid = s[:6]
				ao = dbfunctions.dbauthorandworkmaker(uid, cursor)
				for w in ao.listofworks:
					if w.universalid == s[0:10]:
						wk = w
				loc = citationfunctions.locusintosearchitem(wk, citationtuple)
				thehtml += '<span class="psg'+selectionorexclusion+'" id="searchselection_0' + str(selcount)+'" listval="' \
				           +str(localval)+'">'+ ao.shortname + ', <span class="pickedwork">' + wk.title + \
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

