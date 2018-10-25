# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from flask import session
from server import hipparchia


def preliminarycsssubstitutions(css, pickedfamily):


	return css


def gethostedfontdict():
	"""

	what we host

	:return:
	"""

	d = {'REGULAR': 'DejaVuSans',
	     'MONO': 'DejaVuSansMono',
	     'OBLIQUE': 'DejaVuSans-Oblique',
	     'CONDENSED': 'DejaVuSansCondensed',
	     'CNDENSEDBLD': 'DejaVuSansCondensed-Bold',
	     'BOLD': 'DejaVuSans-Bold',
	     'SEMIBLD': 'DejaVuSans-Bold',
	     'THIN': 'DejaVuSans-ExtraLight',
	     'LIGHT': 'DejaVuSans-ExtraLight',
	     'BLDITALIC': 'DejaVuSans-BoldOblique'}

	n = {'REGULAR': 'NotoSans-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'NotoSans-Italic',
	     'CONDENSED': 'NotoSansDisplay-Condensed',
	     'CNDENSEDBLD': 'NotoSansDisplay-CondensedBold',
	     'BOLD': 'NotoSans-Bold',
	     'SEMIBLD': 'NotoSansDisplay-SemiBold',
	     'THIN': 'NotoSansDisplay-Thin',
	     'LIGHT': 'NotoSansDisplay-Light',
	     'BLDITALIC': 'NotoSans-BoldItalic'}

	i = {'REGULAR': 'IBMPlexSans-Regular',
	     'MONO': 'IBMPlexMono-Regular',
	     'OBLIQUE': 'IBMPlexSans-Italic',
	     'CONDENSED': 'IBMPlexSansCondensed-Regular',
	     'CNDENSEDBLD': 'IBMPlexSansCondensed-Bold',
	     'BOLD': 'IBMPlexSans-Bold',
	     'SEMIBLD': 'IBMPlexSans-SemiBold',
	     'THIN': 'IBMPlexSans-Thin',
	     'LIGHT': 'IBMPlexSans-Light',
	     'BLDITALIC': 'IBMPlexSans-BoldItalic'}

	r = {'REGULAR': 'Roboto-Regular',
	     'MONO': 'RobotoMono-Medium',
	     'OBLIQUE': 'Roboto-Italic',
	     'CONDENSED': 'RobotoCondensed-Regular',
	     'CNDENSEDBLD': 'RobotoCondensed-Bold',
	     'BOLD': 'Roboto-Bold',
	     'SEMIBLD': 'Roboto-Bold',
	     'THIN': 'Roboto-Thin',
	     'LIGHT': 'Roboto-Light',
	     'BLDITALIC': 'Roboto-BoldItalic'}

	hostedfontdict = {'DejaVu': d, 'Noto': n, 'IBMPlex': i, 'Roboto': r}

	return hostedfontdict


def deface(csstext):
	"""

	pull out font face directives

	:param csstext:
	:return:
	"""

	fingerprint = re.compile(r"'hipparchia\w+',")
	re.sub(fingerprint, '', csstext)

	return csstext


def fontsforstyles(csstext):
	"""

	used Font-Bold.ttf to generate bold text

	:param csstext:
	:return:
	"""

	swaps = {
		r"font-stretch: condensed;\n\tfont-weight: bold;": "font-family: 'hipparchiacondensedboldstatic', sans-serif;",
		r"font-weight: bold;\n\tfont-stretch: condensed;": "font-family: 'hipparchiacondensedboldstatic', sans-serif;",
		r"font-style: italic;\n\tfont-weight: bold;": "font-family: 'hipparchiabolditalicstatic', sans-serif;",
		r"font-weight: bold;\n\tfont-style: italic;": "font-family: 'hipparchiabolditalicstatic', sans-serif;",
		r"font-style: italic;": "font-family: 'hipparchiaobliquestatic', sans-serif;",
		r"font-weight: bold;": "font-family: 'hipparchiaboldstatic', sans-serif;",
		r"font-weight: 600;": "font-family: 'hipparchiasemiboldstatic', sans-serif;",
	}

	for s in swaps.keys():
		csstext = re.sub(re.compile(s), swaps[s], csstext)

	return csstext