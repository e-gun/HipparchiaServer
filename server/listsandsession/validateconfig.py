# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import os
import re

def loadconfig(filepath):
	"""
	simple simon: a read of the file to prepare it for the  parse
	:param filepath:
	:return: configlist
	"""

	configlist = []

	with open(filepath) as f:
		for line in f:
			configlist.append(line)

	return configlist


def parseconfig(configlist):
	"""
	generate a list of config options contained in the configlist

	:param configlist:
	:return:
	"""
	findconfig = re.compile(r'^[A-Z]{1,}')

	configvariablelist = []
	for c in configlist:
		configvar = re.search(findconfig, c)
		try:
			configvariablelist.append(configvar.group(0))
		except:
			pass

	return configvariablelist


def compareconfigs(template, model):
	"""

	compare the options on offer in one list to those on offer in a second list

	return a dictionary of the differences

	:param template:
	:param model:
	:return:
	"""
	sample = parseconfig(loadconfig(template))
	active = parseconfig(loadconfig(model))

	missing = set(sample) - set(active)
	extra = set(active) - set(sample)

	differencedict = { 'missing': missing, 'extra': extra }

	return differencedict


dir_path = os.path.dirname(os.path.realpath(__file__))
relativeshift='/../..'
testresults = compareconfigs(dir_path + relativeshift + '/sample_config.py', dir_path + relativeshift + '/config.py')

if len(testresults['missing']) > 0:
	print('\n\nWARNING -- WARNING -- WARNING\n')
	print('Hipparchia is almost certain to crash. If you are lucky it will merely spew error messages.')
	print('Your configuration file ("config.py") needs to assign a value to the following:\n')
	for m in testresults['missing']:
		print('\t', m)
	print('\nSee "sample_config.py" in the HipparchiaServer directory.\n\n')

if len(testresults['extra']) > 0:
	print('\n\nWARNING -- WARNING -- WARNING\n')
	print('Your active configuration contains items that are not in the template:\n')
	for e in testresults['extra']:
		print('\t', e)
	print('\nThese items are being ignored. Consider consulting "sample_config.py" in the HipparchiaServer directory.\n\n')
