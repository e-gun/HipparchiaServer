# -*- coding: utf-8 -*-
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
hipparchia.run(debug = True, threaded=True)
