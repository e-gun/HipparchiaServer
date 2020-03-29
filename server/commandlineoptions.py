# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import argparse
from sys import argv


def getcommandlineargs():
	"""

	what, if anything, was passed to "run.py"?

	gunicorn can't be allowed near this since it wants command line arguments...

	:return:
	"""

	if 'run.py' in argv[0]:
		commandlineparser = argparse.ArgumentParser(description='script used to launch HipparchiaServer')
		exclusivegroup = commandlineparser.add_mutually_exclusive_group()

		commandlineparser.add_argument('--dbhost', required=False, type=str, help='[debugging] override the config file database host address')
		commandlineparser.add_argument('--dbname', required=False, type=str, help='[debugging] override the config file database name')
		commandlineparser.add_argument('--dbport', required=False, type=int, help='[debugging] override the config file database listening port')
		commandlineparser.add_argument('--enabledebugui', action='store_true', help='[debugging] forcibly enable the web debug UI')
		commandlineparser.add_argument('--portoverride', required=False, type=int, help='[debugging] override the config file listening port')
		commandlineparser.add_argument('--profiling', action='store_true', help='[debugging] enable the profiler')
		commandlineparser.add_argument('--skiplemma', action='store_true', help='[debugging] use empty lemmatadict for fast startup (some functions will be lost)')
		commandlineparser.add_argument('--disablevectorbot', action='store_true', help='[force setting] disable the vectorbot for this run')
		commandlineparser.add_argument('--forceuniversalbetacode', action='store_true', help='[force setting] all input on the search line will be parsed as betacode')
		commandlineparser.add_argument('--forcefont', required=False, type=str, help='[force setting] assign a value to DEFAULTLOCALFONT; "MyFont Sans" requires quotation marks to handle the space in the name')
		exclusivegroup.add_argument('--pooledconnection', action='store_true', help='[force setting] force a pooled DB connection')
		exclusivegroup.add_argument('--simpleconnection', action='store_true', help='[force setting] force a simple DB connection')
		commandlineparser.add_argument('--threadcount', required=False, type=int, help='[force setting] override the config file threadcount')
		commandlineparser.add_argument('--calculatewordweights', action='store_true', help='[info] generate word weight info')
		commandlineparser.add_argument('--collapsedgenreweights', action='store_true', help='[info] generate word weight info & merge related genres ("allret", etc.)')

		commandlineargs = commandlineparser.parse_args()

	else:
		# 'gunicorn'
		# WARNING: gunicorn cannot use the vectorbot
		commandlineargs = argparse.Namespace(calculatewordweights=False,
		                                     collapsedgenreweights=False,
		                                     dbhost=None,
		                                     dbname=None,
		                                     dbport=None,
		                                     disablevectorbot=True,
		                                     enabledebugui=None,
		                                     forcefont=None,
		                                     forceuniversalbetacode=None,
		                                     pooledconnection=None,
		                                     portoverride=None,
		                                     profiling=None,
		                                     simpleconnection=None,
		                                     skiplemma=None,
		                                     threadcount=None)

	return commandlineargs
