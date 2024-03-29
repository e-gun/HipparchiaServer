# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque

from server.dbsupport.dblinefunctions import makeablankline
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.sessionfunctions import findactivebrackethighlighting
from server.textsandindices.textandindiceshelperfunctions import setcontinuationvalue


def gtltsubstitutes(text: str) -> str:
	"""
		&lt; for ⟨
		&gt; for ⟩

		should almost certainly be called very late since there are various checks that
		will look for ⟩ and ⟨ specifically

	"""

	text = re.sub(r'⟨', r'&lt;', text)
	text = re.sub(r'⟩', r'&gt;', text)

	return text


def brackethtmlifysearchfinds(listoflineobjects: list, searchobject: SearchObject, linehtmltemplate: str) -> list:
	"""

	can't do comprehensions: require a thisline/previousline structure so you can call setcontinuationvalue()

	:param listoflineobjects:
	:param searchobject:
	:param linehtmltemplate:
	:return:
	"""

	brackettypes = findactivebrackethighlighting(searchobject.session)
	continuationdict = {t: False for t in brackettypes}

	passage = list()
	lines = deque(listoflineobjects)
	try:
		previous = lines.popleft()
	except IndexError:
		previous = makeablankline('gr0000w000', -1)

	passage.append(linehtmltemplate.format(id=previous.getlineurl(), lc=previous.locus(), ft=previous.markeditorialinsersions(continuationdict)))

	while lines:
		ln = lines.popleft()
		passage.append(linehtmltemplate.format(id=ln.getlineurl(), lc=ln.locus(), ft=ln.markeditorialinsersions(continuationdict)))
		continuationdict = {t: setcontinuationvalue(ln, previous, continuationdict[t], t) for t in brackettypes}
		previous = ln

	return passage
