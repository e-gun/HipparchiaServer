# -*- coding: utf-8 -*-
from flask import Flask

hipparchia = Flask(__name__)
hipparchia.config.from_object('config')

from server import startup
from server.routes import browseroute, frontpage, getterroutes, hintroutes, inforoutes, lexicalroutes, searchroute, \
	selectionroutes, textandindexroutes, websocketroutes, resetroutes

