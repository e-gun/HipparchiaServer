# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import os
from multiprocessing import current_process

from flask import Flask

from server import hipparchia
from server.formatting.miscformatting import consolewarning

nullapp = Flask('will_be_deleted_soon')

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
samplesettingsdir = os.path.join(here, 'sample_settings')
serverdir = os.path.normpath(os.path.join(here, '..'))


def startupprint(message: str, color='white', isbold=False, colorcoded=False, baremessage=True):
	# consolewarning(message: str, color='yellow', isbold=False, colorcoded=True, baremessage=False)
	if current_process().name == 'MainProcess':
		consolewarning(message, color, isbold, colorcoded, baremessage)
	return


if not os.path.exists(samplesettingsdir):
	startupprint('"sample_settings" directory not found: configuration check will fail', color='red')

for f in settingfiles:
	filepath = os.path.join(samplesettingsdir, f)
	try:
		nullapp.config.from_pyfile(filepath)
	except FileNotFoundError:
		startupprint('"./sample_settings/{f}" not found'.format(f=f), color='red')

sampleconfigdict = dict(nullapp.config)
del nullapp

if not os.path.exists(settingsdir):
	startupprint('"settings" directory not found; searching for old-style "config.py"', color='yellow')
	settingsfile = os.path.join(serverdir, 'config.py')
	try:
		hipparchia.config.from_pyfile(settingsfile)
	except FileNotFoundError:
		startupprint('could not find old-style "config.py"', color='yellow')
	startupprint('\tplease use the "sample_settings" folder to build a "settings" folder', color='yellow')
	startupprint('\tthere are likely to be new/different settings of which your old configuration is unaware\n', color='yellow')
	settingfiles = list()

for f in settingfiles:
	filepath = os.path.join(settingsdir, f)
	try:
		hipparchia.config.from_pyfile(filepath)
	except FileNotFoundError:
		startupprint('"./settings/{f}" not found; loading "{f}" from "sample_settings" instead'.format(f=f))
		sampledir = os.path.join(here, 'sample_settings')
		filepath = os.path.join(sampledir, f)
		hipparchia.config.from_pyfile(filepath)

missingkeys = sampleconfigdict.keys() - hipparchia.config.keys()
if missingkeys:
	mk = ', '.join(missingkeys)
	startupprint('WARNING: incomplete configuration; you are missing values for: {mk}\n'.format(mk=mk))
	startupprint('the following values were assigned via the defaults in the "sample_settings" files')
	for k in missingkeys:
		hipparchia.config[k] = sampleconfigdict[k]
		startupprint('\t{k} = {v}'.format(k=k, v=hipparchia.config[k]), color='yellow')

extrakeys = hipparchia.config.keys() - sampleconfigdict.keys()
if extrakeys:
	startupprint('WARNING: your configuration file contains more options than are available in "sample_settings"')
	startupprint('the following options are unrecognized:')
	for k in extrakeys:
		startupprint('\t{k}'.format(k=k), color='yellow')

# move to T/F over y/n

for k in hipparchia.config.keys():
	if hipparchia.config[k] == 'yes':
		hipparchia.config[k] = True
	if hipparchia.config[k] == 'no':
		hipparchia.config[k] = False
