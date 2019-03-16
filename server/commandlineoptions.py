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

	commandlineparser = argparse.ArgumentParser(description='Start Hipparchia Server')

	commandlineparser.add_argument('--profiling', action='store_true', help='[debugging] enable the profiler')
	commandlineparser.add_argument('--skiplemma', action='store_true', help='[debugging] use empty lemmatadict for fast startup')
	commandlineparser.add_argument('--portoverride', required=False, type=int, help='[debugging] override the config file listening port')
	commandlineparser.add_argument('--threadcount', required=False, type=int, help='[debugging] override the config file threadcount')
	commandlineargs = commandlineparser.parse_args()

	return commandlineargs

