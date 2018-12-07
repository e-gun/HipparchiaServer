# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import make_response

from server import hipparchia
from server.hipparchiaobjects.cssformattingobject import CssFormattingObject
from server.listsandsession.checksession import probeforsessionvariables


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

	cfo = CssFormattingObject(css)
	cfo.runcleaningsuite()
	css = cfo.css

	# return send_from_directory('css', cssfile)

	response = make_response(css)
	response.headers.set('Content-Type', 'text/css')
	response.headers.set('Content-Disposition', 'attachment', filename=cssfile)

	return response
