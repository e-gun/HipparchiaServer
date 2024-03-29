# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
from string import punctuation

from server import hipparchia

# the one: because sometimes you don't want to zap τ’, δ’, κτλ.
# the other: and sometimes you do
elidedextrapunct = '\′‵‘·̆́“”„—†ˈ⌈⌋⌊⟫⟪❵❴⟧⟦«»›‹⟨⟩⸐„⸏⸖⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚̄⁝͜‖͡⸓͝'
extrapunct = elidedextrapunct + '’'
badpucntwithbackslash = '′‵‘·̆́“”„—†ˈ⌈⌋⌊⟫⟪❵❴⟧⟦«»›‹⟨⟩⸐„⸏⸖⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚̄⁝͜‖͡⸓͝' + '’'

minimumgreek = re.compile('[α-ωῥἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')


def removegravity(accentedword: str) -> str:
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


def forceterminalacute(matchgroup: re.match) -> str:
	"""
	θαμά and θαμὰ need to be stored in the same place

	otherwise you will click on θαμὰ, search for θαμά and get prevalence data that is not what you really wanted

	:param matchgroup:
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


def stripaccents(texttostrip: str, transtable=None) -> str:
	"""

	turn ᾶ into α, etc

	there are more others ways to do this; but this is the fast way
	it turns out that this was one of the slowest functions in the profiler

	transtable should be passed here outside of a loop
	but if you are just doing things one-off, then it is fine to have
	stripaccents() look up transtable itself

	:param texttostrip:
	:param transtable:
	:return:
	"""

	# if transtable == None:
	# 	transtable = buildhipparchiatranstable()

	try:
		stripped = texttostrip.translate(transtable)
	except TypeError:
		stripped = stripaccents(texttostrip, transtable=buildhipparchiatranstable())

	return stripped


def buildhipparchiatranstable() -> dict:
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

	# some of the vowels with quantities are compounds of vowel + accent: can't cut and paste them into the xformer
	invals.append('vUJjÁÄáäÉËéëÍÏíïÓÖóöÜÚüúăāĕēĭīŏōŭū')
	outvals.append('uVIiaaaaeeeeiiiioooouuuuaaeeiioouu')

	invals = str().join(invals)
	outvals = str().join(outvals)

	transtable = str.maketrans(invals, outvals)

	return transtable


def gkattemptelision(hypenatedgreekheadword: str) -> str:
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


def latattemptelision(hypenatedlatinheadword: str) -> str:
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


def tidyupterm(word: str, punct=None) -> str:
	"""

	remove gunk that should not be present in a cleaned line

	pass punct if you do not feel like compiling it 100k times

	:param word:
	:param punct:
	:return:
	"""

	if not punct:
		punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)

	# best do punct before this next one...
	# wait a minute: why is this needed again? i is deadly if you use this function within vectorland
	# try:
	# 	if re.search(r'[a-zA-z]', word[0]) is None:
	# 		word = re.sub(r'[a-zA-z]', '', word)
	# except IndexError:
	# 	# must have been ''
	# 	pass

	invals = u'jv'
	outvals = u'iu'
	word = word.translate(str.maketrans(invals, outvals))

	return word


def universalregexequivalent(searchterm: str) -> str:
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

	searchtermequivalent = str()
	searchterm = re.sub(r'(^\s|\s$)', '', searchterm)
	for c in searchterm:
		try:
			c = equivalents[c]
		except KeyError:
			pass
		searchtermequivalent += c

	# 'δῆμο[σν]' --> '[δΔ]ῆ[μΜ][οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ][[σςΣϲϹ][νΝ]]'
	# this will subsequently yield: 'FutureWarning: Possible nested set at position 29'
	# better yet, this also won't find 'δῆμοϲ' anyway. the fix: '[[σςΣϲϹ][νΝ]]' --> '[σςΣϲϹνΝ]'
	searchtermequivalent = re.sub(r'\[\[(.*?)\]\[(.*?)\]\]', r'[\1\2]', searchtermequivalent)

	# searchtermequivalent = '(^|)('+searchtermequivalent+')($|)'
	searchtermequivalent = re.sub(r'😀', r'\\s', searchtermequivalent)
	searchtermequivalent = re.sub(r'👽', r'\\w', searchtermequivalent)
	searchtermequivalent = '({s})'.format(s=searchtermequivalent)

	# print('searchtermequivalent', searchtermequivalent)

	try:
		searchtermequivalent = searchtermequivalent
	except:
		# if you try something like '(Xἰ' you will produce an error:
		# sre_constants.error: missing ), unterminated subpattern at position 0
		searchtermequivalent = None

	return searchtermequivalent


def depunct(stringtoclean: str, allowedpunctuationsting=None) -> str:
	"""

	'abc*d$ef, ghi;' + ',;' ==> 'abcdef, ghi;'

	:param stringtoclean:
	:param allowedpunctuationsting:
	:return:
	"""

	if not stringtoclean:
		return str()

	badpunct = punctuation
	if allowedpunctuationsting:
		badpunct = set(badpunct) - set(allowedpunctuationsting)
		badpunct = str().join(badpunct)
	badpunct = r'[{np}]'.format(np=re.escape(badpunct))

	cleaned = re.sub(badpunct, str(), stringtoclean)

	return cleaned


def avoidsmallvariants(text: str) -> str:
	"""

	get rid of small variants of '+', etc.
	:return:
	"""

	invals = "﹖﹡／﹗│﹦﹢﹪﹠﹕＇❨❩❴❵⟦⟧"
	outvals = "?*/!|=+%&:'(){}[]"

	cleantext = text.translate(str.maketrans(invals, outvals))

	return cleantext


def forcelunates(text: str) -> str:
	"""

	override σ and ς in the data and instead print ϲ

	:param text:
	:return:
	"""

	invals = "σςΣ"
	outvals = "ϲϲϹ"

	cleantext = text.translate(str.maketrans(invals, outvals))

	return cleantext


def basiclemmacleanup(text: str) -> str:
	"""

	swap out sigmas and 'v', etc.

	:param text:
	:return:
	"""

	invals = "vjσς"
	outvals = "uiϲϲ"

	text = text.lower()

	cleantext = text.translate(str.maketrans(invals, outvals))

	return cleantext


def attemptsigmadifferentiation(text: str) -> str:
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


def abbreviatedsigmarestoration(text: str) -> str:
	"""

	after attemptsigmadifferentiation() in a lexical entry you will see a lot of things like: τὸ μὲν ς. in the entry
	for σοφός.

	try to fix that

	:param text:
	:return:
	"""

	text = re.sub(r'(?<=[\s>])ς\.', 'σ.', text)
	text = re.sub(r'(?<=[\s>])ς</span>\.', 'σ</span>.', text)

	return text


def wordlistintoregex(wordlist: list) -> str:
	"""

	turn
		['a', 'b', 'c']

	into something like
		re.search(r'('a'|'b'|'c')')

	need to clean up all of the odd things about these words in order to make them match up with the actual data

	:param wordlist:
	:return:
	"""

	# overkill: but this can deal with enclitics that change the accentuation of the word...
	# wordlist = [universalregexequivalent(stripaccents(w)) for w in wordlist]

	# all words in the data column are lowercase...
	# wordlist = [upperorlowerregex(w) for w in wordlist]

	wordlist = [acuteorgrav(w.lower()) for w in wordlist]
	wordlist = [re.sub('[uv]', '[uv]', w) for w in wordlist]
	# wordlist = ['((^|\s){w}(\s|$))'.format(w=w) for w in wordlist]
	wordlist = ['(^|\s){w}(\s|$)'.format(w=w) for w in wordlist]
	searchterm = '|'.join(wordlist)

	return searchterm


def upperorlowerregex(word: str) -> str:
	"""

	turn
		'word'

	into
		'[wW][oO][rR][dD]'

	:param word:
	:return:
	"""

	reg = ['[{a}{b}]'.format(a=w, b=w.upper()) for w in word]
	reg = str().join(reg)

	return reg


def acuteorgrav(word: str) -> str:
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
		head = str()

	reg = head

	for t in tail:
		if t in remap:
			reg += '[{a}{b}]'.format(a=t, b=remap[t])
		else:
			reg += t

	return reg


def setdictionarylanguage(thisword) -> str:
	if re.search(r'[a-z]', thisword):
		usedictionary = 'latin'
	else:
		usedictionary = 'greek'
	return usedictionary


def uforvoutsideofmarkup(textwithmarkup) -> str:
	"""

	take a marked up line; swap u for v
	but don't screw up any v's inside of the markup

	:param textwithmarkup:
	:return:
	"""

	markupfinder = re.compile(r'<.*?>')

	spans = re.finditer(markupfinder, textwithmarkup)
	ranges = [s.span() for s in spans]
	if ranges:
		# e.g., ranges = [(26, 54), (57, 64), (64, 85), (102, 109), (109, 137), (138, 145), (145, 166), (181, 188)]
		ranges = [range(r[0], r[1]) for r in ranges]
		flatten = lambda l: [item for sublist in l for item in sublist]
		preserve = set(flatten(ranges))
		textbyposition = enumerate(textwithmarkup)
		newstr = list()
		for t in textbyposition:
			if t[0] not in preserve and t[1] == 'v':
				newstr.append('u')
			else:
				newstr.append(t[1])
		newstr = str().join(newstr)
	else:
		newstr = re.sub(r'v', 'u', textwithmarkup)

	return newstr


def citationcharacterset() -> set:
	"""

	determined via putting the following code into "/testroute"

	# looking for all of the unique chars required to generate all of the citations.

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()
	flatten = lambda x: [item for sublist in x for item in sublist]

	authorlist = [a for a in authordict]

	charlist = list()

	count = 0
	for a in authorlist:
		count += 1
		q = 'select level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value from {t}'
		cursor.execute(q.format(t=a))
		f = cursor.fetchall()
		c = set(str().join(flatten(f)))
		charlist.append(c)

	charlist = flatten(charlist)
	charlist = set(charlist)
	charlist = list(charlist)
	charlist.sort()

	print(charlist)
	dbconnection.connectioncleanup()


	:return:

	"""

	# ooh, look at all of those dangerous injectable characters...; fortunately some of them are small variants

	allusedchars = {' ', ',', '-', '.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ';', '<', '>', '@',
	                'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R',
	                'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
	                'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
	                'z', '❨', '❩', '⟦', '⟧', '﹕', '﹖', '﹠', '﹡', '﹢', '﹦', '﹪', '＇', '／'}

	return allusedchars


def reducetovalidcitationcharacters(text: str, supplement=None) -> str:
	"""

	take a string and purge it of any characters that could not potentially be found in a citation

	supplement should be a stinrg (which is a list...): '123!|abc"

	:param text:
	:return:
	"""

	text = text[:hipparchia.config['MAXIMUMLOCUSLENGTH']]

	# tempting to exclude ';<>-,.'
	totallyunaccepablenomatterwhat = set()

	validchars = citationcharacterset() - totallyunaccepablenomatterwhat
	if supplement:
		validchars = validchars.union(set(supplement))
	reduced = [x for x in text if x in validchars]
	restored = str().join(reduced)
	return restored
