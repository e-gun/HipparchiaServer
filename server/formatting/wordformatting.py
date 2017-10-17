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

	remap = {'ὰ': 'ά',
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

	substitute = remap[matchgroup[1]]
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
	invals = list()
	outvals = list()

	invals.append('ἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰά')
	outvals.append('α' * len(invals[-1]))
	invals.append('ἐἑἒἓἔἕὲέ')
	outvals.append('ε' * len(invals[-1]))
	invals.append('ἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐ')
	outvals.append('ι' * len(invals[-1]))
	invals.append('ὀὁὂὃὄὅόὸ')
	outvals.append('ο' * len(invals[-1]))
	invals.append('ὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺ')
	outvals.append('υ' * len(invals[-1]))
	invals.append('ᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧ')
	outvals.append('η' * len(invals[-1]))
	invals.append('ὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ')
	outvals.append('ω' * len(invals[-1]))

	invals.append('ᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ')
	outvals.append('α'*len(invals[-1]))
	invals.append('ἘἙἚἛἜἝΕ')
	outvals.append('ε' * len(invals[-1]))
	invals.append('ἸἹἺἻἼἽἾἿΙ')
	outvals.append('ι' * len(invals[-1]))
	invals.append('ὈὉὊὋὌὍΟ')
	outvals.append('ο' * len(invals[-1]))
	invals.append('ὙὛὝὟΥ')
	outvals.append('υ' * len(invals[-1]))
	invals.append('ᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯΗ')
	outvals.append('η' * len(invals[-1]))
	invals.append('ᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯ')
	outvals.append('ω' * len(invals[-1]))
	invals.append('ῤῥῬ')
	outvals.append('ρρρ')
	invals.append('ΒΨΔΦΓΞΚΛΜΝΠϘΡσΣςϹΤΧΘΖ')
	outvals.append('βψδφγξκλμνπϙρϲϲϲϲτχθζ')

	invals.append('vUJjÁÄáäÉËéëÍÏíïÓÖóöÜÚüú')
	outvals.append('uVIiaaaaeeeeiiiioooouuuu')

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
			# print('C3')
			prefix = stripaccents(prefix)
			entry = prefix+stem
		else:
			# print('C0')
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

	:param hypenatedlatinheadword:
	:return:
	"""

	hypenatedlatinheadword = re.sub(r'_', '', hypenatedlatinheadword)

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

	pass punct if you do not feel like compiling it 100k times

	:param word:
	:param punct:
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
	except IndexError:
		# must have been ''
		pass

	invals = u'jv'
	outvals = u'iu'
	word = word.translate(str.maketrans(invals, outvals))

	return word


def universalregexequivalent(searchterm):
	"""

	in order to properly highlight a polytonic word that you found via a unaccented search you need to convert:
		ποταμον
	into:
		([πΠ][οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ][τΤ][αἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ][μΜ][οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ][νΝ])

	NB: this function also takes care of capitalization issues: the search is always lower case, but results will be marked
	without regard to their case: 'Antonius', 'Kalendas', etc.

	this function is also called by searchdictionary() to address the τήθη vs τηθή issue

	:param searchterm:
	:return:
	"""

	# need to avoid having '\s' turn into '\[Ss]', etc.
	searchterm = re.sub(r'\\s', '😀', searchterm)
	searchterm = re.sub(r'\\w', '👽', searchterm)

	equivalents = {
		'α': '[αἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ]',
		'β': '[βΒ]',
		'ψ': '[ψΨ]',
		'δ': '[δΔ]',
		'ε': '[εἐἑἒἓἔἕὲέΕἘἙἚἛἜἝ]',
		'φ': '[φΦ]',
		'γ': '[γΓ]',
		'η': '[ηᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἡἦΗᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯ]',
		'ι': '[ιἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐἸἹἺἻἼἽἾἿΙ]',
		'ξ': '[ξΞ]',
		'κ': '[κΚ]',
		'λ': '[λΛ]',
		'μ': '[μΜ]',
		'ν': '[νΝ]',
		'ο': '[οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ]',
		'π': '[πΠ]',
		'ρ': '[ρΡῥῬ]',
		'ϲ': '[σςΣϲϹ]',
		'σ': '[σςΣϲϹ]',
		'ς': '[σςΣϲϹ]',
		'τ': '[τΤ]',
		'υ': '[υὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺὙὛὝὟΥ]',
		'ω': '[ωὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼΩᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯΩ]',
		'χ': '[χΧ]',
		'θ': '[θΘ]',
		'ζ': '[ζΖ]',
		'b': '[Bb]',
		'c': '[Cc]',
		'd': '[Dd]',
		'f': '[Ff]',
		'g': '[Gg]',
		'h': '[Hh]',
		'j': '[JjIi]',
		'k': '[Kk]',
		'l': '[Ll]',
		'm': '[Mm]',
		'n': '[Nn]',
		'p': '[Pp]',
		'q': '[Qq]',
		'r': '[Rr]',
		's': '[Ss]',
		't': '[Tt]',
		'w': '[Ww]',
		'x': '[Xx]',
		'y': '[Yy]',
		'z': '[Zz]',
		'a': '[Aaáä]',
		'e': '[Eeéë]',
		'i': '[IiíïJj]',
		'o': '[Ooóö]',
		'u': '[UuüVv]',
		'v': '[VvUuü]'
	}

	searchtermequivalent = ''
	searchterm = re.sub(r'(^\s|\s$)', '', searchterm)
	for c in searchterm:
		try:
			c = equivalents[c]
		except KeyError:
			pass
		searchtermequivalent += c
	# searchtermequivalent = '(^|)('+searchtermequivalent+')($|)'
	searchtermequivalent = re.sub(r'😀', '\s', searchtermequivalent)
	searchtermequivalent = re.sub(r'👽', '\w', searchtermequivalent)
	searchtermequivalent = '({s})'.format(s=searchtermequivalent)

	try:
		searchtermequivalent = searchtermequivalent
	except:
		# if you try something like '(Xἰ' you will produce an error:
		# sre_constants.error: missing ), unterminated subpattern at position 0
		searchtermequivalent = None

	return searchtermequivalent


def depunct(stringtoclean, allowedpunctuationsting=None):
	"""

	'abc*d$ef, ghi;' + ',;' ==> 'abcdef, ghi;'

	:param wordtoclean:
	:param allowedpunctuationsting:
	:return:
	"""

	badpunct = punctuation
	if allowedpunctuationsting:
		badpunct = set(badpunct) - set(allowedpunctuationsting)
		badpunct = ''.join(badpunct)
	badpunct = r'[{np}]'.format(np=re.escape(badpunct))

	cleaned = re.sub(badpunct, '', stringtoclean)

	return cleaned


def avoidsmallvariants(text):
	"""

	get rid of small variants of '+', etc.
	:return:
	"""

	invals = "﹖﹡／﹗│﹦﹢﹪﹠﹕＇❨❩❴❵⟦⟧"
	outvals = "?*/!|=+%&:'(){}[]"

	cleantext = text.translate(str.maketrans(invals, outvals))

	return cleantext


def forcelunates(text):
	"""

	override σ and ς in the data and instead print ϲ

	:param text:
	:return:
	"""

	invals = "σςΣ"
	outvals = "ϲϲϹ"

	cleantext = text.translate(str.maketrans(invals, outvals))

	return cleantext


def attemptsigmadifferentiation(text):
	"""

	override ϲ and try to print σ or ς as needed

	:param text:
	:return:
	"""

	# first pass
	invals = "ϲϹ"
	outvals = "σΣ"

	text = text.translate(str.maketrans(invals, outvals))

	# then do terminal sigma
	# look out for ς’ instead of σ’
	straypunct = r'\<\>\{\}\[\]\(\)⟨⟩₍₎\.\?\!⌉⎜͙✳※¶§͜﹖→𐄂𝕔;:ˈ＇,‚‛‘“”„·‧∣'
	combininglowerdot = u'\u0323'
	boundaries = r'([' + combininglowerdot + straypunct + '\s]|$)'
	terminalsigma = re.compile(r'σ' + boundaries)
	cleantext = re.sub(terminalsigma, r'ς\1', text)

	return cleantext


def wordlistintoregex(wordlist):
	"""

	turn
		['a', 'b', 'c']

	into something like
		re.search(r'('a'|'b'|'c')')

	:param wordlist:
	:return:
	"""

	# overkill: but this can deal with enclitics that change the accentuation of the word...
	# wordlist = [universalregexequivalent(stripaccents(w)) for w in wordlist]

	# all words in the data column are lowercase...
	# wordlist = [upperorlowerregex(w) for w in wordlist]

	wordlist = [acuteorgrav(w.lower()) for w in wordlist]
	wordlist = ['((^|\s){w}(\s|$))'.format(w=w) for w in wordlist]
	searchterm = '|'.join(wordlist)

	return searchterm


def upperorlowerregex(word):
	"""

	turn
		'word'

	into
		'[wW][oO][rR][dD]'

	:param word:
	:return:
	"""

	reg = ['[{a}{b}]'.format(a=w, b=w.upper()) for w in word]
	reg = ''.join(reg)

	return reg


def acuteorgrav(word):
	"""

	turn
		τολμηρόϲ

	into
		τολμηρ[όὸ]ϲ

	:param word:
	:return:
	"""

	remap = {'ά': 'ὰ',
			'έ': 'ὲ',
			'ί': 'ὶ',
			'ό': 'ὸ',
			'ύ': 'ὺ',
			'ή': 'ὴ',
			'ώ': 'ὼ',
			'ἄ': 'ἂ',
			'ἔ': 'ἒ',
			'ἴ': 'ἲ',
			'ὄ': 'ὂ',
			'ὔ': 'ὒ',
			'ἤ': 'ἢ',
			'ὤ': 'ὢ',
			'ᾅ': 'ᾃ',
			'ᾕ': 'ᾓ',
			'ᾥ': 'ᾣ',
			'ᾄ': 'ᾂ',
			'ᾔ': 'ᾒ',
			'ᾤ': 'ᾢ'
	         }

	tail = word[-2:]

	if len(word) > 2:
		head = word[0:-2]
	else:
		head = ''

	reg = head

	for t in tail:
		if t in remap:
			reg += '[{a}{b}]'.format(a=t, b=remap[t])
		else:
			reg += t

	return reg
