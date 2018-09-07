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


@hipparchia.route('/css/<cssrequest>', methods=['GET'])
def loadcssfile(cssrequest):
	"""

	send the CSS, but insert config-based fonts, etc. into it first

	:return:
	"""

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
	     'BOLD': 'DejaVuSans-Bold',
	     'THIN': 'DejaVuSans-ExtraLight',
	     'LIGHT': 'DejaVuSans-ExtraLight'}

	n = {'REGULAR': 'NotoSans-Regular',
	     'MONO': 'NotoMono-Regular',
	     'OBLIQUE': 'NotoSans-Italic',
	     'CONDENSED': 'NotoSansDisplay-Condensed',
	     'BOLD': 'NotoSans-Bold',
	     'THIN': 'NotoSansDisplay-Thin',
	     'LIGHT': 'NotoSansDisplay-Light'}

	i = {'REGULAR': 'IBMPlexSans-Regular',
	     'MONO': 'IBMPlexMono-Regular',
	     'OBLIQUE': 'IBMPlexSans-Italic',
	     'CONDENSED': 'IBMPlexSansCondensed-Regular',
	     'BOLD': 'IBMPlexSans-Bold',
	     'THIN': 'IBMPlexSans-Thin',
	     'LIGHT': 'IBMPlexSans-Light'}

	r = {'REGULAR': 'Roboto-Regular',
	     'MONO': 'RobotoMono-Medium',
	     'OBLIQUE': 'Roboto-Italic',
	     'CONDENSED': 'RobotoCondensed-Regular',
	     'BOLD': 'Roboto-Bold',
	     'THIN': 'Roboto-Thin',
	     'LIGHT': 'Roboto-Light'}

	hostedfontfamilies = {'DejaVu': d, 'Noto': n, 'IBMPlex': i, 'Roboto': r}

	try:
		family = hostedfontfamilies[hipparchia.config['HOSTEDFONTFAMILY']]
	except KeyError:
		family = hostedfontfamilies['DejaVu']

	for face in family:
		searchfor = re.compile('HOSTEDFONTFAMILY_'+face)
		css = re.sub(searchfor, family[face], css)

	# return send_from_directory('css', cssfile)

	response = make_response(css)
	response.headers.set('Content-Type', 'text/css')
	response.headers.set('Content-Disposition', 'attachment', filename=cssfile)

	return response
