# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import time
from multiprocessing import current_process
from sys import platform

from click import secho

from server import hipparchia
from server.calculatewordweights import findccorporaweights, findtemporalweights, workobjectgeneraweights
from server.commandlineoptions import getcommandlineargs
from server.dbsupport.bulkdboperations import loadallauthorsasobjects, loadallworksasobjects, \
	loadallworksintoallauthors, loadlemmataasobjects
from server.dbsupport.miscdbfunctions import probefordatabases
from server.formatting.miscformatting import skipnewlineprint
from server.listsandsession.genericlistfunctions import dictitemstartswith, findspecificdate
from server.listsandsession.sessiondicts import buildaugenresdict, buildauthorlocationdict, buildkeyedlemmata, \
	buildworkgenresdict, buildworkprovenancedict
from server.threading.mpthreadcount import setthreadcount


if current_process().name == 'MainProcess':
	commandlineargs = getcommandlineargs()

	# stupid Windows will fork new copies and reload all of this

	terminaltext = """
	
	{project} / Copyright (C) {year} / {fullname}
	{mail}
	
	This program comes with ABSOLUTELY NO WARRANTY;
	without even the implied warranty of MERCHANTABILITY
	or FITNESS FOR A PARTICULAR PURPOSE.
	
	This is free software, and you are welcome to redistribute
	it and/or modify it under the terms of the GNU General
	Public License version 3.
	
	"""

	project = 'HipparchiaServer'
	year = '2016-19'
	fullname = 'E. Gunderson'
	mailingaddr = 'Department of Classics, 125 Queen’s Park, Toronto, ON  M5S 2C7 Canada'

	if not hipparchia.config['ENOUGHALREADYWITHTHECOPYRIGHTNOTICE']:
		print(terminaltext.format(project=project, year=year, fullname=fullname, mail=mailingaddr))

	available = probefordatabases()
	warning = sum([available[x] for x in available])
	if warning == 0:
		print('WARNING: support data is missing; some functions will be disabled')
		for key in available:
			if not available[key]:
				print('\t{d} is unavailable'.format(d=key))
		print()
	del warning
	del available

	if setthreadcount(startup=True) == 1:
		print('queries will be dispatched to 1 thread')
	else:
		print('queries will be dispatched to {t} threads'.format(t=setthreadcount()))

	"""
	this stuff gets loaded up front so you have access to all author and work info all the time
	otherwise you'll hit the DB too often and ask the same question over and over again
	"""

	# startup 4.922947645187378
	# profiling: [see https://zapier.com/engineering/profiling-python-boss/]
	# [a]
	# loadallauthorsasobjects(): 3589 function calls in 0.024 seconds
	# loadallworksasobjects(): 236975 function calls in 2.980 seconds
	#        236845    1.671    0.000    1.671    0.000 dbtextobjects.py:115(__init__)
	#       [but nothing happens inside of __init__ that you can expect to speed up]
	# loadallworksintoallauthors(): 473693 function calls in 0.241 seconds
	# [b]
	# buildaugenresdict(): 1840 function calls (1835 primitive calls) in 0.003 seconds
	# [c]
	# dictitemstartswith(): 1184230 function calls in 0.954 seconds
	# findspecificdate(): 1483 function calls in 0.142 seconds

	authordict = loadallauthorsasobjects()
	workdict = loadallworksasobjects()
	authordict = loadallworksintoallauthors(authordict, workdict)

	if commandlineargs.skiplemma:
		print('lemmatadict disabled for debugging run')
		lemmatadict = dict()
	else:
		lemmatadict = loadlemmataasobjects()

	# lemmatadict too long to be used by the hinter: need quicker access; so partition it up into keyedlemmata
	keyedlemmata = buildkeyedlemmata(list(lemmatadict.keys()))

	skipnewlineprint('building core dictionaries')
	launchtime = time.time()
	authorgenresdict = buildaugenresdict(authordict)
	authorlocationdict = buildauthorlocationdict(authordict)
	workgenresdict = buildworkgenresdict(workdict)
	workprovenancedict = buildworkprovenancedict(workdict)
	elapsed = round(time.time() - launchtime, 1)
	secho(' ({e}s)'.format(e=elapsed), fg='red')

	skipnewlineprint('building specialized sublists')
	launchtime = time.time()

	listmapper = {
		'gr': {'a': dictitemstartswith(authordict, 'universalid', 'gr'), 'w': dictitemstartswith(workdict, 'universalid', 'gr')},
		'lt': {'a': dictitemstartswith(authordict, 'universalid', 'lt'), 'w': dictitemstartswith(workdict, 'universalid', 'lt')},
		'dp': {'a': dictitemstartswith(authordict, 'universalid', 'dp'), 'w': dictitemstartswith(workdict, 'universalid', 'dp')},
		'in': {'a': dictitemstartswith(authordict, 'universalid', 'in'), 'w': dictitemstartswith(workdict, 'universalid', 'in')},
		'ch': {'a': dictitemstartswith(authordict, 'universalid', 'ch'), 'w': dictitemstartswith(workdict, 'universalid', 'ch')},
	}

	# search list building and pruning was testing all items for their date
	# this too often at a cost of .5s per full corpus search
	# so a master list is built up front that you can quickly make a check against

	allworks = workdict.keys()
	allvaria = set(findspecificdate(allworks, authordict, workdict, 2000))
	allincerta = set(findspecificdate(allworks, authordict, workdict, 2500))

	del allworks

	elapsed = round(time.time() - launchtime, 1)
	secho(' ({e}s)'.format(e=elapsed), fg='red')
	del elapsed
	del launchtime

	# CALCULATEWORDWEIGHTS will recalibrate the weighting constants: only
	# 	useful after a new DB build with new corpora definitions (i.e., *very* rarely).
	# 	this can take a couple of minutes to calculate, so leaving it
	# 	at 'yes' is not such a great idea. And the new numbers are
	# 	not in fact entered into the code, just calculated; so you have
	# 	to edit dbHeadwordObject() yourself  after you are given the
	# 	numbers to send to it; if COLLAPSEDGENRECOUNTS is 'yes', you will
	#   not see all of the possibilities

	if commandlineargs.calculatewordweights or commandlineargs.collapsedgenreweights:
		print('calculating word weights...')
		if commandlineargs.collapsedgenreweights:
			c = True
		else:
			c = False
		print('greek wordweights', findtemporalweights('G'))
		print('corpus weights', findccorporaweights())

		print('greek genre weights:', workobjectgeneraweights('G', c, workdict))
		print('latin genre weights:', workobjectgeneraweights('L', c, workdict))

	# empty dict in which to store progress polls
	# note that more than one poll can be running
	poll = dict()
else:
	# welcome back Windows users
	authordict = dict()
	workdict = dict()
	authorgenresdict = dict()
	authorlocationdict = dict()
	workgenresdict = dict()
	workprovenancedict = dict()
	lemmatadict = dict()
	listmapper = dict()
	allincerta = dict()
	allvaria = dict()
	keyedlemmata = dict()
	# this will break things?
	poll = dict()
