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
hipparchia.wsgi_app = ProfilerMiddleware(hipparchia.wsgi_app, restrictions=[30])

# debug=True is considered to be a serious security hazard in a networked environment
# if you are working on Hipparchia's code, you might be interested in this; otherwise there
# are only bad reasons to set this to 'True'

# it is assumed that a profiling run is a debugging run
# do not use this script in a production setting...

hipparchia.run(debug=True, threaded=True)
