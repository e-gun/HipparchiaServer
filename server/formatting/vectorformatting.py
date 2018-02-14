# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.startup import authordict, workdict


def formatlsimatches(listofmatches):
	"""

	generate html for the matches

	each match comes as a dict
			thismatch['count'] = count
			thismatch['score'] = round(s[1], 3)
			thismatch['line'] = dbline
			thismatch['sentence'] = ' '.join(thissentence)
			thismatch['words'] = c.bagsofwords[s[0]]

	:param listofmatches:
	:return:
	"""

	rowtemplate = """
	<tr class="vectorrow">
		<td class="vectorscount">[{c}]</td>
		<td class="vectorscore">{s}</td>
		<td class="vectorlocus">{l}</td>
		<td class="vectorsentence">{t}</td>
	</tr>
	"""

	rows = [rowtemplate.format(c=m['count'], s=round(m['score'], 3), l=locusformat(m['line']), t=m['sentence']) for m in listofmatches]

	newrows = list()
	count = 0
	for r in rows:
		count += 1
		if count % 2 == 0:
			r = re.sub(r'class="vectorrow"', 'class="nthrow"', r)
		newrows.append(r)

	rows = ['<table class="vectortable">'] + newrows + ['</table>']

	thehtml = '\n'.join(rows)

	return thehtml


def formatnnmatches(listofneighbors):
	"""

	each neighbor is a tuple: [('εὕρηϲιϲ', 1.0), ('εὑρίϲκω', 0.6673248708248138), ...]

	:param listofneighbors:
	:return:
	"""

	rowtemplate = """
	<tr class="vectorrow">
		<td class="vectorscore">{s}</td>
		<td class="vectorword">{w}</td>
	</tr>
	"""

	rows = [rowtemplate.format(s=round(n[1], 3), w=n[0]) for n in listofneighbors]

	newrows = list()
	count = 0
	for r in rows:
		count += 1
		if count % 3 == 0:
			r = re.sub(r'class="vectorrow"', 'class="nthrow"', r)
		newrows.append(r)

	rows = ['<table class="vectortable">'] + newrows + ['</table>']

	thehtml = '\n'.join(rows)

	return thehtml


def locusformat(dblineobject):
	"""

	return a prolix citation from a dblineobject

	need access to authordict & workdict

	:param dblineobject:
	:return:
	"""

	au = authordict[dblineobject.authorid].name
	wk = workdict[dblineobject.wkuinversalid].title
	loc = dblineobject.locus()

	citationtext = '{a}, <span class="italic">{w}</span>, {l}'.format(a=au, w=wk, l=loc)

	return citationtext