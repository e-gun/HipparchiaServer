# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re


def andsubstitutes(match):
	"""
	turn &NN...& into unicode

	needed for inset notations, etc

	try to keep this in sync with what we have in HipparchiaBuilder

	:param match:
	:return:
	"""

	val = int(match.group(1))
	core = match.group(2)

	# the next bit is all you really need to sync with HipparchiaBuilder
	substitutions = {
		91: [r'<hmu_fontshift_latin_undocumentedfontshift_AND91>', r'</hmu_fontshift_latin_undocumentedfontshift_AND91>'],
		90: [r'<hmu_fontshift_latin_undocumentedfontshift_AND90>', r'</hmu_fontshift_latin_undocumentedfontshift_AND90>'],
		82: [r'<hmu_fontshift_latin_undocumentedfontshift_AND82>', r'</hmu_fontshift_latin_undocumentedfontshift_AND82>'],
		81: [r'<hmu_fontshift_latin_undocumentedfontshift_AND81>', r'</hmu_fontshift_latin_undocumentedfontshift_AND81>'],
		20: [r'<hmu_fontshift_latin_largerthannormal>', r'</hmu_fontshift_latin_largerthannormal>'],
		14: [r'<hmu_fontshift_latin_smallerthannormal_superscript>', r'</hmu_fontshift_latin_smallerthannormal_superscript>'],
		13: [r'<hmu_fontshift_latin_smallerthannormal_italic>', r'</hmu_fontshift_latin_smallerthannormal_italic>'],
		10: [r'<hmu_fontshift_latin_smallerthannormal>', r'</hmu_fontshift_latin_smallerthannormal>'],
		9: [r'<hmu_fontshift_latin_normal>', r'</hmu_fontshift_latin_normal>'],
		8: [r'<hmu_fontshift_latin_smallcapitals_italic>', r'</hmu_fontshift_latin_smallcapitals_italic>'],
		7: [r'<hmu_fontshift_latin_smallcapitals>', r'</hmu_fontshift_latin_smallcapitals>'],
		6: [r'<hmu_fontshift_latin_romannumerals>', r'</hmu_fontshift_latin_romannumerals>'],
		5: [r'<hmu_fontshift_latin_subscript>', r'</hmu_fontshift_latin_subscript>'],
		4: [r'<hmu_fontshift_latin_superscript>', r'</hmu_fontshift_latin_superscript>'],
		3: [r'<hmu_fontshift_latin_italic>', r'</hmu_fontshift_latin_italic>'],
		2: [r'<hmu_fontshift_latin_bold_italic>', r'</hmu_fontshift_latin_bold_italic>'],
		1: [r'<hmu_fontshift_latin_bold>', r'</hmu_fontshift_latin_bold>'],
		0: [r'<hmu_fontshift_latin_normal>', r'</hmu_fontshift_latin_normal>'],
	}

	try:
		one = re.sub(r'hmu_fontshift_latin_', '', substitutions[val][0])
		two = re.sub(r'hmu_fontshift_latin_', '', substitutions[val][1])
		substitute = one + core + two
	except KeyError:
		substitute = '<hmu_unhandled_latin_font_shift betacodeval="{v}" />{c}'.format(v=val, c=core)

	return substitute
