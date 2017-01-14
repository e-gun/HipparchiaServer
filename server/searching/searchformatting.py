# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Process, Manager

from flask import session

from server import hipparchia
from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject, setconnection
from server.formatting_helper_functions import formatpublicationinfo
from server.hipparchiaclasses import FormattedSearchResult


def cleansearchterm(seeking):
	"""
	turn sigma into antisigma, etc
	:param searchterm:
	:return:
	"""
	
	seeking = re.sub('σ|ς', 'ϲ', seeking)
	if session['accentsmatter'] == 'no':
		seeking = re.sub('v', 'u', seeking)

	# possible, but not esp. desirable:
	# seeking = re.sub('VvUu', '(u|v|U|v)', seeking)

	return seeking


def highlightsearchterm(lineobject,searchterm, spanname):
	"""
	html markup for the search term in the line
	in order to highlight a polytonic word that you found via a unaccented search you need to convert:
		ποταμον
	into:
		((π|Π)(ο|ὀ|ὁ|ὂ|ὃ|ὄ|ὅ|ό|ὸ|Ο|Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ)(τ|Τ)(α|ἀ|ἁ|ἂ|ἃ|ἄ|ἅ|ἆ|ἇ|ᾀ|ᾁ|ᾂ|ᾃ|ᾄ|ᾅ|ᾆ|ᾇ|ᾲ|ᾳ|ᾴ|ᾶ|ᾷ|ᾰ|ᾱ|ὰ|ά|ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ|Α)(μ|Μ)ό(ν|Ν))
	
	:param lineobject:
	:param searchterm:
	:param spanname:
	:return:
	"""

	line = lineobject.accented

	equivalents = {
		'α': '(α|ἀ|ἁ|ἂ|ἃ|ἄ|ἅ|ἆ|ἇ|ᾀ|ᾁ|ᾂ|ᾃ|ᾄ|ᾅ|ᾆ|ᾇ|ᾲ|ᾳ|ᾴ|ᾶ|ᾷ|ᾰ|ᾱ|ὰ|ά|ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ|Α)',
		'β': '(β|Β)',
		'ψ': '(ψ|Ψ)',
		'δ': '(δ|Δ)',
		'ε': '(ε|ἐ|ἑ|ἒ|ἓ|ἔ|ἕ|ὲ|έ|Ε|Ἐ|Ἑ|Ἒ|Ἓ|Ἔ|Ἕ)',
		'φ': '(φ|Φ)',
		'γ': '(γ|Γ)',
		'η': '(η|ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|ή|ἡ|ἦ|Η|ᾘ|ᾙ|ᾚ|ᾛ|ᾜ|ᾝ|ᾞ|ᾟ|Ἠ|Ἡ|Ἢ|Ἣ|Ἤ|Ἥ|Ἦ|Ἧ)',
		'ι': '(ι|ἰ|ἱ|ἲ|ἳ|ἴ|ἵ|ἶ|ἷ|ὶ|ί|ῐ|ῑ|ῒ|ΐ|ῖ|ῗ|ΐ|Ἰ|Ἱ|Ἲ|Ἳ|Ἴ|Ἵ|Ἶ|Ἷ|Ι)',
		'ξ': '(ξ|Ξ)',
		'κ': '(κ|Κ)',
		'λ': '(λ|Λ)',
		'μ': '(μ|Μ)',
		'ν': '(ν|Ν)',
		'ο': '(ο|ὀ|ὁ|ὂ|ὃ|ὄ|ὅ|ό|ὸ|Ο|Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ)',
		'π': '(π|Π)',
		'ρ': '(ρ|Ρ|ῥ|Ῥ)',
		'ϲ': '(ϲ|Σ)',
		'σ': '(ϲ|Σ)',
		'ς': '(ϲ|Σ)',
		'τ': '(τ|Τ)',
		'υ': '(υ|ὐ|ὑ|ὒ|ὓ|ὔ|ὕ|ὖ|ὗ|ϋ|ῠ|ῡ|ῢ|ΰ|ῦ|ῧ|ύ|ὺ|Ὑ|Ὓ|Ὕ|Ὗ|Υ)',
		'ω': '(ω|ὠ|ὡ|ὢ|ὣ|ὤ|ὥ|ὦ|ὧ|ᾠ|ᾡ|ᾢ|ᾣ|ᾤ|ᾥ|ᾦ|ᾧ|ῲ|ῳ|ῴ|ῶ|ῷ|ώ|ὼ|Ω|ᾨ|ᾩ|ᾪ|ᾫ|ᾬ|ᾭ|ᾮ|ᾯ|Ὠ|Ὡ|Ὢ|Ὣ|Ὤ|Ὥ|Ὦ|Ὧ|Ω)',
		'χ': '(χ|Χ)',
		'θ': '(θ|Θ)',
		'ζ': '(ζ|Ζ)',
		'a': '(a|á|ä)',
		'e': '(e|é|ë)',
		'i': '(i|í|ï)',
		'o': '(o|ó|ö)',
		'u': '(u|ü|v)',
		'v': '(u|ü|v)'
	}

	newline = line

	line = newline
	accentedsearch = ''
	searchterm = re.sub(r'(^\s|\s$)', '', searchterm)
	for c in searchterm:
		try:
			c = equivalents[c]
		except:
			pass
		accentedsearch += c
	#accentedsearch = '(^|)('+accentedsearch+')($|)'
	accentedsearch = '(' + accentedsearch + ')'
	
	find = re.search(accentedsearch,line)
	try:
		newline = line[0:find.start()]+'<span class="'+spanname+'">'+find.group()+'</span>'+line[find.end():]
	except:
		# the find was almost certainly a hyphenated last word: 'pro-' instead of 'profuit'
		hyph = lineobject.hyphenated
		find = re.search(accentedsearch, hyph)
		try:
			newline = line + '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(&nbsp;match:&nbsp;'+hyph[0:find.start()]+'<span class="'+spanname+'">'+find.group()+'</span>'+hyph[find.end():]+'&nbsp;)'
		except:
			pass
			# print('nofind',accentedsearch, line, lineobject.lastword('contents'))

	return newline


def lineobjectresulthighlighter(lineobject, searchterm, proximate, searchtype, highlight):
	"""
	turn a lineobject into a pretty result
	reformat a line object to highlight what needs highlighting

	:param lineobject:
	:param searchterm:
	:param highlight:
	:return:
	"""

	if highlight is True:
		lineobject.accented = highlightsearchterm(lineobject, searchterm, 'match')
		lineobject.accented = '<span class="highlight">'+lineobject.accented+'</span>'
		
	if proximate != '' and searchtype == 'proximity':
		# negative proximity ('not near') does not need anything special here: you simply never meet the condition
		if re.search(cleansearchterm(proximate),lineobject.accented) is not None or re.search(cleansearchterm(proximate),lineobject.stripped) is not None:
			lineobject.accented = highlightsearchterm(lineobject, proximate, 'proximate')

	return lineobject


def aggregatelines(firstline, lastline, cursor, audbname):
	"""
	build searchable clumps of words spread over various lines

	:param firstline:
	:param lastline:
	:param cursor:
	:param workdbname:
	:return:
	"""

	# transitional until all code is 'monolithic'
	audbname = audbname[0:6]

	query = 'SELECT * FROM ' + audbname + ' WHERE index >= %s AND index <= %s'
	data = (firstline, lastline)
	cursor.execute(query, data)
	lines = cursor.fetchall()
	
	lineobjects = []
	for dbline in lines:
		lineobjects.append(dblineintolineobject(dbline))
	
	aggregate = ''
	if session['accentsmatter'] == 'yes':
		for line in lineobjects:
			aggregate += line.polytonic + ' '
	else:
		for line in lineobjects:
			aggregate += line.stripped + ' '
	
	aggregate = re.sub(r'\s\s', r' ', aggregate)
	
	return aggregate


def formatauthinfo(authorobject):
	"""
	ao data into html
	:param authorobject:
	:return:
	"""
	n = '<span class="emph">'+authorobject.shortname+'</span>'
	d = '[id: ' + authorobject.universalid[2:] + ']<br />'
	if authorobject.genres is not None and authorobject.genres != '':
		g = 'classified among: ' + authorobject.genres + '; '
	else:
		g = ''
	
	if authorobject.universalid[0:2] in ['gr', 'in', 'dp']:
		try:
			if float(authorobject.converted_date) == 2000:
				fl = '"Varia" are not assigned to a date'
			elif float(authorobject.converted_date) == 2500:
				fl = '"Incerta" are not assigned to a date'
			elif float(authorobject.converted_date) > 0:
				fl = 'assigned to approx date: ' + str(authorobject.converted_date) + ' C.E.'
				fl += ' (derived from "' + authorobject.recorded_date + '")'
			elif float(authorobject.converted_date) < 0:
				fl = 'assigned to approx date: ' + str(authorobject.converted_date)[1:] + ' B.C.E.'
				fl += ' (derived from "'+authorobject.recorded_date+'")'
		except:
			# there was no f and so no int(f)
			fl = ''
	else:
		fl = ''
	
	authinfo = n + '&nbsp;' + d + '&nbsp;' + g + fl
	
	return authinfo
	

def woformatworkinfo(workobject):
	"""
	dbdata into html
	send me: universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""
	
	p = formatpublicationinfo(workobject.publication_info)
	
	n = '('+workobject.universalid[-3:]+')&nbsp;'
	t = '<span class="title">'+workobject.title+'</span> '
	
	if workobject.workgenre is not None:
		g = '['+workobject.workgenre+']&nbsp;'
	else:
		g = ''
	
	if workobject.wordcount is not None:
		c = '['+format(workobject.wordcount, ',d')+' wds]'
	else:
		c = ''

	try:
		dateval = int(workobject.converted_date)
	except:
		dateval = 9999

	if dateval < 1500:
		if dateval > 0:
			suffix = 'CE'
			d = '(assigned to ' + str(workobject.converted_date) + ' ' + suffix + ')'
		else:
			suffix = 'BCE'
			d = '(assigned to ' + str(workobject.converted_date[1:]) + ' ' + suffix + ')'
	else:
		d = ''

	if len(p) > 0:
		workinfo = n+t+g+c+d+'<br />'+p+'<br />'
	else:
		workinfo = n + t + g + c + d+'<br />'

	return workinfo


def formatauthorandworkinfo(authorname,workobject):
	"""
	dbdata into html
	send me: authorname + universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""
	
	a = authorname
	t = '<span class="italic">' + workobject.title + '</span> '
	
	c = workobject.wordcount
	
	if c is not None:
		c = '[' + format(c, ',d') + ' wds]'
	else:
		c = ''
		
	authorandworkinfo = a + ', '+ t + c + '<br />\n'
		
	return authorandworkinfo


def sortandunpackresults(hits):
	"""
	multiprocessor hits will unsort the sorted author and work list as the different workers get their results out of order
	these reults arrive bundled with all the hits in any given work listed after the work
	sort and unpack this into a flat result list
		{sortedawindex: (wkid, [(result1), (result2), ...])}
		2455: ('gr0715w001', [(13697, '-1', '-1', '6', '28', '1', '7', 'τινεϲ ὀδόντεϲ παραφύονται, τοὺϲ μὲν προϲπεφυκόταϲ τῷ φατνίῳ διὰ ', 'τινεϲ οδοντεϲ παραφυονται, τουϲ μεν προϲπεφυκοταϲ τω φατνιω δια ', '', ''), (13698, '-1', '-1', '6', '28', '1', '8', 'τῶν ϲμιλιωτῶν ἐκκόψωμεν, τοὺϲ δὲ μὴ προϲπεφυκόταϲ διὰ τῆϲ ὀδοντ-', 'των ϲμιλιωτων εκκοψωμεν, τουϲ δε μη προϲπεφυκοταϲ δια τηϲ οδοντ-', 'ὀδοντάγραϲ οδονταγραϲ', '')])
	:param hits:
	:return: an ordered set of tuples [(wkid1, result1), (wkid1,result2), (wkid2, result1), ...]
	"""
	
	results = []
	listpositions = sorted(hits.keys())
	
	for position in listpositions:
		found = hits[position]
		for find in found[1]:
			results.append((found[0],find))

	return results


def mpresultformatter(hitdict, authordict, workdict, seeking, proximate, searchtype, activepoll):
	"""
	if you have lots of results, they don't get formatted as fast as they could:
	single threaded is fine if all from same author, but something like 1500 hits of αξιολ will bounce you around a lot
		22s single threaded to do search + format
		12s multi-threaded to do search + format

	the hitdict is a collection of line objects where the key is the proper sort order for the results
		hitdict {0: <server.hipparchiaclasses.dbWorkLine object at 0x103dd17b8>, 1: <server.hipparchiaclasses.dbWorkLine object at 0x103dd1780>}

	returns a sorted list of FormattedSearchResult objects

	:return:
	"""

	#for h in hitdict.keys():
	#	print(h,hitdict[h].universalid, hitdict[h].accented)

	linesofcontext = int(session['linesofcontext'])
	
	activepoll.allworkis(len(hitdict))
	activepoll.remain(len(hitdict))
		
	workbundles = []
	if len(hitdict) > int(session['maxresults']):
		limit = int(session['maxresults'])
	else:
		limit = len(hitdict)
	
	criteria = {'ctx': linesofcontext, 'seek': seeking, 'prox': proximate, 'type': searchtype}
	
	for i in range(0,limit):
		lineobject = hitdict[i]
		authorobject = authordict[lineobject.wkuinversalid[0:6]]
		wid = lineobject.wkuinversalid
		workobject = workdict[wid]
		workbundles.append({'hitnumber': i+1, 'lo': lineobject, 'wo': workobject, 'ao': authorobject})

	manager = Manager()
	allfound = manager.dict()
	bundles = manager.list(workbundles)
	criteria = manager.dict(criteria)
	
	workers = hipparchia.config['WORKERS']
	
	jobs = [Process(target=formattingworkpile, args=(bundles, criteria, activepoll, allfound))
	        for i in range(workers)]
	
	for j in jobs: j.start()
	for j in jobs: j.join()

	# allfound = { 1: <server.hipparchiaclasses.FormattedSearchResult object at 0x111e73160>, 2: ... }
	keys = sorted(allfound.keys())
	finds = []
	for k in keys:
		finds.append(allfound[k])

	return finds


def formattingworkpile(bundles, criteria, activepoll, allfound):
	"""
	the work for the workers to send to formattedcittationincontext()
	
	a bundle:
		{'hitnumber': 3, 'wo': <server.hipparchiaclasses.dbOpus object at 0x1109ad240>, 'ao': <server.hipparchiaclasses.dbAuthor object at 0x1109ad0f0>, 'lo': <server.hipparchiaclasses.dbWorkLine object at 0x11099d9e8>}

	criteria:
		{'seek': 'οἵ ῥά οἱ', 'type': 'phrase', 'ctx': 4, 'prox': ''}

	:param workbundles:
	:return:
	"""
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	while len(bundles) > 0:
		try:
			bundle = bundles.pop()
		except:
			# IndexError: pop from empty list
			bundle = None

		if bundle is not None:
			citwithcontext = formattedcittationincontext(bundle['lo'], bundle['wo'], bundle['ao'], criteria['ctx'], criteria['seek'],
														 criteria['prox'], criteria['type'], curs)
			citwithcontext.hitnumber = bundle['hitnumber']
			activepoll.remain(bundle['hitnumber'])

			if bundle['hitnumber'] % 100 == 0:
				dbconnection.commit()

			if citwithcontext.formattedlines != []:
				allfound[bundle['hitnumber']] = citwithcontext

	dbconnection.commit()
	curs.close()

	return allfound


def formattedcittationincontext(lineobject, workobject, authorobject, linesofcontext, searchterm, proximate,
                                searchtype, curs):
	"""
	take a hit
		turn it into a focus line
		surround it by some context
	
	citationincontext[0]:
		{'citation': 'Book 3, line 291', 'author': 'Quintus', 'work': 'Posthomerica', 'newfind': 1, 'url': 'gr2046w001_LN_1796'}
				
	a line deeper inside citationincontext[]:
		{'line': '<span class="highlight"><span class="expanded">Περϲέοϲ</span>, <span class="match">οἵ ῥά οἱ</span> αἰὲν ἐπωμάδιοι φορέονται.</span>', 'index': 249, 'locus': ('249', '1')}
		
	:param line:
	:param workdbname:
	:param authorobject:
	:param linesofcontext:
	:param searchterm:
	:param cursor:
	:return:
	"""

	highlightline = lineobject.index
	citation = locusintocitation(workobject, lineobject.locustuple())

	citationincontext = FormattedSearchResult(-1,authorobject.shortname, workobject.title, citation, lineobject.universalid, [])
	environs = simplecontextgrabber(workobject, highlightline, linesofcontext, curs)
	
	for found in environs:
		found = dblineintolineobject(found)
		if found.index == highlightline:
			found = lineobjectresulthighlighter(found, searchterm, proximate, searchtype, True)
		else:
			found = lineobjectresulthighlighter(found, searchterm, proximate, searchtype, False)
		citationincontext.formattedlines.append(found)

	return citationincontext




# slated for removal

def oldformattingworkpile(bundles, criteria, activepoll, allfound):
	"""
	the work for the workers to send to formattedcittationincontext()

	a bundle:
		{'hitnumber': 3, 'wo': <server.hipparchiaclasses.dbOpus object at 0x1109ad240>, 'ao': <server.hipparchiaclasses.dbAuthor object at 0x1109ad0f0>, 'lo': <server.hipparchiaclasses.dbWorkLine object at 0x11099d9e8>}

	criteria:
		{'seek': 'οἵ ῥά οἱ', 'type': 'phrase', 'ctx': 4, 'prox': ''}

	:param workbundles:
	:return:
	"""

	while len(bundles) > 0:
		try:
			bundle = bundles.pop()
		except:
			# IndexError: pop from empty list
			bundle = None

		if bundle is not None:
			citwithcontext = formattedcittationincontext(bundle['lo'], bundle['wo'], bundle['ao'], criteria['ctx'],
														 criteria['seek'], criteria['prox'], criteria['type'])
			citwithcontext[0]['hitnumber'] = bundle['hitnumber']
			activepoll.remain(activepoll.getremaining() - 1)

			if citwithcontext != []:
				allfound[bundle['hitnumber']] = citwithcontext

	return allfound


def oldformattedcittationincontext(lineobject, workobject, authorobject, linesofcontext, searchterm, proximate,
								searchtype):
	"""
	take a hit
		turn it into a focus line
		surround it by some context

	citationincontext[0]:
		{'citation': 'Book 3, line 291', 'author': 'Quintus', 'work': 'Posthomerica', 'newfind': 1, 'url': 'gr2046w001_LN_1796'}

	a line deeper inside citationincontext[]:
		{'line': '<span class="highlight"><span class="expanded">Περϲέοϲ</span>, <span class="match">οἵ ῥά οἱ</span> αἰὲν ἐπωμάδιοι φορέονται.</span>', 'index': 249, 'locus': ('249', '1')}

	:param line:
	:param workdbname:
	:param authorobject:
	:param linesofcontext:
	:param searchterm:
	:param cursor:
	:return:
	"""

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	citationincontext = []
	highlightline = lineobject.index
	citation = locusintocitation(workobject, lineobject.locustuple())
	# this next bit of info tags the find; 'newfind' + 'url' is turned into JS in the search.html '<script>' loop; this enables click-to-browse
	# similarly the for-result-in-found loop of search.html generates the clickable elements: <browser id="{{ context['url'] }}">
	citationincontext.append({'newfind': 1, 'author': authorobject.shortname,
							  'work': workobject.title, 'citation': citation, 'url': (lineobject.universalid)})

	environs = simplecontextgrabber(workobject, highlightline, linesofcontext, curs)

	for found in environs:
		found = dblineintolineobject(found)
		if found.index == highlightline:
			found = lineobjectresultformatter(found, searchterm, proximate, searchtype, True)
		else:
			found = lineobjectresultformatter(found, searchterm, proximate, searchtype, False)
		citationincontext.append(found)

	dbconnection.commit()
	curs.close()
	del dbconnection

	return citationincontext


def lineobjectresultformatter(lineobject, searchterm, proximate, searchtype, highlight):
	"""
	turn a lineobject into a pretty result
		 out:
		{'index': 1728, 'locus': ('237','3'), 'line':"<span class="highlight">Κάϲτορά θ' ἱππόδαμον καὶ πὺξ <span class="match">ἀγαθὸν</span> Πολυδεύκεα </span>"}

	:param lineobject:
	:param searchterm:
	:param highlight:
	:return:
	"""

	formatteddict = {}
	formatteddict['index'] = lineobject.index

	if highlight is True:
		lineobject.accented = highlightsearchterm(lineobject, searchterm, 'match')
		lineobject.accented = '<span class="highlight">' + lineobject.accented + '</span>'

	if proximate != '' and searchtype == 'proximity':
		# negative proximity ('not near') does not need anything special here: you simply never meet the condition
		if re.search(cleansearchterm(proximate), lineobject.accented) is not None or re.search(
				cleansearchterm(proximate), lineobject.stripped) is not None:
			lineobject.accented = highlightsearchterm(lineobject, proximate, 'proximate')

	formatteddict['line'] = lineobject.accented
	formatteddict['locus'] = lineobject.locustuple()

	return formatteddict
