# -*- coding: utf-8 -*-

import re

from flask import session

from server.dbsupport.dbfunctions import dbauthorandworkmaker, simplecontextgrabber
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


def highlightsearchterm(line,searchterm):


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
		newline = line[0:find.start()]+'<span class="match">'+find.group()+'</span>'+line[find.end():-1]
	except:
		# will barf if you 'find' an empty line, etc
		# i.e., a bug in the search engine will turn into a problem here
		pass

	return newline


def resultformatter(raw, searchterm, highlight):
	# in:
	# (1728, None, '-1', '-1', '-1', '3', '237', "Κάϲτορά θ' ἱππόδαμον καὶ πὺξ ἀγαθὸν Πολυδεύκεα ", "Καϲτορα θ' ιπποδαμον και πυξ αγαθον Πολυδευκεα ", '', '')
	# out:
	# {'index': 1728, 'locus': ('237','3'), 'line':"<span class="highlight">Κάϲτορά θ' ἱππόδαμον καὶ πὺξ <span class="match">ἀγαθὸν</span> Πολυδεύκεα </span>"}
	formatteddict = {}
	formatteddict['index'] = raw[0]
	if highlight is True:
		# newline = raw[7]
		newline = highlightsearchterm(raw[7], searchterm)
		formatteddict['line'] = '<span class="highlight">'+newline+'</span>'
	else:
		formatteddict['line'] = raw[7]
	loc = []
	for i in range(6, 1, -1):
		if (raw[i] != '-1') and (raw[i] is not None):
			loc.append(raw[i])
	formatteddict['locus']=tuple(loc)

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

	if session['accentsmatter'] == 'Y':
		# setting self up for big problems because you have both accents and markup in here
		# will need to pass things through a stripper before searching
		column = 'marked_up_line'
	else:
		column = 'stripped_line'
		
	query = 'SELECT index,'+column+',hyphenated_words FROM ' + workdbname + ' WHERE index >= %s AND index <= %s'
	data = (linenumber-1, linenumber+1)
	cursor.execute(query, data)
	lines = cursor.fetchall()
	
	hyphenmemory = False
	text = []

	for line in lines:
		line = list(line)
		line[1] = re.sub(r'<.*?>','',line[1])
		line[1] = re.sub(r'\s$', '', line[1])

		if session['accentsmatter'] != 'Y':
			line[1] = re.sub(r'[^\w\s]', '', line[1])
			hyphen = line[2].split(' ')
			hyphen = hyphen[0]
		else:
			hyphen = line[2].split(' ')
			try:
				hyphen = hyphen[1]
			except:
				hyphen = ''
		wordsinline = line[1].split(' ')

		if line[0] == linenumber-1:
			if hyphen == '':
				text = wordsinline[(numberofextrawords * -1):]
			else:
				wordsinline = wordsinline[:-1] + [hyphen]
				text = wordsinline[(numberofextrawords * -1):]
		elif line[0] == linenumber:
			if hyphenmemory == True:
				wordsinline = wordsinline[1:]
			if hyphen == '':
				text += wordsinline
			else:
				text += wordsinline[:-1] + [hyphen]
				hyphenmemory = True
		elif line[0] == linenumber+1:
			if hyphenmemory == True:
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

	if '_AT_' in workdbname:
		workdbname = workdbname[0:10]

	aggregate = ''

	if session['accentsmatter'] == 'Y':
		# setting self up for big problems because you have both accents and markup in here
		# will need to pass things through a stripper before searching
		column = 'marked_up_line'
	else:
		column = 'stripped_line'

	query = 'SELECT '+column+' FROM ' + workdbname + ' WHERE index >= %s AND index <= %s'
	data = (firstline, lastline)
	cursor.execute(query, data)
	lines = cursor.fetchall()

	text = []
	if session['accentsmatter'] == 'Y':
		for line in lines:
			# note that we just killed a bunch of supplenda
			text.append(re.sub(r'<.*?>','',line[0]))
	else:
		for line in lines:
			cleaned = re.sub(r'[^\w\s]','', line[0])
			cleaned = re.sub(r'\d', '', cleaned)
			text.append(cleaned)

	for t in text:
		# dies on empty lines (even though we are not supposed to have those...
		try:
			if t[-1] == '-':
				aggregate += t[:-1]
			else:
				aggregate += t
		except:
			pass
		
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


def aoformattedcittationincontext(line, workdbname, authorobject, linesofcontext, searchterm, cursor):
	
	if '_AT_' in workdbname:
		workdbname = workdbname[0:10]
		
	citationincontext = []
	highlightline = line[0]
	locus = resultformatter(line, searchterm, False)
	for w in authorobject.listofworks:
		if w.universalid == workdbname:
			workobject = w
	citation = locusintocitation(workobject, locus['locus'])
	# this next bit of info tags the find; 'newfind' + 'url' is turned into JS in the search.html '<script>' loop; this enables click-to-browse
	# similarly the for-result-in-found loop of search.html generates the clickable elements: <browser id="{{ context['url'] }}">
	citationincontext.append({'newfind': 1, 'author': authorobject.shortname,
	                 'work': workobject.title, 'citation': citation, 'url': (workdbname+'_LN_'+str(locus['index']))})
	environs = simplecontextgrabber(workobject, highlightline, linesofcontext, cursor)

	for found in environs:
		if found[0] == highlightline:
			found = resultformatter(found, searchterm, True)
		else:
			found = resultformatter(found, searchterm, False)
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


def formatauthorandworkinfo(authorname,workinfo):
	"""
	dbdata into html
	send me: authorname + universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""
	
	t = workinfo[1]
	c = workinfo[3]
	
	a = authorname
	t = '<span class="italic">' + t + '</span> '
	
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


# slated for removal

def dbformatauthinfo(authinfo):
	"""
	db data into html
	send me: cleanname, universalid, genres, floruit, location, language

	"""
	
	n = authinfo[0]
	d = authinfo[1]
	g = authinfo[2]
	f = authinfo[3]
	lc = authinfo[4]
	lg = authinfo[5]
	
	n = '<span class="emph">' + n + '</span>'
	d = '[id: ' + d[2:] + ']<br />'
	
	if g is not None and g != '':
		g = 'classified among: ' + g + '; '
	else:
		g = ''
	
	if lg == 'G':
		try:
			if int(f) == 1500:
				fl = 'approx date is unknown (search for 1500 C.E.)'
			elif int(f) > 0:
				fl = 'assigned to approx date: ' + str(f) + ' C.E.'
			elif int(f) < 0:
				fl = 'assigned to approx date: ' + str(f)[1:] + ' B.C.E.'
		except:
			# there was no f and so no int(f)
			fl = ''
	else:
		fl = ''
	
	authinfo = n + '&nbsp;' + d + '&nbsp;' + g + fl
	
	return authinfo


def dbformatworkinfo(workinfo):
	"""
	dbdata into html
	send me: universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""
	
	n = workinfo[0][-3:]
	t = workinfo[1]
	g = workinfo[2]
	c = workinfo[3]
	p = workinfo[4]
	
	p = formatpublicationinfo(p)
	
	n = '(' + n + ')&nbsp;'
	t = '<span class="title">' + t + '</span> '
	
	if g is not None:
		g = '[' + g + ']&nbsp;'
	else:
		g = ''
	
	if c is not None:
		c = '[' + format(c, ',d') + ' wds]'
	else:
		c = ''
	
	workinfo = n + t + g + c + '<br />' + p + '<br />'
	
	return workinfo


def dbremovespuria(authorandworklist, cursor):
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
		query = 'SELECT title FROM works WHERE universalid = %s'
		data = (re.sub(r'x', r'w', aw[0:10]),)
		cursor.execute(query, data)
		found = cursor.fetchone()
		try:
			if re.search(sp, found[0]) is not None:
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


def dbprunebydate(authorandworklist, cursor):
	"""
	send me a list of authorsandworks and i will trim it via the session date limit variables
	:param authorandworklist:
	:param cursor:
	:return:
	"""
	trimmedlist = []
	
	if session['corpora'] == 'G' and (session['earliestdate'] != '-850' or session['latestdate'] != '1500'):
		min = int(session['earliestdate'])
		max = int(session['latestdate'])
		if min > max:
			min = max
			session['earliestdate'] = session['latestdate']
		
		# because there is no need to query plutarch 100 times
		previous = ['', '']
		for aw in authorandworklist:
			if aw[0:6] != previous[0]:
				query = 'SELECT floruit FROM authors WHERE universalid = %s'
				data = (aw[0:6],)
				cursor.execute(query, data)
				found = cursor.fetchall()
				try:
					date = float(found[0][0])
				except:
					date = -9999
			else:
				date = previous[1]
			
			if date < min or date > max:
				# print('dropped',aw[0].name,found[0][0])
				pass
			else:
				trimmedlist.append(aw)
			
			previous = [aw[0:6], date]
	
	else:
		trimmedlist = authorandworklist
	
	return trimmedlist


def dbformattedcittationincontext(line, workdbname, linesofcontext, searchterm, cursor):
	if '_AT_' in workdbname:
		workdbname = workdbname[0:10]
	
	authorobject = dbauthorandworkmaker(workdbname[0:6], cursor)
	citationincontext = []
	highlightline = line[0]
	locus = resultformatter(line, searchterm, False)
	for w in authorobject.listofworks:
		if w.universalid == workdbname:
			workobject = w
	citation = locusintocitation(workobject, locus['locus'])
	# this next bit of info tags the find; 'newfind' + 'url' is turned into JS in the search.html '<script>' loop; this enables click-to-browse
	# similarly the for-result-in-found loop of search.html generates the clickable elements: <browser id="{{ context['url'] }}">
	citationincontext.append({'newfind': 1, 'author': authorobject.shortname,
	                          'work': workobject.title, 'citation': citation,
	                          'url': (workdbname + '_LN_' + str(locus['index']))})
	environs = simplecontextgrabber(workobject, highlightline, linesofcontext, cursor)
	
	for found in environs:
		if found[0] == highlightline:
			found = resultformatter(found, searchterm, True)
		else:
			found = resultformatter(found, searchterm, False)
		citationincontext.append(found)
	
	return citationincontext


