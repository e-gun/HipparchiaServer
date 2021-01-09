# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import Dict, List


def loadconfig(filepath) -> list:
	"""
	simple simon: a read of the file to prepare it for the  parse
	:param filepath:
	:return: configlist
	"""

	configlist = list()

	with open(filepath) as f:
		for line in f:
			configlist.append(line)

	return configlist


def parseconfig(configlist) -> List[str]:
	"""
	generate a list of config options contained in the configlist

	:param configlist:
	:return:
	"""
	findconfig = re.compile(r'^[A-Z]+')

	configvariablelist = list()
	for c in configlist:
		configvar = re.search(findconfig, c)
		try:
			configvariablelist.append(configvar.group(0))
		except:
			pass

	return configvariablelist


def compareconfigs(template, model) -> Dict[str, set]:
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

	differencedict = {'missing': missing, 'extra': extra}

	return differencedict
