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


class CssFormattingObject(object):

	d = {'REGULAR': 'DejaVuSans',
	     'MONO': 'DejaVuSansMono',
	     'OBLIQUE': 'DejaVuSans-Oblique',
	     'CONDENSED': 'DejaVuSansCondensed',
	     'CNDENSEDBLD': 'DejaVuSansCondensed-Bold',
	     'CNDENSEDOBL': 'DejaVuSansCondensed-Oblique',
	     'BOLD': 'DejaVuSans-Bold',
	     'SEMIBLD': 'DejaVuSans-Bold',
	     'THIN': 'DejaVuSans-ExtraLight',
	     'LIGHT': 'DejaVuSans-ExtraLight',
	     'BLDITALIC': 'DejaVuSans-BoldOblique'}

	f = {'REGULAR': 'FiraSans-Regular',
	     'MONO': 'FiraMono-Regular',
	     'OBLIQUE': 'FiraSans-Italic',
	     'CONDENSED': 'FiraSans-Thin',
	     'CNDENSEDBLD': 'FiraSans-Bold',
	     'CNDENSEDOBL': 'FiraSans-ThinItalic',
	     'BOLD': 'FiraSans-Bold',
	     'SEMIBLD': 'FiraSans-Bold',
	     'THIN': 'FiraSans-ExtraLight',
	     'LIGHT': 'FiraSans-ExtraLight',
	     'BLDITALIC': 'FiraSans-BoldItalic'}

	i = {'REGULAR': 'IBMPlexSans-Regular',
	     'MONO': 'IBMPlexMono-Regular',
	     'OBLIQUE': 'IBMPlexSans-Italic',
	     'CONDENSED': 'IBMPlexSansCondensed-Regular',
	     'CNDENSEDBLD': 'IBMPlexSansCondensed-Bold',
	     'CNDENSEDOBL': 'IBMPlexSansCondensed-Italic',
	     'BOLD': 'IBMPlexSans-Bold',
	     'SEMIBLD': 'IBMPlexSans-SemiBold',
	     'THIN': 'IBMPlexSans-Thin',
	     'LIGHT': 'IBMPlexSans-Light',
	     'BLDITALIC': 'IBMPlexSans-BoldItalic'}

	n = {'REGULAR': 'NotoSans-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'NotoSans-Italic',
	     'CONDENSED': 'NotoSansDisplay-Condensed',
	     'CNDENSEDBLD': 'NotoSansDisplay-CondensedBold',
	     'CNDENSEDOBL': 'NotoSansDisplay-CondensedItalic',
	     'BOLD': 'NotoSans-Bold',
	     'SEMIBLD': 'NotoSansDisplay-SemiBold',
	     'THIN': 'NotoSansDisplay-Thin',
	     'LIGHT': 'NotoSansDisplay-Light',
	     'BLDITALIC': 'NotoSans-BoldItalic'}

	r = {'REGULAR': 'Roboto-Regular',
	     'MONO': 'RobotoMono-Medium',
	     'OBLIQUE': 'Roboto-Italic',
	     'CONDENSED': 'RobotoCondensed-Regular',
	     'CNDENSEDBLD': 'RobotoCondensed-Bold',
	     'CNDENSEDOBL': 'RobotoCondensed-Italic',
	     'BOLD': 'Roboto-Bold',
	     'SEMIBLD': 'Roboto-Bold',
	     'THIN': 'Roboto-Thin',
	     'LIGHT': 'Roboto-Light',
	     'BLDITALIC': 'Roboto-BoldItalic'}

	def __init__(self, originalcss):
		self.css = originalcss
		self.substitutes = ['DEFAULTLOCALFONT', 'DEFAULTLOCALGREEKFONT', 'DEFAULTLOCALNONGREEKFONT']
		self.hostedfontdict = {
			'DejaVu': CssFormattingObject.d,
			'Fira': CssFormattingObject.f,
			'IBMPlex': CssFormattingObject.i,
			'Noto': CssFormattingObject.n,
			'Roboto': CssFormattingObject.r
		}
		self.faces = dict()
		self.knownface = True
		if hipparchia.config['ENBALEFONTPICKER'] == 'yes':
			self.pickerinuse = True
			self.pickedfamily = session['fontchoice']
		else:
			self.pickerinuse = False
			self.pickedfamily = hipparchia.config['HOSTEDFONTFAMILY']

	def runcleaningsuite(self):
		self._pickerswaps()
		self._determineface()
		self._swapface()
		self._swapdefaults()
		self._fontsforstyles()

	def _determineface(self):
		try:
			self.faces = self.hostedfontdict[self.pickedfamily]
		except KeyError:
			self._deface()
			self.knownface = False

	def _swapface(self):
		for face in self.faces:
			searchfor = re.compile('HOSTEDFONTFAMILY_'+face)
			self.css = re.sub(searchfor, self.faces[face], self.css)

	def _deface(self):
		fingerprint = re.compile(r"'hipparchia\w+',")
		re.sub(fingerprint, '', self.css)

	def _swapdefaults(self):
		for s in self.substitutes:
			searchfor = re.compile(s + 'WILLBESUPPLIEDFROMCONFIGFILE')
			self.css = re.sub(searchfor, hipparchia.config[s], self.css)

	def _pickerswaps(self):
		if self.pickerinuse:
			searchfor = re.compile('DEFAULTLOCALFONTWILLBESUPPLIEDFROMCONFIGFILE')
			self.css = re.sub(searchfor, self.pickedfamily, self.css)
			self._deface()

	def _fontsforstyles(self):
		"""

		used Font-Bold.ttf to generate bold text, etc

		:param csstext:
		:return:
		"""

		if hipparchia.config['USEFONTFILESFORSTYLES'] != 'yes':
			return

		if not self.knownface:
			return

		# need this to run in order
		swaps = [
			(r"font-stretch: condensed; font-weight: bold;", "font-family: 'hipparchiacondensedboldstatic', sans-serif;"),
			(r"font-weight: bold; font-stretch: condensed;", "font-family: 'hipparchiacondensedboldstatic', sans-serif;"),
			(r"font-stretch: condensed; font-style: italic;", "font-family: 'hipparchiacondenseditalicstatic', sans-serif;"),
			(r"font-style: italic; font-stretch: condensed;", "font-family: 'hipparchiacondenseditalicstatic', sans-serif;"),
			(r"font-style: italic; font-weight: bold;", "font-family: 'hipparchiabolditalicstatic', sans-serif;"),
			(r"font-weight: bold; font-style: italic;", "font-family: 'hipparchiabolditalicstatic', sans-serif;"),
			(r"font-style: italic;", "font-family: 'hipparchiaobliquestatic', sans-serif;"),
			(r"font-weight: bold;", "font-family: 'hipparchiaboldstatic', sans-serif;"),
			(r"font-weight: 600;", "font-family: 'hipparchiasemiboldstatic', sans-serif;"),
			(r"font-stretch: condensed;", "font-family: 'hipparchiacondensedstatic', sans-serif;")
		]

		for s in swaps:
			self.css = re.sub(re.compile(s[0]), s[1], self.css)
