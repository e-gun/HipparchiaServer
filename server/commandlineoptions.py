# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import argparse


def getcommandlineargs():
	"""

	what, if anything, was passed to "run.py"?

	:return:
	"""

	commandlineparser = argparse.ArgumentParser(description='script used to launch HipparchiaServer')
	exclusivegroup = commandlineparser.add_mutually_exclusive_group()

	commandlineparser.add_argument('--calculatewordweights', action='store_true', help='[info] (re)generate word weight info')
	commandlineparser.add_argument('--collapsedgenreweights', action='store_true', help='[info] (re)generate word weight info & merge related genres ("allret", etc.)')
	commandlineparser.add_argument('--dbhost', required=False, type=str, help='[debugging] override the config file database host address')
	commandlineparser.add_argument('--dbname', required=False, type=str, help='[debugging] override the config file database name')
	commandlineparser.add_argument('--dbport', required=False, type=int, help='[debugging] override the config file database listening port')
	commandlineparser.add_argument('--disablevectorbot', action='store_true', help='[debugging] forciby disable the vectorbot for this run')
	commandlineparser.add_argument('--enabledebugui', action='store_true', help='[debugging] (potentially) override the config file and turn the debug UI on')
	exclusivegroup.add_argument('--pooledconnection', action='store_true', help='[debugging] (potentially) override the config file and force a pooled DB connection')
	commandlineparser.add_argument('--profiling', action='store_true', help='[debugging] enable the profiler')
	exclusivegroup.add_argument('--simpleconnection', action='store_true', help='[debugging] (potentially) override the config file and force a simple DB connection')
	commandlineparser.add_argument('--skiplemma', action='store_true', help='[debugging] use empty lemmatadict for fast startup')
	commandlineparser.add_argument('--portoverride', required=False, type=int, help='[debugging] override the config file listening port')
	commandlineparser.add_argument('--threadcount', required=False, type=int, help='[debugging] override the config file threadcount')

	commandlineargs = commandlineparser.parse_args()

	return commandlineargs
