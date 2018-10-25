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
from server.formatting.cssformatting import deface, fontsforstyles, gethostedfontdict
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

	with open(hipparchia.root_path+'/css/'+cssfile, encoding='utf8') as f:
		css = f.read()

	substitutes = ['DEFAULTLOCALFONT', 'DEFAULTLOCALGREEKFONT', 'DEFAULTLOCALNONGREEKFONT']
	for s in substitutes:
		searchfor = re.compile(s+'WILLBESUPPLIEDFROMCONFIGFILE')
		css = re.sub(searchfor, hipparchia.config[s], css)

	pickedfamily = None
	if hipparchia.config['ENBALEFONTPICKER'] == 'yes':
		pickedfamily = session['fontchoice']
		searchfor = re.compile('DEFAULTLOCALFONTWILLBESUPPLIEDFROMCONFIGFILE')
		css = re.sub(searchfor, pickedfamily, css)

	hostedfontfamilies = gethostedfontdict()

	if not pickedfamily:
		pickedfamily = hipparchia.config['HOSTEDFONTFAMILY']

	try:
		faces = hostedfontfamilies[pickedfamily]
	except KeyError:
		faces = dict()
		css = deface(css)

	for face in faces:
		searchfor = re.compile('HOSTEDFONTFAMILY_'+face)
		css = re.sub(searchfor, faces[face], css)

	if hipparchia.config['USEFONTFILESFORSTYLES'] == 'yes':
		css = fontsforstyles(css)

	# return send_from_directory('css', cssfile)

	response = make_response(css)
	response.headers.set('Content-Type', 'text/css')
	response.headers.set('Content-Disposition', 'attachment', filename=cssfile)

	return response
