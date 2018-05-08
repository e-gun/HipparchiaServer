# -*- coding: utf-8 -*-
from flask import Flask
import os

hipparchia = Flask(__name__)

settingfiles = {'debugsettings.py',
		'defaultsessionvalues.py',
		'generaldisplaysettings.py',
		'htmlandcssstylesettings.py',
		'inputsettings.py',
		'networksettings.py',
		'performancesettings.py',
		'securitysettings.py',
		'semanticvectorsettings.py'}

here = os.path.dirname(os.path.realpath(__file__))
settingsdir = os.path.join(here, 'settings')

if not os.path.exists(settingsdir):
	print('"settings" directory not found; using "sample_settings" instead')
	settingsdir = os.path.join(here, 'sample_settings')

for f in settingfiles:
	filepath = os.path.join(settingsdir, f)
	try:
		hipparchia.config.from_pyfile(filepath)
	except FileNotFoundError:
		print('"./settings/{f}" not found; loading "{f}" from "sample_settings" instead'.format(f=f))
		sampledir = os.path.join(here, 'sample_settings')
		filepath = os.path.join(sampledir, f)
		hipparchia.config.from_pyfile(filepath)

from server import startup
from server.routes import browseroute, frontpage, getterroutes, hintroutes, inforoutes, lexicalroutes, searchroute, \
	selectionroutes, textandindexroutes, websocketroutes, resetroutes, cssroutes
from server.threading import vectordbautopilot
