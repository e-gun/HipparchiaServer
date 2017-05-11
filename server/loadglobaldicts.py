# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re

from server import hipparchia
from server.dbsupport.dbfunctions import loadallauthorsasobjects, loadallworksasobjects, loadallworksintoallauthors
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


def dictitemstartswith(originaldict, element, muststartwith):
	"""

	trim a dict via a criterion: muststartwith must begin the item to survive the check

	:param originaldict:
	:param element:
	:param muststartwith:
	:return:
	"""

	muststartwith = re.compile('^'+muststartwith)
	newdict = {x: originaldict[x] for x in originaldict
	           if re.search(muststartwith, getattr(originaldict[x], element))}

	return newdict


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
	'in': {'a': insauthors, 'w': insworks},
	'dp': {'a': ddpauthors, 'w': ddpworks},
	'ch': {'a': chrauthors, 'w': chrworks},
}


def findspecificdate(authorandworklist, authorobjectdict, workobjectdict, specificdate):
	"""

	tell me which items on the authorandworklist have unknown dates

		incerta = 2500
		varia = 2000
		[failedtoparse = 9999]

	this profiles as fairly slow when called on a large search list (.5s): 
	it might be better to build a list of these up front
	when loading HipparchiaServer since this is both static and repetitive

	:param authorandworklist:
	:param authorobjectdict:
	:param worksdict:
	:return:
	"""
	datematches = []

	for aw in authorandworklist:
		w = workobjectdict[aw]
		try:
			# does the work have a date? if not, we will throw an exception
			cd = int(w.converted_date)
			if cd == specificdate:
				datematches.append(aw)
		except:
			# no work date? then we will look inside the author for the date
			aid = aw[0:6]
			try:
				cd = int(authorobjectdict[aid].converted_date)
				if cd == specificdate:
					datematches.append(aw)
			except:
				# the author can't tell you his date; i guess it is incerta by definition
				datematches.append(aw)

	return datematches

# search list building and pruning was testing all items for their date this too often at a cost of .5s per full corpus search
# so a master list is built up front that you can quickly make a check against

allworks = workdict.keys()
allvaria = set(findspecificdate(allworks, authordict, workdict, 2000))
allincerta = set(findspecificdate(allworks, authordict, workdict, 2500))
allunknown = set(findspecificdate(allworks, authordict, workdict, 2000))
allincerta = allincerta.union(allunknown)
del allworks
del allunknown
