# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import redirect, session, url_for

from server import hipparchia
from server.dbsupport.vectordbfunctions import createstoredimagestable, createvectorstable


@hipparchia.route('/resetsession')
def clearsession():
	"""
	clear the session
	this will reset all settings and reload the front page
	:return:
	"""

	session.clear()

	return redirect(url_for('frontpage'))


@hipparchia.route('/resetvectors')
def resetsemanticvectors():
	"""

	empty out the vectors table

	then reload the front page

	:return:
	"""

	createvectorstable()

	return redirect(url_for('frontpage'))


@hipparchia.route('/resetvectorimages')
def resetvectorgraphs():
	"""

	empty out the vector images table

	then reload the front page

	:return:
	"""

	createstoredimagestable()

	return redirect(url_for('frontpage'))
