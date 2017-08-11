#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia

if __name__ == '__main__':

	if hipparchia.config['ENABLELOGGING'] == 'yes':
		from inspect import stack
		from os import path
		import logging
		here = stack()[-1][1]
		thisdir = path.dirname(here)
		logger = logging.getLogger('werkzeug')
		handler = logging.FileHandler('{h}/{l}'.format(h=thisdir, l=hipparchia.config['HIPPARCHIALOGFILE']))
		logger.addHandler(handler)

		# Also add the handler to Flask's logger for cases
		#  where Werkzeug isn't used as the underlying WSGI server.
		hipparchia.logger.addHandler(handler)

	# debug=True is considered to be a serious security hazard in a networked environment
	# if you are working on Hipparchia's code, you might be interested in this; otherwise there
	# are only bad reasons to set this to 'True'

	hipparchia.run(threaded=True, debug=False, host=hipparchia.config['LISTENINGADDRESS'], port=hipparchia.config['FLASKSERVEDFROMPORT'])
