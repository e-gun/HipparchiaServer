#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from multiprocessing import current_process

from click import secho
from werkzeug.contrib.profiler import ProfilerMiddleware

from version import hipparchiaserverversion as hipparchiaversion

if current_process().name == 'MainProcess':
	# stupid Windows will fork new copies and reload all of this
	vstring = """
	{banner}
	 {v}
	{banner}
	"""
	v = 'HipparchiaServer v{v}'.format(v=hipparchiaversion)
	banner = ''.join('=' for _ in range(len(v)+2))
	secho(vstring.format(banner=banner, v=v, s=''), bold=True, fg='cyan')

from server import hipparchia
from server.commandlineoptions import getcommandlineargs

if __name__ == '__main__':

	if hipparchia.config['ENABLELOGGING'] == 'yes':
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

	"""
	sometimes ^C will not kill every thread and you will still have an open server port
	this will leave you unable to restart without rebooting: 'socket already in use'
	you need to find the process that is holding the port open and kill it
	for example
	
	less fancy:
	
		$ ps ax | grep ipparchia | grep run.py
		$ kill -15 >>THEPID<<
	
	>>THEPID<< == 11980 in the following
	
		11980 s007  S+     0:40.40 /usr/local/Cellar/python/3.7.0/Frameworks/Python.framework/Versions/3.7/Resources/Python.app/Contents/MacOS/Python /Users/erik/hipparchia_venv/HipparchiaServer/run.py
	
	"more fancy" requires using lsof...
	
	"""

	commandlineargs = getcommandlineargs()

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
