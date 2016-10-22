# -*- coding: utf-8 -*-

import re

from flask import session

from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject, makeablankline
from server.dbsupport.citationfunctions import locusintocitation
from server.formatting_helper_functions import formatpublicationinfo


def cleansearchterm(seeking):
	"""
	turn sigma into antisigma, etc
	:param searchterm:
	:return:
	"""
	
	seeking = re.sub('σ|ς', 'ϲ', seeking)
	seeking = re.sub('v', 'u', seeking)
	
	return seeking


def highlightsearchterm(lineobject,searchterm, spanname):

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
	for c in searchterm:
		try:
			c = equivalents[c]
		except:
			pass
		accentedsearch += c
	accentedsearch = '('+accentedsearch+')'
	find = re.search(accentedsearch,line)
	try:
		newline = line[0:find.start()]+'<span class="'+spanname+'">'+find.group()+'</span>'+line[find.end():]
	except:
		# the find was almost certainly a hyphenated last word: 'pro-' instead of 'profuit'
		hyph = lineobject.hyphenated['accented']
		find = re.search(accentedsearch, hyph)
		try:
			newline = line + '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(&nbsp;match:&nbsp;'+hyph[0:find.start()]+'<span class="'+spanname+'">'+find.group()+'</span>'+hyph[find.end():]+'&nbsp;)'
		except:
			pass
			# print('nofind',accentedsearch, line, lineobject.lastword('contents'))

	return newline


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
		lineobject.accented = '<span class="highlight">'+lineobject.accented+'</span>'
		
	if proximate != '' and searchtype == 'proximity':
		# negative proximity ('not near') does not need anything special here: you simply never meet the condition
		if re.search(cleansearchterm(proximate),lineobject.accented) is not None or re.search(cleansearchterm(proximate),lineobject.stripped) is not None:
			lineobject.accented = highlightsearchterm(lineobject, proximate, 'proximate')
	
	formatteddict['line'] = lineobject.accented
	formatteddict['locus'] = lineobject.locustuple()

	return formatteddict


def lookoutsideoftheline(linenumber, numberofextrawords, workdbname, cursor):
	"""
	grab a line and add the N words at the tail and head of the previous and next lines
	 this will let you search for phrases that fall along a line break "και δη | και"
	:param linenumber:
	:param numberofextrawords:
	:param workdbname:
	:param cursor:
	:return:
	"""
	if '_AT_' in workdbname:
		workdbname = workdbname[0:10]

	query = 'SELECT * FROM ' + workdbname + ' WHERE index >= %s AND index <= %s'
	data = (linenumber-1, linenumber+1)
	cursor.execute(query, data)
	results = cursor.fetchall()
	lines = []
	for r in results:
		lines.append(dblineintolineobject(workdbname, r))

	# will get key errors if there is no linenumber+/-1
	if len(lines) == 2:
		if lines[0].index == linenumber:
			lines = [makeablankline(workdbname, linenumber-1)] + lines
		else:
			lines.append(makeablankline(workdbname, linenumber+1))
	if len(lines) == 1:
		lines = [makeablankline(workdbname, linenumber-1)] + lines
		lines.append(makeablankline(workdbname, linenumber+1))
	
	ldict = {}
	for line in lines:
		ldict[line.index] = line
	
	text = []
	for line in lines:
		if session['accentsmatter'] == 'Y':
			wordsinline = line.wordlist('accented')
		else:
			wordsinline = line.wordlist('stripped')
		
		if line.index == linenumber-1:
			text = wordsinline[(numberofextrawords * -1):]
		elif line.index == linenumber:
			# actually, null should be '', but is somehow coming back as something more than that
			text += wordsinline
		elif line.index == linenumber+1:
			if ldict[linenumber].hashyphenated == True:
				wordsinline = wordsinline[1:]
			text += wordsinline[:numberofextrawords]
			
	aggregate = ' '.join(text)
	aggregate = re.sub(r'\s\s',r' ', aggregate)
	aggregate = ' ' + aggregate + ' '
	
	return aggregate


def aggregatelines(firstline, lastline, cursor, workdbname):
	"""
	build searchable clumps of words spread over various lines
	:param firstline:
	:param lastline:
	:param cursor:
	:param authorobject:
	:param worknumber:
	:return:
	"""

	aggregate = ''

	query = 'SELECT * FROM ' + workdbname + ' WHERE index >= %s AND index <= %s'
	data = (firstline, lastline)
	cursor.execute(query, data)
	lines = cursor.fetchall()

	previous = makeablankline(workdbname, firstline-1)
	lineobjects = []
	for dbline in lines:
		lineobjects.append(dblineintolineobject(workdbname, dbline))

	if session['accentsmatter'] == 'Y':
		acc = 'accented'
	else:
		acc = 'stripped'
		
	for line in lineobjects:
		if previous.hyphenated[acc] == '' and line.hyphenated[acc] == '':
			if session['accentsmatter'] == 'Y':
				wds = line.unformattedline() + ' '
			else:
				wds = line.stripped
		elif previous.hyphenated[acc] != '' and line.hyphenated[acc] == '':
			wds = line.allbutfirstword(acc) + ' '
		elif previous.hyphenated[acc] == '' and line.hyphenated[acc] != '':
			wds = line.allbutlastword(acc) + ' ' + line.hyphenated[acc]
		else:
			wds = line.allbutfirstandlastword(acc) + ' ' + line.hyphenated[acc]
		aggregate += wds
		previous = line
		
	aggregate = re.sub(r'\s\s', r' ', aggregate)
	
	return aggregate


def aoprunebydate(authorandworklist, authorobjectdict):
	"""
	send me a list of authorsandworks and i will trim it via the session date limit variables
	
	:param authorandworklist:
	:param authorobjectdict:
	:return:
	"""
	trimmedlist = []
	
	if session['corpora']  == 'G' and (session['earliestdate'] != '-850' or session['latestdate'] != '1500'):
		min = int(session['earliestdate'])
		max = int(session['latestdate'])
		if min > max:
			min = max
			session['earliestdate'] = session['latestdate']
	
		for aw in authorandworklist:
			aid = aw[0:6]
			if authorobjectdict[aid].earlier(min) or authorobjectdict[aid].later(max):
				pass
				# print('passing',aw ,authorobjectdict[aid].floruit)
			else:
				trimmedlist.append(aw)
				# print('append', aw, authorobjectdict[aid].floruit)
	else:
		trimmedlist = authorandworklist

	return trimmedlist


def aoremovespuria(authorandworklist, worksdict):
	"""
	at the moment pretty crude: just look for [Sp.] or [sp.] at the end of a title
	toss it from the list if you find it
	:param authorandworklist:
	:param cursor:
	:return:
	"""
	trimmedlist = []
	
	sp = re.compile(r'\[(S|s)p\.\]')
	
	for aw in authorandworklist:
		wk = re.sub(r'x',r'w',aw[0:10])
		title = worksdict[wk].title
		try:
			if re.search(sp,title) is not None:
				for w in session['wkselections']:
					if w in aw:
						trimmedlist.append(aw)
				for w in session['psgselections']:
					if w in aw:
						trimmedlist.append(aw)
			else:
				trimmedlist.append(aw)
		except:
			trimmedlist.append(aw)
	
	return trimmedlist


def formattedcittationincontext(lineobject, workobject, authorobject, linesofcontext, searchterm, proximate, searchtype,
                                cursor):
	"""
	take a hit
		turn it into a focus line
		turround it by some context
	:param line:
	:param workdbname:
	:param authorobject:
	:param linesofcontext:
	:param searchterm:
	:param cursor:
	:return:
	"""
	
	citationincontext = []
	highlightline = lineobject.index
	citation = locusintocitation(workobject, lineobject.locustuple())
	# this next bit of info tags the find; 'newfind' + 'url' is turned into JS in the search.html '<script>' loop; this enables click-to-browse
	# similarly the for-result-in-found loop of search.html generates the clickable elements: <browser id="{{ context['url'] }}">
	citationincontext.append({'newfind': 1, 'author': authorobject.shortname,
	                          'work': workobject.title, 'citation': citation, 'url': (lineobject.universalid)})
	environs = simplecontextgrabber(workobject, highlightline, linesofcontext, cursor)
	
	for found in environs:
		found = dblineintolineobject(lineobject.wkuinversalid, found)
		if found.index == highlightline:
			found = lineobjectresultformatter(found, searchterm, proximate, searchtype, True)
		else:
			found = lineobjectresultformatter(found, searchterm, proximate, searchtype, False)
		citationincontext.append(found)
	
	return citationincontext


def aoformatauthinfo(authorobject):
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
	
	if authorobject.language == 'G':
		try:
			if float(authorobject.floruit) == 1500:
				fl = 'approx date is unknown (search for 1500 C.E.)'
			elif float(authorobject.floruit) > 0:
				fl = 'assigned to approx date: ' + str(authorobject.floruit) + ' C.E.'
			elif float(authorobject.floruit) < 0:
				fl = 'assigned to approx date: ' + str(authorobject.floruit)[1:] + ' B.C.E.'
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
	
	workinfo = n+t+g+c+'<br />'+p+'<br />'
	
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




