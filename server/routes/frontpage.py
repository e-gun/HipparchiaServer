# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import render_template, send_file, session

from server import hipparchia
from server.dbsupport.dbfunctions import versionchecking
from server.listsandsession.sessionfunctions import sessionvariables
from server.startup import listmapper


@hipparchia.route('/')
def frontpage():
	"""
	the front page
	it used to do stuff
	now it just loads the JS which then calls all of the routes

	:return:
	"""

	expectedsqltemplateversion = 6012017
	stylesheet = hipparchia.config['CSSSTYLESHEET']

	sessionvariables()

	# check to see which dbs we actually own
	activelists = [l for l in listmapper if len(listmapper[l]['a']) > 0]

	buildinfo = versionchecking(activelists, expectedsqltemplateversion)

	# check to see eith which dbs we search by default or are presently active
	activecorpora = [c for c in ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	                 if session[c] == 'yes']

	if hipparchia.config['AVOIDCIRCLEDLETTERS'] != 'yes':
		corporalabels = {'g': 'Ⓖ', 'l': 'Ⓛ', 'd': 'Ⓓ', 'i': 'Ⓘ', 'c': 'Ⓒ'}
	else:
		corporalabels = {'g': 'G', 'l': 'L', 'd': 'D', 'i': 'I', 'c': 'C'}

	page = render_template('search.html',activelists=activelists, activecorpora=activecorpora, clab=corporalabels, css=stylesheet,
	                       buildinfo=buildinfo, onehit=session['onehit'], hwindexing=session['headwordindexing'],
						   spuria=session['spuria'], varia=session['varia'], undated=session['incerta'])

	return page


@hipparchia.route('/favicon.ico')
def sendfavicon():
	return send_file('static/images/hipparchia_favicon.ico')


@hipparchia.route('/apple-touch-icon-precomposed.png')
def appletouchticon():
	return send_file('static/images/hipparchia_apple-touch-icon-precomposed.png')
