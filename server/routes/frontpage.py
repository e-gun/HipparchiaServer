# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
from os import path
from sys import argv

from flask import render_template, send_file, session

from server import hipparchia
from server.dbsupport.miscdbfunctions import versionchecking
from server.formatting.vectorformatting import vectorhtmlforfrontpage
from server.listsandsession.sessionfunctions import probeforsessionvariables
from server.startup import listmapper


@hipparchia.route('/')
def frontpage():
	"""
	the front page
	it used to do stuff
	now it just loads the JS which then calls all of the routes

	:return:
	"""

	probeforsessionvariables()

	expectedsqltemplateversion = 2242018
	stylesheet = hipparchia.config['CSSSTYLESHEET']
	fonts = hipparchia.config['FONTPICKERLIST']
	fonts.sort()
	if fonts:
		picker = hipparchia.config['ENBALEFONTPICKER']
	else:
		# anythong other then 'yes' disables the picker
		picker = 'nofontstopick'

	debugpanel = hipparchia.config['ALLOWUSERTOSETDEBUGMODES']

	vectorhtml = vectorhtmlforfrontpage()

	# check to see which dbs we actually own
	activelists = [l for l in listmapper if len(listmapper[l]['a']) > 0]

	buildinfo = versionchecking(activelists, expectedsqltemplateversion)

	# check to see eith which dbs we search by default or are presently active
	activecorpora = [c for c in ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	                 if session[c] == 'yes']

	if hipparchia.config['AVOIDCIRCLEDLETTERS'] != 'yes':
		corporalabels = {'g': 'Ⓖ', 'l': 'Ⓛ', 'd': 'Ⓓ', 'i': 'Ⓘ', 'c': 'Ⓒ'}
	elif hipparchia.config['FALLBACKTODOUBLESTRIKES'] == 'yes':
		corporalabels = {'g': '𝔾', 'l': '𝕃', 'd': '𝔻', 'i': '𝕀', 'c': 'ℂ'}
	else:
		corporalabels = {'g': 'G', 'l': 'L', 'd': 'D', 'i': 'I', 'c': 'C'}

	page = render_template('search.html',
							activelists=activelists,
							activecorpora=activecorpora,
							clab=corporalabels,
							css=stylesheet,
							buildinfo=buildinfo,
							onehit=session['onehit'],
							picker=picker,
							fonts=fonts,
							hwindexing=session['headwordindexing'],
							indexbyfrequency=session['indexbyfrequency'],
							spuria=session['spuria'],
							varia=session['varia'],
							undated=session['incerta'],
							debug=debugpanel,
							vectorhtml=vectorhtml)

	return page


@hipparchia.route('/favicon.ico')
def sendfavicon():
	return send_file('static/images/hipparchia_favicon.ico')


@hipparchia.route('/apple-touch-icon-precomposed.png')
def appletouchticon():
	return send_file('static/images/hipparchia_apple-touch-icon-precomposed.png')


@hipparchia.route('/loadhelpdata')
def loadhelpdata():
	"""

	do not load the help html until someone clicks on the '?' button

	then send this stuff

	:return:
	"""

	currentpath = path.dirname(argv[0])
	helppath = currentpath + '/server/helpfiles/'
	divmapper = {'Interface': 'helpinterface.html',
					'Browsing': 'helpbrowsing.html',
					'Dictionaries': 'helpdictionaries.html',
					'MakingSearchLists': 'helpsearchlists.html',
					'BasicSyntax': 'helpbasicsyntax.html',
					'RegexSearching': 'helpregex.html',
					'SpeedSearching': 'helpspeed.html',
					'LemmaSearching': 'helplemmata.html',
					'VectorSearching': 'helpvectors.html',
					'Oddities': 'helpoddities.html',
					'Extending': 'helpextending.html',
					'Openness': 'helpopenness.html'}

	helpdict = dict()
	helpdict['helpcategories'] = list(divmapper.keys())

	for d in divmapper:
		helpfilepath = helppath+divmapper[d]
		helpcontents = ''
		if path.isfile(helpfilepath):
			with open(helpfilepath, encoding='utf8') as f:
				helpcontents = f.read()
		helpdict[d] = helpcontents

	helpdict = json.dumps(helpdict)
	
	return helpdict
