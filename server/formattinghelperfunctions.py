# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import re
from string import punctuation

from flask import session

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
	except IndexError:
		# the word was not >0 char long
		pass
	try:
		if accentedword[-2] in 'ὰὲὶὸὺὴὼἂἒἲὂὒἢὢᾃᾓᾣᾂᾒᾢ':
			accentedword = re.sub(terminalgraveb, forceterminalacute, accentedword)
	except IndexError:
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
		('j', 'i'),
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

	maxlinelen = 120

	tags = [
		{'volumename': ['', '. ']},
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
		if re.search(seek, pubinfo):
			found = re.search(seek, pubinfo)
			foundinfo = avoidlonglines(found.group(1), maxlinelen, '<br />', [])
			publicationhtml += '<span class="pub{t}">{va}{fi}{vb}</span>'.format(t=tag, va=val[0], fi=foundinfo, vb=val[1])
	
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


def gkattemptelision(hypenatedgreekheadword):
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

	if re.search(terminalacute, prefix[-1]) and re.search(initialrough, stem[0]) is None and re.search(initialsmooth, stem[0]):
		# print('A')
		# vowel + vowel: 'ἀπό-ἀθρέω'
		entry = prefix[:-1]+stripaccents(stem[0])+stem[1:]
	elif re.search(terminalacute, prefix[-1]) and re.search(initialrough, stem[0]) is None and re.search(initialrough, stem[0]) is None:
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
	elif re.search(terminalacute, prefix[-1]) and re.search(initialrough, stem[0]) and re.search(unaspirated, prefix[-2]):
		# print('D')
		# vowel + rough and 'π' is in the prefix
		entry = prefix[:-2] + aspirated + stripaccents(stem[0]) + stem[1:]


	return entry


def latattemptelision(hypenatedlatinheadword):
	"""

	useful debug query:
		﻿select * from latin_lemmata where dictionary_entry like '%-%'
		﻿select * from latin_lemmata where dictionary_entry like '%-%¹'

		de_-sero¹
		con-manduco¹
		per-misceo
		per-misceo
		prae-verto
		dis-sido

	typical cases:
		just combine
		drop one
		merge consonants

	in progress: a fair number of cases are still unhandled

	:param hypenatedgreekheadword:
	:return:
	"""

	hypenatedlatinheadword = re.sub(r'_','',hypenatedlatinheadword)

	triplets = {
		'dsc': 'sc',
		'dse': 'sse',
		'dsi': 'ssi',
		'dso': 'sso',
		'dst': 'st',
		'dsu': 'ssu'
	}

	combinations = {
		'bd': 'd',
		'bf': 'ff',
		'bp': 'pp',
		'bm': 'mm',
		'br': 'rr',
		'dt': 'tt',
		'ds': 'ss',
		'nr': 'rr',
		'np': 'mp',
		'nm': 'mm',
		'dl': 'll',
		'dc': 'cc',
		'xr': 'r',
		'xn': 'n',
		'xm': 'm',
		'xv': 'v',
		'xl': 'l',
		'xd': 'd',
		'sn': 'n',
		'sm': 'm',
		'sr': 'r',
		'sf': 'ff',
		'xe': 'xse'
	}

	units = hypenatedlatinheadword.split(',')
	hyphenated = units[-1]

	prefix = hyphenated.split('-')[0]
	stem = hyphenated.split('-')[1]

	tail = prefix[-1]
	try:
		head = stem[0:1]
	except IndexError:
		head = stem[0]

	combination = tail+head

	if combination in triplets:
		entry = prefix[:-1]+triplets[combination]+stem[2:]
		return entry

	if combination in combinations:
		entry = prefix[:-1]+combinations[combination]+stem[1:]
		return entry

	entry = prefix + stem

	return entry


def tidyupterm(word):
	"""
	remove gunk that should not be present in a cleaned line

	:param word:
	:return:
	"""

	extrapunct = '\′‵’‘·̆́“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))
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

	invals = u'jv'
	outvals = u'iu'
	word = word.translate(str.maketrans(invals, outvals))

	return word