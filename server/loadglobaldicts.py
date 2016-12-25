# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""


from server.dbsupport.dbfunctions import loadallauthorsasobjects, loadallworksasobjects, loadallworksintoallauthors
from server.formatting_helper_functions import prunedict
from server.sessionhelpers.sessiondicts import buildaugenresdict, buildworkgenresdict, buildauthorlocationdict, \
	buildworkprovenancedict

"""
this stuff gets loaded up front so you have access to all author and work info all the time
otherwise you'll hit the DB too often and ask the same question over and over again: it's a serious source of lag
"""

authordict = loadallauthorsasobjects()
workdict = loadallworksasobjects()
authordict = loadallworksintoallauthors(authordict, workdict)

authorgenresdict = buildaugenresdict(authordict)
authorlocationdict = buildauthorlocationdict(authordict)
workgenresdict = buildworkgenresdict(workdict)
workprovenancedict = buildworkprovenancedict(workdict)

print('building specialized sublists')
tlgauthors = prunedict(authordict, 'universalid', 'gr')
tlgworks = prunedict(workdict, 'universalid', 'gr')
latauthors = prunedict(authordict, 'universalid', 'lt')
latworks = prunedict(workdict, 'universalid', 'lt')
insauthors = prunedict(authordict, 'universalid', 'in')
insworks = prunedict(workdict, 'universalid', 'in')
ddpauthors = prunedict(authordict, 'universalid', 'dp')
ddpworks = prunedict(workdict, 'universalid', 'dp')

listmapper = {
	'gr': {'a': tlgauthors, 'w': tlgworks},
	'lt': {'a': latauthors, 'w': latworks},
	'in': {'a': insauthors, 'w': insworks},
	'dp': {'a': ddpauthors, 'w': ddpworks},
}

