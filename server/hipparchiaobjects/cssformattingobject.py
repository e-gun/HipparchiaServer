# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server import hipparchia


class CssFormattingObject(object):
	a = {'REGULAR': 'Alegreya-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'Alegreya-Italic',
	     'CONDENSED': 'AlegreyaSC-Regular',
	     'CNDENSEDBLD': 'AlegreyaSC-Bold',
	     'CNDENSEDOBL': 'AlegreyaSC-Italic',
	     'BOLD': 'Alegreya-Bold',
	     'SEMIBLD': 'Alegreya-Medium',
	     'THIN': 'Alegreya-Regular',
	     'LIGHT': 'Alegreya-Regular',
	     'BLDITALIC': 'Alegreya-BoldItalic'}

	c = {'REGULAR': 'cmunss',
	     'MONO': 'cmunbtl',
	     'OBLIQUE': 'cmunsi',
	     'CONDENSED': False,
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': False,
	     'BOLD': 'cmunsx',
	     'SEMIBLD': 'cmunbsr',
	     'THIN': False,
	     'LIGHT': False,
	     'BLDITALIC': 'cmunso'}

	cx = {'REGULAR': 'cmunrm',
	     'MONO': 'cmunbtl',
	     'OBLIQUE': 'cmunti',
	     'CONDENSED': False,
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': False,
	     'BOLD': 'cmunbx',
	     'SEMIBLD': 'cmunrb',
	     'THIN': False,
	     'LIGHT': False,
	     'BLDITALIC': 'cmunbi'}

	d = {'REGULAR': 'DejaVuSans',
	     'MONO': 'DejaVuSansMono',
	     'OBLIQUE': 'DejaVuSans-Oblique',
	     'CONDENSED': 'DejaVuSansCondensed',
	     'CNDENSEDBLD': 'DejaVuSansCondensed-Bold',
	     'CNDENSEDOBL': 'DejaVuSansCondensed-Oblique',
	     'BOLD': 'DejaVuSans-Bold',
	     'SEMIBLD': False,
	     'THIN': False,
	     'LIGHT': 'DejaVuSans-ExtraLight',
	     'BLDITALIC': 'DejaVuSans-BoldOblique'}

	dx = {'REGULAR': 'DejaVuSerif',
	     'MONO': 'DejaVuSansMono',
	     'OBLIQUE': 'DejaVuSerif-Italic',
	     'CONDENSED': 'DejaVuSerifCondensed',
	     'CNDENSEDBLD': 'DejaVuSerifCondensed-Bold',
	     'CNDENSEDOBL': 'DejaVuSerifCondensed-Italic',
	     'BOLD': 'DejaVuSerif-Bold',
	     'SEMIBLD': False,
	     'THIN': False,
	     'LIGHT': False,
	     'BLDITALIC': 'DejaVuSerif-BoldItalic'}

	f = {'REGULAR': 'FiraSans-Regular',
	     'MONO': 'FiraMono-Regular',
	     'OBLIQUE': 'FiraSans-Italic',
	     'CONDENSED': 'FiraSans-Thin',
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': 'FiraSans-ThinItalic',
	     'BOLD': 'FiraSans-Bold',
	     'SEMIBLD': False,
	     'THIN': False,
	     'LIGHT': 'FiraSans-ExtraLight',
	     'BLDITALIC': 'FiraSans-BoldItalic'}

	g = {'REGULAR': 'EBGaramond-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'EBGaramond-Italic',
	     'CONDENSED': False,
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': False,
	     'BOLD': 'EBGaramond-SemiBold',
	     'SEMIBLD': False,
	     'THIN': False,
	     'LIGHT': False,
	     'BLDITALIC': 'EBGaramond-SemiBoldItalic'}

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

	ix = {'REGULAR': 'IBMPlexSerif-Regular',
	     'MONO': 'IBMPlexMono-Regular',
	     'OBLIQUE': 'IBMPlexSerif-Italic',
	     'CONDENSED': False,
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': False,
	     'BOLD': 'IBMPlexSerif-Bold',
	     'SEMIBLD': 'IBMPlexSerif-SemiBold',
	     'THIN': 'IBMPlexSerif-Thin',
	     'LIGHT': 'IBMPlexSerif-Light',
	     'BLDITALIC': 'IBMPlexSerif-BoldItalic'}

	l = {'REGULAR': 'Lato-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'Lato-Italic',
	     'CONDENSED': False,
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': False,
	     'BOLD': 'Lato-Bold',
	     'SEMIBLD': 'Lato-SemiBold',
	     'THIN': 'Lato-Thin',
	     'LIGHT': 'Lato-Hairline',
	     'BLDITALIC': 'Lato-BoldItalic'}

	n = {'REGULAR': 'NotoSans-Regular',
	     'MONO': 'NotoSansMono-Regular',
	     'OBLIQUE': 'NotoSans-Italic',
	     'CONDENSED': 'NotoSansDisplay_ExtraCondensed-Regular',
	     'CNDENSEDBLD': 'NotoSansDisplay_ExtraCondensed-SemiBold',
	     'CNDENSEDOBL': 'NotoSansDisplay_ExtraCondensed-Italic',
	     'BOLD': 'NotoSans-Bold',
	     'SEMIBLD': 'NotoSans-SemiBold',
	     'THIN': 'NotoSans-Thin',
	     'LIGHT': 'NotoSans-ExtraLight',
	     'BLDITALIC': 'NotoSans-BoldItalic'}

	nd = {'REGULAR': 'NotoSansDisplay-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'NotoSansDisplay-Italic',
	     'CONDENSED': 'NotoSansDisplay-Condensed',
	     'CNDENSEDBLD': 'NotoSansDisplay-CondensedBold',
	     'CNDENSEDOBL': 'NotoSansDisplay-CondensedItalic',
	     'BOLD': 'NotoSansDisplay-Bold',
	     'SEMIBLD': 'NotoSansDisplay-SemiBold',
	     'THIN': 'NotoSansDisplay-Thin',
	     'LIGHT': 'NotoSansDisplay-Light',
	     'BLDITALIC': 'NotoSansDisplay-BoldItalic'}

	nu = {'REGULAR': 'NotoSansUI-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'NotoSansUI-Italic',
	     'CONDENSED': 'NotoSansDisplay-Condensed',
	     'CNDENSEDBLD': 'NotoSansDisplay-CondensedBold',
	     'CNDENSEDOBL': 'NotoSansDisplay-CondensedItalic',
	     'BOLD': 'NotoSansUI-Bold',
	     'SEMIBLD': 'NotoSansDisplay-SemiBold',
	     'THIN': 'NotoSansDisplay-Thin',
	     'LIGHT': 'NotoSansDisplay-Light',
	     'BLDITALIC': 'NotoSansUI-BoldItalic'}

	# too many missing glyphs
	o = {'REGULAR': 'OpenSans-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'OpenSans-Italic',
	     'CONDENSED': 'OpenSansCondensed-Light',
	     'CNDENSEDBLD': 'OpenSansCondensed-Bold',
	     'CNDENSEDOBL': 'OpenSansCondensed-LightItalic',
	     'BOLD': 'OpenSans-Bold',
	     'SEMIBLD': 'OpenSans-SemiBold',
	     'THIN': False,
	     'LIGHT': 'OpenSans-Light',
	     'BLDITALIC': 'OpenSans-BoldItalic'}

	r = {'REGULAR': 'Roboto-Regular',
	     'MONO': 'RobotoMono-Medium',
	     'OBLIQUE': 'Roboto-Italic',
	     'CONDENSED': 'RobotoCondensed-Regular',
	     'CNDENSEDBLD': 'RobotoCondensed-Bold',
	     'CNDENSEDOBL': 'RobotoCondensed-Italic',
	     'BOLD': 'Roboto-Bold',
	     'SEMIBLD': False,
	     'THIN': 'Roboto-Thin',
	     'LIGHT': 'Roboto-Light',
	     'BLDITALIC': 'Roboto-BoldItalic'}

	# too many missing glyphs when you get to oblique greek
	s = {'REGULAR': 'SourceSansPro-Regular',
	     'MONO': 'SourceCodePro-Regular',
	     'OBLIQUE': 'SourceSansPro-It',
	     'CONDENSED': False,
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': False,
	     'BOLD': 'SourceSansPro-Bold',
	     'SEMIBLD': 'SourceSansPro-Bold',
	     'THIN': False,
	     'LIGHT': 'SourceSansPro-Light',
	     'BLDITALIC': 'SourceSansPro-BoldIt'}

	u = {'REGULAR': 'Ubuntu-R',
	     'MONO': 'UbuntuMono-R',
	     'OBLIQUE': 'Ubuntu-RI',
	     'CONDENSED': 'Ubuntu-C',
	     'CNDENSEDBLD': False,
	     'CNDENSEDOBL': 'Ubuntu-RI',
	     'BOLD': 'Ubuntu-B',
	     'SEMIBLD': 'Ubuntu-M',
	     'THIN': False,
	     'LIGHT': 'Ubuntu-L',
	     'BLDITALIC': 'Ubuntu-BI'}

	def __init__(self, originalcss):
		self.css = originalcss
		self.substitutes = ['DEFAULTLOCALFONT', 'DEFAULTLOCALGREEKFONT', 'DEFAULTLOCALNONGREEKFONT']
		self.hostedfontdict = {
			'Alegreya': CssFormattingObject.a,
			'CMUSans': CssFormattingObject.c,
			'CMUSerif': CssFormattingObject.cx,
			'DejaVuSans': CssFormattingObject.d,
			'DejaVuSerif': CssFormattingObject.dx,
			'Fira': CssFormattingObject.f,
			'EBGaramond': CssFormattingObject.g,
			'IBMPlex': CssFormattingObject.i,
			'Lato': CssFormattingObject.l,
			'Noto': CssFormattingObject.n,
			'Roboto': CssFormattingObject.r,
			'Ubuntu': CssFormattingObject.u,
			# Defective:
			# 'IBMPlexSerif': CssFormattingObject.ix,
			# These only seem complete: they are missing plenty...
			# 'Open Sans': CssFormattingObject.o,
			# 'SourceSans': CssFormattingObject.s
		}
		self.faces = dict()
		self.knownface = True
		if hipparchia.config['ENBALEFONTPICKER']:
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
		# self._invertcolors()
		self._colorless()

	def _colorless(self):
		if session['suppresscolors']:
			# kill - "color: var(--red);"
			# save - "background-color: var(--main-body-color);"
			self.css = re.sub(r'(?<!-)color: var\(--(.*?)\)', 'color: var(--black)', self.css)

	def _invertcolors(self):
		hslfinder = re.compile(r'hsla\((\d+), (\d+)%, (\d+)%')
		self.css = re.sub(hslfinder, self.colorinversion, self.css)

	@staticmethod
	def colorinversion(regexmatch):
		template = 'hsla({h}, {s}%, {b}%'
		hue = int(regexmatch.group(1))
		sat = int(regexmatch.group(2))
		brt = int(regexmatch.group(3))

		if hue > 180:
			newhue = hue - 180
		else:
			newhue = 180 - hue

		# compress sat span since 0 is just grey
		dist = 50 - sat
		newsat = 50 + dist
		if newsat < 5:
			newsat = 5

		dist = 50 - brt
		newbrt = 50 + dist

		inverted = template.format(h=newhue, s=newsat, b=newbrt)

		return inverted

	def _determineface(self):
		try:
			self.faces = self.hostedfontdict[self.pickedfamily]
		except KeyError:
			self._deface()
			self.knownface = False

	def _swapface(self):
		for face in self.faces:
			if self.faces[face]:
				searchfor = re.compile('HOSTEDFONTFAMILY_'+face)
				self.css = re.sub(searchfor, self.faces[face], self.css)

	def _deface(self):
		fingerprint = re.compile(r"'hipparchia\w+',")
		re.sub(fingerprint, '', self.css)

	def _swapdefaults(self):
		for s in self.substitutes:
			searchfor = re.compile(s + 'WILLBESUPPLIEDFROMCONFIGFILE')
			swap = '"{f}"'.format(f=hipparchia.config[s])
			self.css = re.sub(searchfor, swap, self.css)

	def _pickerswaps(self):
		if self.pickerinuse:
			searchfor = re.compile('DEFAULTLOCALFONTWILLBESUPPLIEDFROMCONFIGFILE')
			swap = '"{f}"'.format(f=self.pickedfamily)
			self.css = re.sub(searchfor, swap, self.css)
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

		# need this to run in order, so can't use a dict()
		# [(findpattern1, replace1), ...]

		swaps = [
			('CNDENSEDBLD', r"font-stretch: condensed; font-weight: bold;", "font-family: 'hipparchiacondensedboldstatic', sans-serif;"),
			('CNDENSEDBLD', r"font-weight: bold; font-stretch: condensed;", "font-family: 'hipparchiacondensedboldstatic', sans-serif;"),
			('CNDENSEDOBL', r"font-stretch: condensed; font-style: italic;", "font-family: 'hipparchiacondenseditalicstatic', sans-serif;"),
			('CNDENSEDOBL', r"font-style: italic; font-stretch: condensed;", "font-family: 'hipparchiacondenseditalicstatic', sans-serif;"),
			('BLDITALIC', r"font-style: italic; font-weight: bold;", "font-family: 'hipparchiabolditalicstatic', sans-serif;"),
			('BLDITALIC', r"font-weight: bold; font-style: italic;", "font-family: 'hipparchiabolditalicstatic', sans-serif;"),
			('OBLIQUE', r"font-style: italic;", "font-family: 'hipparchiaobliquestatic', sans-serif;"),
			('BOLD', r"font-weight: bold;", "font-family: 'hipparchiaboldstatic', sans-serif;"),
			('SEMIBLD', r"font-weight: 600;", "font-family: 'hipparchiasemiboldstatic', sans-serif;"),
			('CONDENSED', r"font-stretch: condensed;", "font-family: 'hipparchiacondensedstatic', sans-serif;"),
			('REGULAR', r"font-style: normal;", "font-family: 'hipparchiasansstatic', sans-serif;")
		]

		for s in swaps:
			if self.faces[s[0]]:
				self.css = re.sub(re.compile(s[1]), s[2], self.css)
