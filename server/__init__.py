# -*- coding: utf-8 -*-
from flask import Flask

hipparchia = Flask(__name__)

from server import configureatstartup
from server import startup
from server.routes import browseroute, frontpage, getterroutes, hintroutes, inforoutes, lexicalroutes, searchroute, \
	selectionroutes, textandindexroutes, websocketroutes, resetroutes, cssroutes
if hipparchia.config['AUTOVECTORIZE'] == 'yes':
	from server.threading import vectordbautopilot
