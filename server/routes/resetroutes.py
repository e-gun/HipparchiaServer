# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import redirect, session, url_for
from flask import Response as FlaskResponse

from server import hipparchia
from server.dbsupport.vectordbfunctions import createstoredimagestable, createvectorstable


@hipparchia.route('/reset/<item>')
def resetroute(item) -> FlaskResponse:
	"""

	reset some item and then load the front page

	"""

	resetter = {'session': lambda: session.clear(),
					'vectors': lambda: createvectorstable(),
					'vectorimages': lambda: createstoredimagestable()}

	blockable = ['vectors', 'vectorimages']

	if item not in resetter:
		return redirect(url_for('frontpage'))

	if item in blockable:
		amblocked = hipparchia.config['BLOCKRESETPATHS']
	else:
		amblocked = False

	if not amblocked:
		resetter[item]()

	return redirect(url_for('frontpage'))
