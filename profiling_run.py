#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from werkzeug.contrib.profiler import ProfilerMiddleware

from server import hipparchia

hipparchia.config['PROFILE'] = True
hipparchia.wsgi_app = ProfilerMiddleware(hipparchia.wsgi_app, restrictions=[20])

d = False

# WARNING:
#   debug=True is considered to be a serious security hazard in a networked environment
#   it is assumed that a profiling run is a debugging run; DO NOT USE THIS SCRIPT IN A PRODUCTION SETTING

hipparchia.run(debug=d, threaded=True)
