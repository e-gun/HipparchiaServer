# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from os import name as osname
from platform import platform, python_version_tuple

from flask import Response as FlaskResponse
from flask import __version__ as flaskversion
from flask import render_template, send_file, session

from server import hipparchia
from server.commandlineoptions import getcommandlineargs
from server.compatability import dbversionchecking
from server.dbsupport.miscdbfunctions import getpostgresserverversion
from server.formatting.frontpagehtmlformatting import vectorhtmlforfrontpage, vectorhtmlforoptionsbar, \
	getsearchfieldbuttonshtml, getauthorholdingfieldhtml, getdaterangefieldhtml, getlexicafieldhtml
from server.hipparchiaobjects.authenticationobjects import LoginForm
from server.listsandsession.checksession import probeforsessionvariables
from server.startup import listmapper
from server.versioning import fetchhipparchiaserverversion, readgitdata
from versionconstants import RELEASE as release

JSON_STR = str
PAGE_STR = str

""""

set some variables at outer scope that both frontpage() and errorhandlingpage() will use 

"""

stylesheet = hipparchia.config['CSSSTYLESHEET']
# check to see which dbs we actually own
activelists = [l for l in listmapper if len(listmapper[l]['a']) > 0]
buildinfo = dbversionchecking(activelists)

psqlversion = getpostgresserverversion()
# Note that unlike the Python sys.version, the returned value will always include the patchlevel (it defaults to '0').
pythonversion = '.'.join(python_version_tuple())

theenvironment = """
Platform    {pf}
PostgreSQL  {ps}
Python      {py}
Flask       {fl}

WS          {ws}
Grabber     {gr}
IsActive	{ac}
via CLI     {gx}
Vectors     {vv}
"""

if hipparchia.config['EXTERNALWEBSOCKETS']:
	ws = hipparchia.config['EXTERNALBINARYNAME']
else:
	ws = 'python websockets'

if hipparchia.config['EXTERNALVECTORHELPER']:
	vv = 'w/ external assistance'
else:
	vv = 'pure python pipeline'

if hipparchia.config['EXTERNALGRABBER']:
	gx = hipparchia.config['GRABBERCALLEDVIACLI']
else:
	gx = '[Inactive]'


theenvironment = theenvironment.format(pf=platform(), ps=psqlversion, py=pythonversion, fl=flaskversion, ws=ws,
									   gr=hipparchia.config['EXTERNALBINARYNAME'], gx=gx,
									   ac=hipparchia.config['EXTERNALGRABBER'], vv=vv)

shortversion = fetchhipparchiaserverversion()
gitlength = 5
commit = readgitdata()
version = '{v} [git: {g}]'.format(v=fetchhipparchiaserverversion(), g=commit[:gitlength])

if not release:
	shortversion = version


"""

now define some routes...

"""


@hipparchia.route('/')
def frontpage() -> PAGE_STR:
	"""

	the front page. it used to do stuff; now it just loads the JS which then calls all of the routes:
	regular users never leave the front page
	the only other pages are basically debug pages as seen in debuggingroutes.py

	:return:
	"""

	probeforsessionvariables()

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

	loginform = None

	if hipparchia.config['LIMITACCESSTOLOGGEDINUSERS']:
		loginform = LoginForm()

	page = render_template('search.html',
						   activelists=activelists,
						   activecorpora=activecorpora,
						   clab=corporalabels,
						   css=stylesheet,
						   backend=theenvironment,
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
						   vectorhtml=vectorhtmlforfrontpage(),
						   vectoroptionshtml=vectorhtmlforoptionsbar(),
						   havevectors=havevectors,
						   version=version,
						   shortversion=shortversion,
						   searchfieldbuttons=getsearchfieldbuttonshtml(),
						   holdingshtml=getauthorholdingfieldhtml(),
						   datesearchinghtml=getdaterangefieldhtml(),
						   lexicalthml=getlexicafieldhtml(),
						   icanzap=icanzap,
						   loginform=loginform)

	return page


@hipparchia.route('/favicon.ico')
def sendfavicon() -> FlaskResponse:
	r = send_file('static/images/hipparchia_favicon.ico')
	return send_file('static/images/hipparchia_favicon.ico')


@hipparchia.route('/apple-touch-icon-precomposed.png')
def appletouchticon() -> FlaskResponse:
	return send_file('static/images/hipparchia_apple-touch-icon-precomposed.png')


@hipparchia.route('/robots.txt')
def robotstxt() -> FlaskResponse:
	blockall = 'User-Agent: *\nDisallow: /\n'
	r = FlaskResponse(response=blockall, status=200, mimetype='text/plain')
	r.headers['Content-Type'] = 'text/plain; charset=utf-8'
	return r


def errorhandlingpage(errornumber) -> PAGE_STR:
	"""

	generic error pages

	NB: not every field is used in every error page

	"""
	template = render_template('error{e}.html'.format(e=errornumber),
							   css=stylesheet,
							   backend=theenvironment,
							   buildinfo=buildinfo,
							   version=version,
							   shortversion=shortversion,
							   )
	return template


@hipparchia.errorhandler(400)
def badrequesterror(e) -> PAGE_STR:
	# but this can not ever be delivered because nginx or the flask middleware will barf first and send its 400 page
	return errorhandlingpage(400), 400


@hipparchia.errorhandler(404)
def pagenotfound(e) -> PAGE_STR:
	return errorhandlingpage(404), 404


@hipparchia.errorhandler(500)
def internalservererror(e) -> PAGE_STR:
	return errorhandlingpage(500), 500
