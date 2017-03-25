# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia
from server.dbsupport.dbfunctions import loadallauthorsasobjects, loadallworksasobjects, loadallworksintoallauthors
from server.listsandsession.listmanagement import dictitemstartswith
from server.listsandsession.sessiondicts import buildaugenresdict, buildworkgenresdict, buildauthorlocationdict, \
	buildworkprovenancedict

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

if hipparchia.config['ENOUGHALREADYWITHTHECOPYRIGHTNOTICE'] != 'yes':
	print(terminaltext.format(project='HipparchiaServer', year='2016-17', fullname='E. Gunderson',
	                          mail='Department of Classics, 125 Queen’s Park, Toronto, ON M5S 2C7 Canada'))


"""
this stuff gets loaded up front so you have access to all author and work info all the time
otherwise you'll hit the DB too often and ask the same question over and over again: a serious source of lag
"""

authordict = loadallauthorsasobjects()
workdict = loadallworksasobjects()
authordict = loadallworksintoallauthors(authordict, workdict)

authorgenresdict = buildaugenresdict(authordict)
authorlocationdict = buildauthorlocationdict(authordict)
workgenresdict = buildworkgenresdict(workdict)
workprovenancedict = buildworkprovenancedict(workdict)

print('building specialized sublists\n')
tlgauthors = dictitemstartswith(authordict, 'universalid', 'gr')
tlgworks = dictitemstartswith(workdict, 'universalid', 'gr')
latauthors = dictitemstartswith(authordict, 'universalid', 'lt')
latworks = dictitemstartswith(workdict, 'universalid', 'lt')
insauthors = dictitemstartswith(authordict, 'universalid', 'in')
insworks = dictitemstartswith(workdict, 'universalid', 'in')
ddpauthors = dictitemstartswith(authordict, 'universalid', 'dp')
ddpworks = dictitemstartswith(workdict, 'universalid', 'dp')
chrauthors = dictitemstartswith(authordict, 'universalid', 'ch')
chrworks = dictitemstartswith(workdict, 'universalid', 'ch')

listmapper = {
	'gr': {'a': tlgauthors, 'w': tlgworks},
	'lt': {'a': latauthors, 'w': latworks},
	'dp': {'a': insauthors, 'w': insworks},
	'in': {'a': ddpauthors, 'w': ddpworks},
	'ch': {'a': chrauthors, 'w': chrworks},
}
