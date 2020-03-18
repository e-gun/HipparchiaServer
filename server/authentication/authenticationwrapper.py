# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
	(see LICENSE in the top level directory of the distribution)
"""

import json

from flask import session

from server import hipparchia


def requireauthentication(routefunction):
	"""

	do we need to limit access at all?

	if so, check session to see if we are logged in; if not, require a login

	multiple wrapped routes gives you this problem:
		File "/Users/erik/hipparchia_venv/lib/python3.7/site-packages/flask/app.py", line 1283, in add_url_rule
		"existing endpoint function: %s" % endpoint
		AssertionError: View function mapping is overwriting an existing endpoint function: wrapper

	hence the name reset:
		wrapper.__name__ = wrappername

	:param routefunction:
	:return:
	"""

	try:
		session['loggedin']
	except KeyError:
		session['loggedin'] = False
	except RuntimeError:
		# RuntimeError: Working outside of request context.
		# an issue at startup
		pass

	wrappername = routefunction.__name__

	injectjs = """
		$('#validateusers').dialog( "open" );
	"""

	htmlresults = """
	<br>
	you are not logged in
	<br>
	please log in and try again
	<br>
	"""

	indexmakeritems = ['authorname', 'title', 'structure', 'worksegment', 'elapsed', 'wordsfound', 'indexhtml', 'keytoworks', 'newjs']
	textmakeritems = ['authorname', 'title', 'structure', 'worksegment', 'texthtml']
	browseritems = ['browseforwards', 'browseback', 'authornumber', 'workid', 'authorboxcontents', 'workboxcontents', 'browserhtml', 'worknumber']
	searchitems = ['title', 'searchsummary', 'found', 'image', 'js', 'htmlsearch', 'thesearch']
	itemsweuse = set(textmakeritems + browseritems + searchitems + indexmakeritems)
	outputdict = {i: str() for i in itemsweuse}

	def wrapper(*args, **kwargs):
		if session['loggedin'] or not hipparchia.config['LIMITACCESSTOLOGGEDINUSERS']:
			return routefunction(*args, **kwargs)
		else:
			outputdict['title'] = 'not logged in'
			outputdict['searchsummary'] = htmlresults
			outputdict['browserhtml'] = htmlresults
			outputdict['indexhtml'] = htmlresults
			outputdict['js'] = injectjs
			outputdict['newjs'] = '<script>{js}</script>'.format(js=injectjs)
			jsonoutput = json.dumps(outputdict)
			return jsonoutput

	wrapper.__name__ = wrappername

	return wrapper