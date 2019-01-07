#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

# WARNING: DO NOT USE THIS SCRIPT IN A PRODUCTION SETTING
#   debug=True is considered to be a serious security hazard in a networked environment
#   it is assumed that a profiling run is a debugging run

from werkzeug.contrib.profiler import ProfilerMiddleware

from server import hipparchia

hipparchia.config['PROFILE'] = True
hipparchia.wsgi_app = ProfilerMiddleware(hipparchia.wsgi_app, restrictions=[25])

d = False

hipparchia.run(debug=d, threaded=True, host=hipparchia.config['LISTENINGADDRESS'], port=hipparchia.config['FLASKSERVEDFROMPORT'])
