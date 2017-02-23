# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import re
import configparser
from string import punctuation

from flask import session
from server import hipparchia

config = configparser.ConfigParser()
config.read('config.ini')


def removegravity(accentedword):
	"""
	turn all graves into accutes so you can match the dictionary form
	:param accentedword:
	:return:
	"""
	# this failed to work when i typed the greekkeys versions: look out for identical looks with diff unicode vals...
	# meanwhile eta did not work until the unicode codes were forced...

	terminalgravea = re.compile(r'([ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ])$')
	terminalgraveb = re.compile(r'([ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ])(.)$')

	try:
		if accentedword[-1] in 'ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ':
			accentedword = re.sub(terminalgravea, forceterminalacute, accentedword)
	except:
		# the word was not >0 char long
		pass
	try:
		if accentedword[-2] in 'ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ':
			accentedword = re.sub(terminalgraveb, forceterminalacute, accentedword)
	except:
		# the word was not >1 char long
		pass

	return accentedword


def forceterminalacute(matchgroup):
	"""
	θαμά and θαμὰ need to be stored in the same place

	otherwise you will click on θαμὰ, search for θαμά and get prevalence data that is not what you really wanted

	:param match:
	:return:
	"""

	map = { 'ὰ': 'ά',
	        'ὲ': 'έ',
	        'ὶ': 'ί',
	        'ὸ': 'ό',
	        'ὺ': 'ύ',
	        'ὴ': 'ή',
	        'ὼ': 'ώ',
			'ἂ': 'ἄ',
			'ἒ': 'ἔ',
			'ἲ': 'ἴ',
			'ὂ': 'ὄ',
			'ὒ': 'ὔ',
			'ἢ': 'ἤ',
			'ὢ': 'ὤ',
			'ᾃ': 'ᾅ',
			'ᾓ': 'ᾕ',
			'ᾣ': 'ᾥ',
			'ᾂ': 'ᾄ',
			'ᾒ': 'ᾔ',
			'ᾢ': 'ᾤ',
		}

	substitute = map[matchgroup[1]]
	try:
		# the word did not end with a vowel
		substitute += matchgroup[2]
	except:
		# the word ended with a vowel
		pass

	return substitute


def stripaccents(texttostrip):
	"""
	turn ᾶ into α, etc

	:return:
	"""
	substitutes = (
		('v', 'u'),
		('U', 'V'),
		('(Á|Ä)', 'A'),
		('(á|ä)', 'a'),
		('(É|Ë)', 'E'),
		('(é|ë)', 'e'),
		('(Í|Ï)', 'I'),
		('(í|ï)', 'i'),
		('(Ó|Ö)', 'O'),
		('(ó|ö)', 'o'),
		('(ῤ|ῥ|Ῥ)', 'ρ'),
		# some sort of problem with acute alpha which seems to be unkillable
		# (u'u\1f71',u'\u03b1'),
		('(ἀ|ἁ|ἂ|ἃ|ἄ|ἅ|ἆ|ἇ|ᾀ|ᾁ|ᾂ|ᾃ|ᾄ|ᾅ|ᾆ|ᾇ|ᾲ|ᾳ|ᾴ|ᾶ|ᾷ|ᾰ|ᾱ|ὰ|ά)', 'α'),
		('(ἐ|ἑ|ἒ|ἓ|ἔ|ἕ|ὲ|έ)', 'ε'),
		('(ἰ|ἱ|ἲ|ἳ|ἴ|ἵ|ἶ|ἷ|ὶ|ί|ῐ|ῑ|ῒ|ΐ|ῖ|ῗ|ΐ)', 'ι'),
		('(ὀ|ὁ|ὂ|ὃ|ὄ|ὅ|ό|ὸ)', 'ο'),
		('(ὐ|ὑ|ὒ|ὓ|ὔ|ὕ|ὖ|ὗ|ϋ|ῠ|ῡ|ῢ|ΰ|ῦ|ῧ|ύ|ὺ)', 'υ'),
		('(ὠ|ὡ|ὢ|ὣ|ὤ|ὥ|ὦ|ὧ|ᾠ|ᾡ|ᾢ|ᾣ|ᾤ|ᾥ|ᾦ|ᾧ|ῲ|ῳ|ῴ|ῶ|ῷ|ώ|ὼ)', 'ω'),
		# similar problems with acute eta
		# (u'\u1f75','η'),
		('(ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|ή|ἠ|ἡ|ἦ|ἧ)', 'η'),
		('(ᾨ|ᾩ|ᾪ|ᾫ|ᾬ|ᾭ|ᾮ|ᾯ|Ὠ|Ὡ|Ὢ|Ὣ|Ὤ|Ὥ|Ὦ|Ὧ|Ω)', 'ω'),
		('(Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ|Ο)', 'ο'),
		('(ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ|Α)', 'α'),
		('(Ἐ|Ἑ|Ἒ|Ἓ|Ἔ|Ἕ|Ε)', 'ε'),
		('(Ἰ|Ἱ|Ἲ|Ἳ|Ἴ|Ἵ|Ἶ|Ἷ|Ι)', 'ι'),
		('(Ὑ|Ὓ|Ὕ|Ὗ|Υ)', 'υ'),
		('(ᾘ|ᾙ|ᾚ|ᾛ|ᾜ|ᾝ|ᾞ|ᾟ|Ἠ|Ἡ|Ἢ|Ἣ|Ἤ|Ἥ|Ἦ|Ἧ|Η)', 'η'),
		('Β', 'β'),
		('Ψ', 'ψ'),
		('Δ', 'δ'),
		('Φ', 'φ'),
		('Γ', 'γ'),
		('Ξ', 'ξ'),
		('Κ', 'κ'),
		('Λ', 'λ'),
		('Μ', 'μ'),
		('Ν', 'ν'),
		('Π', 'π'),
		('Ϙ', 'ϙ'),
		('Ρ', 'ρ'),
		('Ϲ', 'ϲ'),
		('Τ', 'τ'),
		('Θ', 'θ'),
		('Ζ', 'ζ')
	)
	
	for swap in range(0, len(substitutes)):
		texttostrip = re.sub(substitutes[swap][0], substitutes[swap][1], texttostrip)
	
	return texttostrip


def getpublicationinfo(workobject, cursor):
	"""
	what's in a name?
	:param workobject:
	:return: html for the bibliography
	"""
	
	uid = workobject.universalid
	query = 'SELECT publication_info FROM works WHERE universalid = %s'
	data = (uid,)
	cursor.execute(query, data)
	pi = cursor.fetchone()
	pi = pi[0]
	
	publicationhtml = formatpublicationinfo(pi)

	return publicationhtml


def formatpublicationinfo(pubinfo):
	"""
	in:
		<volumename>FHG </volumename>4 <press>Didot </press><city>Paris </city><year>1841–1870</year><pages>371 </pages><pagesintocitations>Frr. 1–2</pagesintocitations><editor>Müller, K. </editor>
	out:
		<span class="pubvolumename">FHG <br /></span><span class="pubpress">Didot , </span><span class="pubcity">Paris , </span><span class="pubyear">1841–1870. </span><span class="pubeditor"> (Müller, K. )</span>
	
	:param pubinfo:
	:return:
	"""

	tags = [
		{'volumename': ['', '<br />']},
		{'press': ['', ', ']},
		{'city': ['', ', ']},
		{'year': ['', '. ']},
		{'series': ['', '']},
		{'editor': [' (', ')']},
		# {'pages':[' (',')']}
	]
	
	publicationhtml = ''
	
	for t in tags:
		tag = next(iter(t.keys()))
		val = next(iter(t.values()))
		seek = re.compile('<' + tag + '>(.*?)</' + tag + '>')
		if re.search(seek, pubinfo) is not None:
			found = re.search(seek, pubinfo)
			foundinfo = avoidlonglines(found.group(1), 120, '<br />', [])
			publicationhtml += '<span class="pub' + tag + '">' + val[0] + foundinfo + val[1] + '</span>'
	
	return publicationhtml


def bcedating():
	"""
	return the English equivalents for session['earliestdate'] and session['latestdate']
	:return:
	"""
	
	dmax = session['latestdate']
	dmin = session['earliestdate']
	if dmax[0] == '-':
		dmax = dmax[1:] + ' B.C.E.'
	else:
		dmax = dmax + ' C.E.'
	
	if dmin[0] == '-':
		dmin = dmin[1:] + ' B.C.E.'
	else:
		dmin = dmin + 'C.E.'
		
	return dmin, dmax


def htmlifysearchfinds(listoffinds):
	"""
	it is too painful to let JS turn this information into HTML
	the Flask template used to do this work, now this does it

	send me a list of FormattedSearchResult objects

	:param listoffinds:
	:return:
	"""

	resultsashtml = []
	listofurls = []

	for find in listoffinds:
		htmlforthefind = ''
		lines = find.formattedlines

		listofurls.append(find.clickurl)

		htmlforthefind += '<locus>\n'
		htmlforthefind += '\t<span class="findnumber">[%(hn)d]</span>&nbsp;&nbsp;'
		htmlforthefind += '<span class="foundauthor">%(au)s</span>,&nbsp;'
		htmlforthefind += '<span class="foundwork">%(wk)s</span>:\n'
		htmlforthefind += '\t<browser id="%(url)s">'
		htmlforthefind += '<span class="foundlocus">%(cs)s</span><br />'
		htmlforthefind += '</browser>\n</locus>\n'

		substitutes = {'hn': find.hitnumber, 'au': find.author, 'wk': find.work, 'url': find.clickurl, 'cs': find.citationstring}
		htmlforthefind = htmlforthefind % substitutes

		for ln in lines:
			prefix = ''
			if hipparchia.config['DBDEBUGMODE'] == 'yes':
				prefix = '<smallcode>%(id)s</smallcode>&nbsp;' %{'id': ln.universalid}
			htmlforthefind += '%(pr)s<span class="locus">%(lc)s</span>&nbsp;\n'
			if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
				htmlforthefind += '<span class="foundtext">%(lh)s</span><br />\n'
			else:
				htmlforthefind += '<span class="foundtext">%(la)s</span><br />\n'

			substitutes = {'pr': prefix, 'lc': ln.locus(), 'lh': ln.showlinehtml(), 'la': ln.accented}
			htmlforthefind = htmlforthefind % substitutes

		resultsashtml.append(htmlforthefind)

	htmlandjs = {}
	htmlandjs['hits'] = resultsashtml

	if len(listoffinds) > 0:
		htmlandjs['hitsjs'] = injectbrowserjavascript(listofurls)
	else:
		htmlandjs['hitsjs'] = ''

	return htmlandjs


def injectbrowserjavascript(listofurls):
	"""
	the clickable urls don't work without inserting new js into the page to catch the clicks
	need to match the what we used to get via the flask template
	:return:
	"""
	
	jso = ['document.getElementById("'+url+'").onclick = openbrowserfromclick;' for url in listofurls]
	jsoutput = '\n'.join(jso)

	return jsoutput


def insertcrossreferencerow(lineobject):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""
	linehtml = ''

	if re.search(r'documentnumber',lineobject.annotations) is None:
		columna = ''
		columnb = '<span class="crossreference">{ln}</span>'.format(ln=lineobject.annotations)

		linehtml = '<tr class="browser"><td class="crossreference">{c}</td>'.format(c=columnb)
		linehtml += '<td class="crossreference">{c}</td></tr>\n'.format(c=columna)

	return linehtml


def insertdatarow(label, css, founddate):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""

	columna = ''
	columnb = '<span class="textdate">{l}:&nbsp;{fd}</span>'.format(l=label, fd=founddate)
	
	linehtml = '<tr class="browser"><td class="{css}">{cb}</td>'.format(css=css, cb=columnb)
	linehtml += '<td class="crossreference">{ca}</td></tr>\n'.format(ca=columna)

	return linehtml


def avoidlonglines(string, maxlen, splitval, stringlist=[]):
	"""

	Authors like Livy can swallow the browser window by sending 351 characters worth of editors to one of the lines

	break up a long line into multiple lines by splitting every N characters

	splitval will be something like '<br />' or '\n'

	:param string:
	:param maxlen:
	:return:
	"""

	breakcomeswithinamarkupseries = re.compile(r'^\s[^\s]{1,}>')

	if len(string) < maxlen:
		stringlist.append(string)
		newstringhtml = splitval.join(stringlist)
	else:
		searchzone = string[0:maxlen]
		stop = False
		stopval = len(string)

		for c in range(maxlen-1,-1,-1):
			if searchzone[c] == ' ' and stop == False and re.search(breakcomeswithinamarkupseries, string[c:]) is None:
				stop = True
				stringlist.append(string[0:c])
				stopval = c
		newstringhtml = avoidlonglines(string[stopval+1:], maxlen, splitval, stringlist)

	return newstringhtml


def cleanwords(word):
	"""
	remove gunk that should not be in a concordance
	:param word:
	:return:
	"""

	punct = re.compile('[%s]' % re.escape(punctuation + '\′‵’‘·“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'))
	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)
	# best do punct before this next one...
	try:
		if re.search(r'[a-zA-z]', word[0]) is None:
			word = re.sub(r'[a-zA-z]', '', word)
	except:
		# must have been ''
		pass

	return word


def attemptelision(hypenatedgreekheadword):
	"""

	useful debug query:
		select * from greek_lemmata where dictionary_entry like '%ἀπό-%'

	a difficult class of entry: multiple prefixes
		ὑπό,κατά-κλῄζω1
		ὑπό,κατά,ἐκ-λάω1
		ὑπό,ἐν-δύω1
		ὑπό,ἐκ-λάω1
		ὑπό,ἐκ-εἴρω2
		ὑπό,ἐκ-ἐράω1
		ὑπό,ἐκ-δύω1
		ὑπό,ἐκ-ἀράω2
		ὑπό,ἀνά,ἀπό-νέω1
		ὑπό,ἀνά,ἀπό-αὔω2

	this will try to do it all at a go, but ideally a MorphPossibilityObject.getbaseform() call will
	send nothing worse than things that look like 'ὑπό,ἐκ-δύω' here since that function attempts to
	call this successively in the case of multiple compounds: first you get ἀπό-αὔω2 then you ask for
	ἀνά-ἀπαὔω2, then you ask for ὑπό-ἀνάπόαὔω2

	IN PROGRESS BUT MOSTLY WORKING FOR GREEK

	Latin works on all of the easy cases; no effort made on the hard ones yet

	:param hypenatedgreekheadword:
	:return:
	"""

	entry = hypenatedgreekheadword
	terminalacute = re.compile(r'[άέίόύήώ]')
	initialrough = re.compile(r'[ἁἑἱὁὑἡὡῥἃἓἳὃὓἣὣ]')
	initialsmooth = re.compile(r'[ἀἐἰὀὐἠὠἄἔἴὄὔἤὤ]')

	unaspirated = 'π'
	aspirated = 'φ'


	units = hypenatedgreekheadword.split(',')
	hyphenated = units[-1]

	prefix = hyphenated.split('-')[0]
	stem = hyphenated.split('-')[1]

	if re.search(terminalacute, prefix[-1]) is not None and re.search(initialrough, stem[0]) is None and re.search(initialsmooth, stem[0]) is not None:
		# print('A')
		# vowel + vowel: 'ἀπό-ἀθρέω'
		entry = prefix[:-1]+stripaccents(stem[0])+stem[1:]
	elif re.search(terminalacute, prefix[-1]) is not None and re.search(initialrough, stem[0]) is None and re.search(initialrough, stem[0]) is None:
		# print('B')
		# vowel + consonant: 'ἀπό-νέω'
		entry = prefix[:-1]+stripaccents(prefix[-1])+stem
	elif re.search(terminalacute, prefix[-1]) is None and re.search(initialrough, stem[0]) is None and re.search(initialrough, stem[0]) is None:
		# consonant + consonant: 'ἐκ-δαϲύνω'
		if prefix[-1] not in ['ν'] and stem[0] not in ['γ', 'λ', 'μ']:
			# print('C1')
			# consonant + consonant: 'ἐκ-δαϲύνω'
			entry = prefix+stem
		elif prefix[-1] in ['ν'] and stem[0] in ['γ', 'λ', 'μ', 'ϲ']:
			# print('C2')
			# consonant + consonant: 'ϲύν-μνημονεύω'
			if prefix == 'ϲύν':
				prefix = stripaccents(prefix)
			entry = prefix[:-1]+stem[0]+stem
		elif prefix[-1] in ['ν']:
			#print('C3')
			prefix = stripaccents(prefix)
			entry = prefix+stem
		else:
			#print('C0')
			pass
	elif re.search(terminalacute, prefix[-1]) is not None and re.search(initialrough, stem[0]) is not None and re.search(unaspirated, prefix[-2]) is not None:
		# print('D')
		# vowel + rough and 'π' is in the prefix
		entry = prefix[:-2] + aspirated + stripaccents(stem[0]) + stem[1:]


	return entry

