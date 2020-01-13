# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import Flask

hipparchia = Flask(__name__)

from server import configureatstartup
from server import startup
from server.routes import browseroute, frontpage, getterroutes, hintroutes, inforoutes, lexicalroutes, searchroute, \
	selectionroutes, textandindexroutes, websocketroutes, resetroutes, cssroutes
if hipparchia.config['AUTOVECTORIZE']:
	from server.threading import vectordbautopilot
