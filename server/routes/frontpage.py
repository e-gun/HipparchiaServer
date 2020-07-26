# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
from os import name as osname
from os import path
from platform import platform, python_version_tuple
from sys import argv

from flask import __version__ as flaskversion
from flask import render_template, send_file, session

from server import hipparchia
from server.commandlineoptions import getcommandlineargs
from server.dbsupport.dbbuildinfo import versionchecking
from server.dbsupport.miscdbfunctions import getpostgresserverversion
from server.formatting.vectorformatting import vectorhtmlforfrontpage, vectorhtmlforoptionsbar
from server.hipparchiaobjects.authenticationobjects import LoginForm
from server.listsandsession.checksession import probeforsessionvariables
from server.startup import listmapper
from version import devel, hipparchiaserverversion, readgitdata


@hipparchia.route('/')
def frontpage():
	"""
	the front page
	it used to do stuff
	now it just loads the JS which then calls all of the routes

	:return:
	"""

	probeforsessionvariables()

	expectedsqltemplateversion = 10082019

	stylesheet = hipparchia.config['CSSSTYLESHEET']

	fonts = hipparchia.config['FONTPICKERLIST']
	fonts.sort()
	if fonts:
		picker = hipparchia.config['ENBALEFONTPICKER']
	else:
		picker = False

	debugpanel = hipparchia.config['ALLOWUSERTOSETDEBUGMODES']

	commandlineargs = getcommandlineargs()
	if commandlineargs.enabledebugui:
		debugpanel = True

	havevectors = hipparchia.config['SEMANTICVECTORSENABLED']

	vectorhtml = vectorhtmlforfrontpage()
	vectoroptionshtml = vectorhtmlforoptionsbar()

	# check to see which dbs we actually own
	activelists = [l for l in listmapper if len(listmapper[l]['a']) > 0]

	buildinfo = versionchecking(activelists, expectedsqltemplateversion)
	psqlversion = getpostgresserverversion()
	# Note that unlike the Python sys.version, the returned value will always include the patchlevel (it defaults to '0').
	pythonversion = '.'.join(python_version_tuple())

	backend = """
	Platform    {pf}
	PostgreSQL  {ps}
	Python      {py}
	Flask       {fl}
	"""

	backend = backend.format(pf=platform(), ps=psqlversion, py=pythonversion, fl=flaskversion)

	knowncorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']

	# check to see eith which dbs we search by default or are presently active
	activecorpora = [c for c in knowncorpora if session[c]]

	if not hipparchia.config['AVOIDCIRCLEDLETTERS']:
		corporalabels = {'g': 'Ⓖ', 'l': 'Ⓛ', 'd': 'Ⓓ', 'i': 'Ⓘ', 'c': 'Ⓒ'}
	elif hipparchia.config['FALLBACKTODOUBLESTRIKES']:
		corporalabels = {'g': '𝔾', 'l': '𝕃', 'd': '𝔻', 'i': '𝕀', 'c': 'ℂ'}
	else:
		corporalabels = {'g': 'G', 'l': 'L', 'd': 'D', 'i': 'I', 'c': 'C'}

	icanzap = 'yes'
	if osname == 'nt':
		# windows can't have the UI σ/ς option because it can't fork()
		# the 'fix' is to have frozensession always available when building a dbWorkLine
		# but that involves a lot kludge just to make a very optional option work
		icanzap = 'no'

	gitlength = 5
	commit = readgitdata()
	version = '{v} [git: {g}]'.format(v=hipparchiaserverversion, g=commit[:gitlength])

	shortversion = hipparchiaserverversion

	if devel:
		shortversion = version

	loginform = None

	if hipparchia.config['LIMITACCESSTOLOGGEDINUSERS']:
		loginform = LoginForm()

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
							vectorhtml=vectorhtml,
							vectoroptionshtml=vectoroptionshtml,
							havevectors=havevectors,
							version=version,
							shortversion=shortversion,
							backend=backend,
							icanzap=icanzap,
							loginform=loginform)

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

	if not hipparchia.config['EXTERNALWSGI']:
		currentpath = path.dirname(argv[0])
	else:
		# path.dirname(argv[0]) = /home/hipparchia/hipparchia_venv/bin
		currentpath = path.abspath(hipparchia.config['HARDCODEDPATH'])

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
					'IncludedMaterials': 'includedmaterials.html',
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
