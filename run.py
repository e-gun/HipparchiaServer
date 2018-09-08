#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia

hipparchiaversion = '1.1.0+ [MASTER]'
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
	
	# lsof | grep pyth | grep 5000
	
	python3.6 53249 hipparchia   23u    PIPE 0xfffff8017e2e5000              16384        ->0xfffff8017e2e5168
	python3.6 77379 hipparchia   23u    PIPE 0xfffff8017e2e5000              16384        ->0xfffff8017e2e5168
	python3.6 78871 hipparchia   23u    PIPE 0xfffff8017e2e5000              16384        ->0xfffff8017e2e5168
	python3.6 78871 hipparchia   36u    PIPE 0xfffff8004ee15000              16384        ->0xfffff8004ee15168

	# kill -15 53249 77379 78871
	
	"""

	hipparchia.run(threaded=True, debug=False, host=hipparchia.config['LISTENINGADDRESS'], port=hipparchia.config['FLASKSERVEDFROMPORT'])
