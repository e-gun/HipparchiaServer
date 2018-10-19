# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import make_response, session

from server import hipparchia
from server.listsandsession.sessionfunctions import probeforsessionvariables


@hipparchia.route('/css/<cssrequest>', methods=['GET'])
def loadcssfile(cssrequest):
	"""

	send the CSS, but insert config-based fonts, etc. into it first

	:return:
	"""

	probeforsessionvariables()

	# extremely unsafe to allow user to supply a path

	validcss = [hipparchia.config['CSSSTYLESHEET'], 'ldavis.css']

	cssfile = hipparchia.config['CSSSTYLESHEET']

	if cssrequest in validcss:
		cssfile = cssrequest

	substitutes = ['DEFAULTLOCALFONT', 'DEFAULTLOCALGREEKFONT', 'DEFAULTLOCALNONGREEKFONT']

	with open(hipparchia.root_path+'/css/'+cssfile) as f:
		css = f.read()

	if hipparchia.config['ENBALEFONTPICKER'] == 'yes':
		searchfor = re.compile('DEFAULTLOCALFONTWILLBESUPPLIEDFROMCONFIGFILE')
		css = re.sub(searchfor, session['fontchoice'], css)

	for s in substitutes:
		searchfor = re.compile(s+'WILLBESUPPLIEDFROMCONFIGFILE')
		css = re.sub(searchfor, hipparchia.config[s], css)

	d = {'REGULAR': 'DejaVuSans',
	     'MONO': 'DejaVuSansMono',
	     'OBLIQUE': 'DejaVuSans-Oblique',
	     'CONDENSED': 'DejaVuSansCondensed',
	     'CNDENSEDBLD': 'DejaVuSansCondensed-Bold',
	     'BOLD': 'DejaVuSans-Bold',
	     'SEMIBLD': 'DejaVuSans-Bold',
	     'THIN': 'DejaVuSans-ExtraLight',
	     'LIGHT': 'DejaVuSans-ExtraLight',
	     'BLDITALICLD': 'DejaVuSans-BoldOblique'}

	n = {'REGULAR': 'NotoSans-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'NotoSans-Italic',
	     'CONDENSED': 'NotoSansDisplay-Condensed',
	     'CNDENSEDBLD': 'NotoSansDisplay-CondensedBold',
	     'BOLD': 'NotoSans-Bold',
	     'SEMIBLD': 'NotoSansDisplay-SemiBold',
	     'THIN': 'NotoSansDisplay-Thin',
	     'LIGHT': 'NotoSansDisplay-Light',
	     'BLDITALICLD': 'NotoSans-BoldItalic'}

	i = {'REGULAR': 'IBMPlexSans-Regular',
	     'MONO': 'IBMPlexMono-Regular',
	     'OBLIQUE': 'IBMPlexSans-Italic',
	     'CONDENSED': 'IBMPlexSansCondensed-Regular',
	     'CNDENSEDBLD': 'IBMPlexSansCondensed-Bold',
	     'BOLD': 'IBMPlexSans-Bold',
	     'SEMIBLD': 'IBMPlexSans-SemiBold',
	     'THIN': 'IBMPlexSans-Thin',
	     'LIGHT': 'IBMPlexSans-Light',
	     'BLDITALICLD': 'IBMPlexSans-BoldItalic'}

	r = {'REGULAR': 'Roboto-Regular',
	     'MONO': 'RobotoMono-Medium',
	     'OBLIQUE': 'Roboto-Italic',
	     'CONDENSED': 'RobotoCondensed-Regular',
	     'CNDENSEDBLD': 'RobotoCondensed-Bold',
	     'BOLD': 'Roboto-Bold',
	     'SEMIBLD': 'Roboto-Bold',
	     'THIN': 'Roboto-Thin',
	     'LIGHT': 'Roboto-Light',
	     'BLDITALICLD': 'Roboto-BoldItalic'}

	hostedfontfamilies = {'DejaVu': d, 'Noto': n, 'IBMPlex': i, 'Roboto': r}

	if hipparchia.config['USEFONTFILESFORSTYLES'] == 'yes':
		forceface = True
	else:
		forceface = False

	try:
		family = hostedfontfamilies[hipparchia.config['HOSTEDFONTFAMILY']]
	except KeyError:
		forceface = False
		family = hostedfontfamilies['DejaVu']

	for face in family:
		searchfor = re.compile('HOSTEDFONTFAMILY_'+face)
		css = re.sub(searchfor, family[face], css)

	if forceface:
		swaps = {
			r"font-stretch: condensed;\n\tfont-weight: bold;":  "font-family: 'hipparchiacondensedboldstatic', sans-serif;",
			r"font-weight: bold;\n\tfont-stretch: condensed;": "font-family: 'hipparchiacondensedboldstatic', sans-serif;",
			r"font-style: italic;\n\tfont-weight: bold;": "font-family: 'hipparchiabolditalicstatic', sans-serif;",
			r"font-weight: bold;\n\tfont-style: italic;": "font-family: 'hipparchiabolditalicstatic', sans-serif;",
			r"font-style: italic;": "font-family: 'hipparchiaobliquestatic', sans-serif;",
			r"font-weight: bold;": "font-family: 'hipparchiaboldstatic', sans-serif;",
			r"font-weight: 600;": "font-family: 'hipparchiasemiboldstatic', sans-serif;",
		}
		for s in swaps.keys():
			css = re.sub(re.compile(s), swaps[s], css)

	# return send_from_directory('css', cssfile)

	response = make_response(css)
	response.headers.set('Content-Type', 'text/css')
	response.headers.set('Content-Disposition', 'attachment', filename=cssfile)

	return response
