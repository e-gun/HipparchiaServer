# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
from string import punctuation


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


def stripaccents(texttostrip, transtable=None):
	"""

	turn ᾶ into α, etc

	there are more others ways to do this; but this is the fast way
	it turns out that this was one of the slowest functions in the profiler

	transtable should be passed here outside of a loop
	but if you are just doing things one-off, then it is fine to have
	stripaccents() look up transtable itself

	:param texttostrip:
	:return:
	"""

	if transtable == None:
		transtable = buildhipparchiatranstable()

	stripped = texttostrip.translate(transtable)

	return stripped


def buildhipparchiatranstable():
	"""

	pulled this out of stripaccents() so you do not maketrans 200k times when
	polytonicsort() sifts an index

	:return:
	"""

	invals = ['ἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ']
	outvals = ['αααααααααααααααααααααααααεεεεεεεειιιιιιιιιιιιιιιιιοοοοοοοουυυυυυυυυυυυυυυυυηηηηηηηηηηηηηηηηηηηηηηηωωωωωωωωωωωωωωωωωωωωωωω']

	invals.append('ᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑἘἙἚἛἜἝΕἸἹἺἻἼἽἾἿΙὈὉὊὋὌὍΟὙὛὝὟΥᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯΗᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯΩῤῥῬΒΨΔΦΓΞΚΛΜΝΠϘΡσΣςϹΤΧΘΖ')
	outvals.append('αααααααααααααααααεεεεεεειιιιιιιιιοοοοοοουυυυυηηηηηηηηηηηηηηηηηωωωωωωωωωωωωωωωωωρρρβψδφγξκλμνπϙρϲϲϲϲτχθζ')

	invals.append('vUjÁÄáäÉËéëÍÏíïÓÖóöÜÚüú')
	outvals.append('uViaaaaeeeeiiiioooouuuu')

	invals = ''.join(invals)
	outvals = ''.join(outvals)

	transtable = str.maketrans(invals, outvals)

	return transtable


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


def tidyupterm(word, punct=None):
	"""
	remove gunk that should not be present in a cleaned line

	:param word:
	:return:
	"""

	if not punct:
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


def cleanaccentsandvj(texttostrip):
	"""
	turn ᾶ into α, etc

	:return:
	"""

	substitutes = (
		('v', 'u'),
		('U', 'V'),
		('[Jj]', 'i'),
		('[ÁÄ]', 'A'),
		('[áä]', 'a'),
		('[ÉË]', 'E'),
		('[éë]', 'e'),
		('[ÍÏ]', 'I'),
		('[íï]', 'i'),
		('[ÓÖ]', 'O'),
		('[óö]', 'o'),
		('[ῥῤῬ]', 'ρ'),
		# some sort of problem with acute alpha which seems to be unkillable
		# (u'u\1f71',u'\u03b1'),
		('[ἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰά]', 'α'),
		('[ἐἑἒἓἔἕὲέ]', 'ε'),
		('[ἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐϊ]', 'ι'),
		('[ὀὁὂὃὄὅόὸ]', 'ο'),
		('[ὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺ]', 'υ'),
		('[ὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]', 'ω'),
		# similar problems with acute eta
		# (u'\u1f75','η'),
		('[ᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧ]', 'η'),
		('[ᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯΩ]', 'ω'),
		('[ὈὉὊὋὌὍΟ]', 'ο'),
		('[ᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ]', 'α'),
		('[ἘἙἚἛἜἝΕ]', 'ε'),
		('[ἸἹἺἻἼἽἾἿΙΪ]', 'ι'),
		('[ὙὛὝὟΥΫ]', 'υ'),
		('[ᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯΗ]', 'η'),
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