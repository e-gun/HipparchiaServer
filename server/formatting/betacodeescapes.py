# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

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

	substitutions = {
		91: [r'<hmu_undocumented_font_shift_AND91>',r'</hmu_undocumented_font_shift_AND91>'],
		90: [r'<hmu_undocumented_font_shift_AND90>', r'</hmu_undocumented_font_shift_AND90>'],
		82: [r'<hmu_undocumented_font_shift_AND82>', r'</hmu_undocumented_font_shift_AND82>'],
		81: [r'<hmu_undocumented_font_shift_AND81>', r'</hmu_undocumented_font_shift_AND81>'],
		20: [r'<span class="largerthannormal">',r'</span>'],
		14: [r'<span class="smallerthannormalsuperscript">',r'</span>'],
		13: [r'<span class="smallerthannormalitalic">', r'</span>'],
		10: [r'<span class="smallerthannormal">', r'</span>'],
		9: [r'<span class="normal">', r'</span>'],
		8: [r'<span class="smallcapitalsitalic">', r'</span>'],
		7: [r'<span class="smallcapitals">', r'</span>'],
		6: [r'<span class="romannumerals">', r'</span>'],
		5: [r'<span class="subscript">', r'</span>'],
		4: [r'<span class="superscript">', r'</span>'],
		3: [r'<span class="italic">', r'</span>'],
		2: [r'<span class="bolditalic">', r'</span>'],
		1: [r'<span class="bold">', r'</span>'],
	}

	try:
		substitute = substitutions[val][0] + core + substitutions[val][1]
	except KeyError:
		substitute = '<hmu_unhandled_latin_font_shift betacodeval="{v}" />{c}'.format(v=val, c=core)

	return substitute