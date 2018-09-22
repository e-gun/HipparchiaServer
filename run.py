#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia

hipparchiaversion = '1.1.1+ [MASTER]'
print('\nVersion: {v}\n'.format(v=hipparchiaversion))

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

	# debug=True is considered to be a serious security hazard in a networked environment
	# if you are working on Hipparchia's code, you might be interested in this; otherwise there
	# are only bad reasons to set this to 'True'

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

	host = hipparchia.config['LISTENINGADDRESS']
	port = hipparchia.config['FLASKSERVEDFROMPORT']

	hipparchia.run(threaded=True, debug=False, host=host, port=port)
