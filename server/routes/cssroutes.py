# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import make_response

from server import hipparchia


@hipparchia.route('/css/<cssfile>', methods=['GET'])
def loadcssfile(cssfile):
	"""

	send the CSS, but insert config-based fonts, etc. into it first

	:return:
	"""

	# extremely unsafe to allow user to supply a path and cssfile should have been fed to the html template via config.py
	safefiles = ['hipparchiastyles.css', 'hardcodedstyles.css', 'custom.css']

	if cssfile not in safefiles:
		cssfile = safefiles[0]

	substitutes = ['DEFAULTFONT', 'DEFAULTNONGREEKFONT', 'DEFAULTGREEKFONT']

	with open(hipparchia.root_path+'/css/'+cssfile) as f:
		css = f.read()

	for s in substitutes:
		searchfor = re.compile('HIPPARCHIA'+s)
		css = re.sub(searchfor, hipparchia.config[s], css)

	# return send_from_directory('css', cssfile)

	response = make_response(css)
	response.headers.set('Content-Type', 'text/css')
	response.headers.set('Content-Disposition', 'attachment', filename=cssfile)

	return response

