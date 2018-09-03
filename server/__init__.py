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
serverdir = os.path.normpath(os.path.join(here, '..'))

if not os.path.exists(settingsdir):
	print('"settings" directory not found; searching for old-style "config.py"')
	settingsfile = os.path.join(serverdir, 'config.py')
	try:
		hipparchia.config.from_pyfile(settingsfile)
	except FileNotFoundError:
		print('could not find old-style "config.py"')
	print('\tplease use the "sample_settings" folder to build a "settings" folder')
	print('\tthere might be new/different settings of which your old configuration is unaware\n')
	settingfiles = list()

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
