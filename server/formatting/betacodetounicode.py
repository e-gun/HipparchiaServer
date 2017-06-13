# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re


# lifted from HipparchiaBuilder

def replacegreekbetacode(texttoclean):
	"""
	swap betacode for unicode values
	:param texttoclean:
	:return:
	"""

	texttoclean = capitalletters(texttoclean)
	texttoclean = lowercaseletters(texttoclean)
	# combining dot
	texttoclean = re.sub(r'\?', u'\u0323', texttoclean)
	# exclmation point not properly documented
	texttoclean = re.sub(r'\!', u'\u2219', texttoclean)

	return texttoclean


def capitalletters(betacode):
	# needs to be done in order of length of regex string
	# capital + breathing + accent + adscript
	csga = re.compile(r'[*]\)\\\|([AHW])')
	crga = re.compile(r'[*]\(\\\|([AHW])')
	csaa = re.compile(r'[*]\)\/\|([AHW])')
	craa = re.compile(r'[*]\(\/\|([AHW])')
	csca = re.compile(r'[*]\(\=\|([AHW])')
	crca = re.compile(r'[*]\(\=\|([AHW])')

	unicode = re.sub(csga, capitalsmoothgraveadscript, betacode)
	unicode = re.sub(crga, capitalroughgraveadscript, unicode)
	unicode = re.sub(csaa, capitalsmoothacuteadscript, unicode)
	unicode = re.sub(craa, capitalroughacuteadscript, unicode)
	unicode = re.sub(csca, capitalsmoothcircumflexadscript, unicode)
	unicode = re.sub(crca, capitalroughcircumflexadscript, unicode)

	# capital + breathing + accent
	csg = re.compile(r'[*]\)\\([AEIOUHW])')
	crg = re.compile(r'[*]\(\\([AEIOUHW])')
	csa = re.compile(r'[*]\)\/([AEIOUHW])')
	cra = re.compile(r'[*]\(\/([AEIOUHW])')
	csc = re.compile(r'[*]\)\=([AEIOUHW])')
	crc = re.compile(r'[*]\(\=([AEIOUHW])')

	unicode = re.sub(csg, capitalsmoothgrave, unicode)
	unicode = re.sub(crg, capitalroughgrave, unicode)
	unicode = re.sub(csa, capitalsmoothacute, unicode)
	unicode = re.sub(cra, capitalroughacute, unicode)
	unicode = re.sub(csc, capitalsmoothcircumflex, unicode)
	unicode = re.sub(crc, capitalroughcircumflex, unicode)

	# capital + breathing
	cs = re.compile(r'[*]\)([AEIOUHWR])')
	cr = re.compile(r'[*]\(([AEIOUHWR])')

	unicode = re.sub(cs, capitalsmooth, unicode)
	unicode = re.sub(cr, capitalrough, unicode)

	# capital + accent
	cg = re.compile(r'[*]\\([AEIOUHW])')
	ca = re.compile(r'[*]\/([AEIOUHW])')

	unicode = re.sub(cg, capitalgrave, unicode)
	unicode = re.sub(ca, capitalacute, unicode)

	# capital + adscript
	cad = re.compile(r'[*]\|([AHW])')

	unicode = re.sub(cad, capitaladscript, unicode)

	# sigmas: all lunates
	sig = re.compile(r'[*]S[1-3]{0,1}')
	unicode = re.sub(sig, u'\u03f9', unicode)

	# capitals
	cap = re.compile(r'[*]([A-Z])')
	unicode = re.sub(cap, capitals, unicode)

	return unicode


# capital + breathing + accent + adscript
def capitalsmoothgraveadscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾊ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾚ',
		'W': u'ᾪ',
	}

	substitute = substitutions[val]

	return substitute


def capitalroughgraveadscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾋ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾛ',
		'W': u'ᾫ',
	}

	substitute = substitutions[val]

	return substitute


def capitalsmoothacuteadscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾌ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾜ',
		'W': u'ᾬ',
	}

	substitute = substitutions[val]

	return substitute


def capitalroughacuteadscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾍ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾝ',
		'W': u'ᾭ',
	}

	substitute = substitutions[val]

	return substitute


def capitalsmoothcircumflexadscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾎ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾞ',
		'W': u'ᾮ',
	}

	substitute = substitutions[val]

	return substitute


def capitalroughcircumflexadscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾏ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾟ',
		'W': u'ᾯ',
	}

	substitute = substitutions[val]

	return substitute


# capital + breathing + accent
def capitalsmoothgrave(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἂ',
		'E': u'Ἒ',
		'I': u'Ἲ',
		'O': u'Ὂ',
		'U': u'',
		'H': u'Ἢ',
		'W': u'Ὢ',
	}

	substitute = substitutions[val]

	return substitute


def capitalroughgrave(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἃ',
		'E': u'Ἓ',
		'I': u'Ἳ',
		'O': u'Ὃ',
		'U': u'Ὓ',
		'H': u'Ἣ',
		'W': u'Ὣ',
	}

	substitute = substitutions[val]

	return substitute


def capitalsmoothacute(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἄ',
		'E': u'Ἔ',
		'I': u'Ἴ',
		'O': u'Ὄ',
		'U': u'',
		'H': u'Ἤ',
		'W': u'Ὤ',
	}

	substitute = substitutions[val]

	return substitute


def capitalroughacute(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἅ',
		'E': u'Ἕ',
		'I': u'Ἵ',
		'O': u'Ὅ',
		'U': u'Ὕ',
		'H': u'Ἥ',
		'W': u'Ὥ',
	}

	substitute = substitutions[val]

	return substitute


def capitalsmoothcircumflex(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἆ',
		'E': u'',
		'I': u'Ἶ',
		'O': u'',
		'U': u'',
		'H': u'Ἦ',
		'W': u'Ὦ',
	}

	substitute = substitutions[val]

	return substitute


def capitalroughcircumflex(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἇ',
		'E': u'',
		'I': u'Ἷ',
		'O': u'',
		'U': u'Ὗ',
		'H': u'Ἧ',
		'W': u'Ὧ',
	}

	substitute = substitutions[val]

	return substitute


# capital + breathing
def capitalsmooth(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἀ',
		'E': u'Ἐ',
		'I': u'Ἰ',
		'O': u'Ὀ',
		'U': u'',
		'H': u'Ἠ',
		'W': u'Ὠ',
		'R': u'Ρ'
	}

	substitute = substitutions[val]

	return substitute


def capitalrough(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ἁ',
		'E': u'Ἑ',
		'I': u'Ἱ',
		'O': u'Ὁ',
		'U': u'Ὑ',
		'H': u'Ἡ',
		'W': u'Ὡ',
		'R': u'Ῥ'
	}

	substitute = substitutions[val]

	return substitute


# capital + accent
def capitalgrave(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ὰ',
		'E': u'Ὲ',
		'I': u'Ὶ',
		'O': u'Ὸ',
		'U': u'Ὺ',
		'H': u'Ὴ',
		'W': u'Ὼ',
	}

	substitute = substitutions[val]

	return substitute


def capitalacute(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Ά',
		'E': u'Έ',
		'I': u'Ί',
		'O': u'Ό',
		'U': u'Ύ',
		'H': u'Ή',
		'W': u'Ώ',
	}

	substitute = substitutions[val]

	return substitute


def capitaladscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾼ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ῌ',
		'W': u'ῼ',
	}

	substitute = substitutions[val]

	return substitute


def capitals(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'Α',
		'B': u'Β',
		'C': u'Ξ',
		'D': u'Δ',
		'E': u'Ε',
		'F': u'Φ',
		'G': u'Γ',
		'H': u'Η',
		'I': u'Ι',
		'J': u'⒣',
	# need the unused J because Roman characters are present; but see IG I3 1-2 [1-500 501-1517]) - 370: fr d-f, line 69 - Jέ[κτει Jεμέραι -- ⒣εμέραι is what we want
		'K': u'Κ',
		'L': u'Λ',
		'M': u'Μ',
		'N': u'Ν',
		'O': u'Ο',
		'P': u'Π',
		'Q': u'Θ',
		'R': u'Ρ',
		'S': u'Ϲ',
		'T': u'Τ',
		'U': u'Υ',
		'V': u'Ϝ',
		'W': u'Ω',
		'X': u'Χ',
		'Y': u'Ψ',
		'Z': u'Ζ'
	}

	substitute = substitutions[val]

	return substitute


def lowercaseletters(betacode):
	"""
	swap betacode for unicode values

	notice the problem that we can get with the papyri:
		μεμίϲθ(ωμαἰ ὡϲ πρόκ(ἐιται
		vs
		μεμίϲθ(ωμαι) ὡϲ πρόκ(ε)ιται

	the betacode knows how to prevent this:
		MEMI/SQ[1WMAI]1 W(S PRO/K[1E]1ITAI

	so you can't convert '[1' and ']1' into '(' and ')' before you get here

	:param betacode:
	:return:
	"""
	# needs to be done in order of length of regex string
	# otherwise 4-element items will disappear in the wake of doing all of the 3s, etc.

	# roman numeral problem: (XI) will wind up as (Xἰ
	# very had to fix because a lookahead of (?!\s) will ruin εἰ

	# lowercase + breathing + accent + subscript
	lsga = re.compile(r'([AHW])\)\\\|')
	lrga = re.compile(r'([AHW])\(\\\|')
	lsaa = re.compile(r'([AHW])\)\/\|')
	lraa = re.compile(r'([AHW])\(\/\|')
	lsca = re.compile(r'([AHW])\)\=\|')
	lrca = re.compile(r'([AHW])\(\=\|')

	unicode = re.sub(lsga, lowercasesmoothgravesubscript, betacode)
	unicode = re.sub(lrga, lowercaseroughgravesubscript, unicode)
	unicode = re.sub(lsaa, lowercasesmoothacutesubscript, unicode)
	unicode = re.sub(lraa, lowercaseroughacutesubscript, unicode)
	unicode = re.sub(lsca, lowercasesmoothcircumflexsubscript, unicode)
	unicode = re.sub(lrca, lowercaseroughcircumflexsubscript, unicode)

	# lowercase + breathing + accent
	lsg = re.compile(r'([AEIOUHW])\)\\')
	lrg = re.compile(r'([AEIOUHW])\(\\')
	lsa = re.compile(r'([AEIOUHW])\)\/')
	lra = re.compile(r'([AEIOUHW])\(\/')
	lsc = re.compile(r'([AEIOUHW])\)\=')
	lrc = re.compile(r'([AEIOUHW])\(\=')

	unicode = re.sub(lsg, lowercasesmoothgrave, unicode)
	unicode = re.sub(lrg, lowercaseroughgrave, unicode)
	unicode = re.sub(lsa, lowercasesmoothacute, unicode)
	unicode = re.sub(lra, lowercaseroughacute, unicode)
	unicode = re.sub(lsc, lowercasesmoothcircumflex, unicode)
	unicode = re.sub(lrc, lowercaseroughcircumflex, unicode)

	# lowercase + accent + subscript
	lga = re.compile(r'([AHW])\\\|')
	laa = re.compile(r'([AHW])\/\|')
	lca = re.compile(r'([AHW])\=\|')

	unicode = re.sub(lga, lowercasegravesub, unicode)
	unicode = re.sub(laa, lowercaseacutedsub, unicode)
	unicode = re.sub(lca, lowercasesircumflexsub, unicode)

	# lowercase + breathing + subscript
	lss = re.compile(r'([AHW])\)\|')
	lrs = re.compile(r'([AHW])\(\|')

	unicode = re.sub(lss, lowercasesmoothsub, unicode)
	unicode = re.sub(lrs, lowercaseroughsub, unicode)

	# lowercase + accent + diaresis
	lgd = re.compile(r'([IU])\\\+')
	lad = re.compile(r'([IU])\/\+')
	lcd = re.compile(r'([U])\=\+')

	unicode = re.sub(lgd, lowercasegravediaresis, unicode)
	unicode = re.sub(lad, lowercaseacutediaresis, unicode)
	unicode = re.sub(lcd, lowercasesircumflexdiaresis, unicode)

	# lowercase + breathing
	ls = re.compile(r'([AEIOUHWR])\)')
	lr = re.compile(r'([AEIOUHWR])\(')

	unicode = re.sub(ls, lowercasesmooth, unicode)
	unicode = re.sub(lr, lowercaserough, unicode)

	# lowercase + accent
	lg = re.compile(r'([AEIOUHW])\\')
	la = re.compile(r'([AEIOUHW])\/')
	lc = re.compile(r'([AEIOUHW])\=')

	unicode = re.sub(lg, lowercasegrave, unicode)
	unicode = re.sub(la, lowercaseacute, unicode)
	unicode = re.sub(lc, lowercascircumflex, unicode)

	# lowercase + diaresis
	ld = re.compile(r'([IU])\+')

	unicode = re.sub(ld, lowercasediaresis, unicode)

	# lowercase + subscript
	lad = re.compile(r'([AHW])\|')

	unicode = re.sub(lad, lowercasesubscript, unicode)

	# lowercase + vowel length
	# perseus' LSJ: vowel+_ for long-vowel and vowel+^ for short
	# short = re.compile(r'[AIU]\^')
	# long = re.compile(r'[AIU]_')

	# sigmas: all lunates
	sig = re.compile(r'S[1-3]{0,1}')
	unicode = re.sub(sig, u'ϲ', unicode)

	# lowercases
	lap = re.compile(r'([A-Z])')
	unicode = re.sub(lap, lowercases, unicode)

	return unicode


# lowercase + breathing + accent + subscript
def lowercasesmoothgravesubscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾂ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾒ',
		'W': u'ᾢ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseroughgravesubscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾃ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾓ',
		'W': u'ᾣ',
	}

	substitute = substitutions[val]

	return substitute


def lowercasesmoothacutesubscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾄ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾔ',
		'W': u'ᾤ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseroughacutesubscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾅ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾕ',
		'W': u'ᾥ',
	}

	substitute = substitutions[val]

	return substitute


def lowercasesmoothcircumflexsubscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾆ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾖ',
		'W': u'ᾦ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseroughcircumflexsubscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾇ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ᾗ',
		'W': u'ᾧ',
	}

	substitute = substitutions[val]

	return substitute


# lowercase + breathing + accent
def lowercasesmoothgrave(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἂ',
		'E': u'ἒ',
		'I': u'ἲ',
		'O': u'ὂ',
		'U': u'ὒ',
		'H': u'ἢ',
		'W': u'ὢ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseroughgrave(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἃ',
		'E': u'ἓ',
		'I': u'ἳ',
		'O': u'ὃ',
		'U': u'ὓ',
		'H': u'ἣ',
		'W': u'ὣ',
	}

	substitute = substitutions[val]

	return substitute


def lowercasesmoothacute(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἄ',
		'E': u'ἔ',
		'I': u'ἴ',
		'O': u'ὄ',
		'U': u'ὔ',
		'H': u'ἤ',
		'W': u'ὤ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseroughacute(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἅ',
		'E': u'ἕ',
		'I': u'ἵ',
		'O': u'ὅ',
		'U': u'ὕ',
		'H': u'ἥ',
		'W': u'ὥ',
	}

	substitute = substitutions[val]

	return substitute


def lowercasesmoothcircumflex(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἆ',
		'E': u'ἐ͂', # IG 104.27: AI)/TIOS E)=I FO/NO --> αἴτιος ἐ͂ι φόνο [U1f10 + U0342]
		'I': u'ἶ',
		'O': u'ὀ͂', # IG 127.36: E)PAINE/SAI W(S O)=SIN A)NDRA/SIN --> ἐπαινέσαι ὡς ὀ͂σιν ἀνδράσιν [U1f40 + U0342]
		'U': u'ὖ',
		'H': u'ἦ',
		'W': u'ὦ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseroughcircumflex(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἇ',
		'E': u'ἑ͂', # IG: TE=S BOLE=S E(=I
		'I': u'ἷ',
		'O': u'ὁ͂', # IG: PE]RI\ DE\ O(=[N !]DIK
		'U': u'ὗ',
		'H': u'ἧ',
		'W': u'ὧ',
	}

	substitute = substitutions[val]

	return substitute


# lowercase + accent + subscript
def lowercasegravesub(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾲ',
		'H': u'ῂ',
		'W': u'ῲ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseacutedsub(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾴ',
		'H': u'ῄ',
		'W': u'ῴ',
	}

	substitute = substitutions[val]

	return substitute


def lowercasesircumflexsub(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾷ',
		'H': u'ῇ',
		'W': u'ῷ',
	}

	substitute = substitutions[val]

	return substitute


# lowercase + breathing + subscript

def lowercasesmoothsub(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾀ',
		'H': u'ᾐ',
		'W': u'ᾠ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseroughsub(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾁ',
		'H': u'ᾑ',
		'W': u'ᾡ',
	}

	substitute = substitutions[val]

	return substitute


# lowercase + accent + diaresis
def lowercasegravediaresis(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ῒ',
		'O': u'',
		'U': u'ῢ',
		'H': u'',
		'W': u'',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseacutediaresis(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ΐ',
		'O': u'',
		'U': u'',
		'H': u'ΰ',
		'W': u'',
	}

	substitute = substitutions[val]

	return substitute


def lowercasesircumflexdiaresis(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'ῧ',
		'H': u'',
		'W': u'',
	}

	substitute = substitutions[val]

	return substitute


# lowercase + breathing
def lowercasesmooth(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἀ',
		'E': u'ἐ',
		'I': u'ἰ',
		'O': u'ὀ',
		'U': u'ὐ',
		'H': u'ἠ',
		'W': u'ὠ',
		'R': u'ῤ'
	}

	substitute = substitutions[val]

	return substitute


def lowercaserough(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ἁ',
		'E': u'ἑ',
		'I': u'ἱ',
		'O': u'ὁ',
		'U': u'ὑ',
		'H': u'ἡ',
		'W': u'ὡ',
		'R': u'ῥ'
	}

	substitute = substitutions[val]

	return substitute


# lowercase + accent
def lowercasegrave(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ὰ',
		'E': u'ὲ',
		'I': u'ὶ',
		'O': u'ὸ',
		'U': u'ὺ',
		'H': u'ὴ',
		'W': u'ὼ',
	}

	substitute = substitutions[val]

	return substitute


def lowercaseacute(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ά',
		'E': u'έ',
		'I': u'ί',
		'O': u'ό',
		'U': u'ύ',
		'H': u'ή',
		'W': u'ώ',
	}

	substitute = substitutions[val]

	return substitute


def lowercascircumflex(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾶ',
		'E': u'\u03b5\u0342',
		# epsilon-for-eta; see something like 1-500 501-1517, Attica (IG I3 1-2 [1-500 501-1517]) - 370: fr d-f, line 75
		'I': u'ῖ',
		'O': u'\u03bf\u0342',
		# to avoid blanking in a case of omicron-for-omega;  Attica (IG I3 1-2 [1-500 501-1517]) - 342: line 12; χρυϲο͂ν
		'U': u'ῦ',
		'H': u'ῆ',
		'W': u'ῶ',
	}

	substitute = substitutions[val]

	return substitute


# lowercase + diaresis
def lowercasediaresis(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'',
		'E': u'',
		'I': u'ϊ',
		'O': u'',
		'U': u'ϋ',
		'H': u'',
		'W': u'',
	}

	substitute = substitutions[val]

	return substitute


# lowercase + subscript
def lowercasesubscript(match, g=1):
	val = match.group(g)

	substitutions = {
		'A': u'ᾳ',
		'E': u'',
		'I': u'',
		'O': u'',
		'U': u'',
		'H': u'ῃ',
		'W': u'ῳ',
	}

	substitute = substitutions[val]

	return substitute


# lowercases
def lowercases(match, g=0):
	val = match.group(g)

	substitutions = {
		'A': u'α',
		'B': u'β',
		'C': u'ξ',
		'D': u'δ',
		'E': u'ε',
		'F': u'φ',
		'G': u'γ',
		'H': u'η',
		'I': u'ι',
		'J': u'⒣', # this is a divergence from HipparchiaBuilder's version; don't overwrite it
		'K': u'κ',
		'L': u'λ',
		'M': u'μ',
		'N': u'ν',
		'O': u'ο',
		'P': u'π',
		'Q': u'θ',
		'R': u'ρ',
		'S': u'ϲ',
		'T': u'τ',
		'U': u'υ',
		'V': u'ϝ',
		'W': u'ω',
		'X': u'χ',
		'Y': u'ψ',
		'Z': u'ζ'
	}

	substitute = substitutions[val]

	return substitute
