#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import multiprocessing

try:
	from rich.traceback import install as installtracebackhandler
except ImportError:
	installtracebackhandler = None

if installtracebackhandler:
	installtracebackhandler()

from click import secho

try:
	# DeprecationWarning: 'werkzeug.contrib.profiler' has moved to'werkzeug.middleware.profiler'.
	# This import is deprecated as ofversion 0.15 and will be removed in version 1.0.
	from werkzeug.middleware.profiler import ProfilerMiddleware
except ImportError:
	# maybe you have an older version of werkzeug...
	from werkzeug.contrib.profiler import ProfilerMiddleware

from server.versioning import fetchhipparchiaserverversion
from server.versioning import readgitdata

# if multiprocessing.current_process().name == 'MainProcess':
# 	# stupid Windows will fork new copies and reload all of this
# 	vstring = """
# 	{banner}
# 	  {v}
# 	  {g}
# 	{banner}
# 	"""
# 	v = 'HipparchiaServer v{v}'.format(v=fetchhipparchiaserverversion())
# 	c = readgitdata()
# 	t = len(v) - len('[git: ]')
# 	c = c[:t]
# 	g = '[git: {c}]'.format(c=c)
# 	# p = ''.join(' ' for _ in range(pad))
# 	banner = str().join('=' for _ in range(len(g)+4))
# 	secho(vstring.format(banner=banner, v=v, g=g), bold=True, fg='cyan')

from server import hipparchia
from server.commandlineoptions import getcommandlineargs
from server.compatability import checkcompatability

if __name__ == '__main__':

	# this code block duplicates material found in '__init__.py'; the only gain is the secho() notification so that
	# you know where you stand at startup

	secho('multiprocessing method set by OS default to: {m}'.format(m=multiprocessing.get_start_method()), fg='cyan')

	if hipparchia.config['ENABLELOGGING']:
		from inspect import stack
		from os import path
		import logging
		here = stack()[-1][1]
		thisdir = path.dirname(here)
		logger = logging.getLogger('werkzeug')
		handler = logging.FileHandler('{ld}/{lf}'.format(ld=thisdir, lf=hipparchia.config['HIPPARCHIALOGFILE']))
		logger.addHandler(handler)

		# Also add the handler to Flask's logger for cases
		#  where Werkzeug isn't used as the underlying WSGI server.
		hipparchia.logger.addHandler(handler)

	commandlineargs = getcommandlineargs()
	checkcompatability()

	host = hipparchia.config['LISTENINGADDRESS']

	if not commandlineargs.portoverride:
		port = hipparchia.config['FLASKSERVEDFROMPORT']
	else:
		port = commandlineargs.portoverride

	if commandlineargs.profiling:
		hipparchia.wsgi_app = ProfilerMiddleware(hipparchia.wsgi_app, restrictions=[25])

	# debug=True is a *serious* security hazard in a networked environment
	# if you are working on Hipparchia's code, you might be interested in this; otherwise there
	# are only bad reasons to set this to 'True'

	hipparchia.run(threaded=True, debug=False, host=host, port=port)
