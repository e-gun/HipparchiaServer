# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
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

	firstrowtemplate = """
	<tr class="vectorrow">
		<td class="vectorscore">{s}</td>
		<td class="vectorword"><lemmaheadword id="{w}">{w}</lemmaheadword></td>
		<td class="imageholder" rowspan="{n}"><p id="imagearea"></p></td>
	</tr>
	"""

	rowtemplate = """
	<tr class="vectorrow">
		<td class="vectorscore">{s}</td>
		<td class="vectorword"><lemmaheadword id="{w}">{w}</lemmaheadword></td>
	</tr>
	"""

	firstrow = firstrowtemplate.format(s=round(listofneighbors[0][1], 3), w=listofneighbors[0][0], n=len(listofneighbors))

	rows = [firstrow] + [rowtemplate.format(s=round(n[1], 3), w=n[0]) for n in listofneighbors[1:]]

	newrows = list()
	count = 0
	for r in rows:
		count += 1
		if count % 3 == 0:
			r = re.sub(r'class="vectorrow"', 'class="nthrow"', r)
		newrows.append(r)

	rows = ['<table class="indented">'] + newrows + ['</table>']

	thehtml = '\n'.join(rows)

	return thehtml


def formatnnsimilarity(termone, termtwo, similarityscore):
	"""


	:param similarityscore:
	:return:
	"""

	template = """
	<p class="indented">
	the similarity of forms of <code>{a}</code>  
	and forms of <code>{b}</code> is <code>{c}</code>.
	</p>
	"""

	similarity = template.format(a=termone, b=termtwo, c=round(similarityscore, 3))

	return similarity


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


def vectorhtmlforfrontpage():
	"""

	read the config and generate the html

	:return:
	"""

	cdc = """
		<span id="cosinedistancesentencecheckbox">
			<span class="small">Word environs:</span>
			<span class="small">by sentence</span><input type="checkbox" id="cosdistbysentence" value="yes" title="Cosine distances: words in the same sentence">
		</span>
		<span id="cosinedistancelineorwordcheckbox">
			<span class="small">within N lines/words</span><input type="checkbox" id="cosdistbylineorword" value="yes" title="Cosine distances within N lines or words">
		</span>
		"""

	cs = """
		<span id="semanticvectorquerycheckbox">
			<span class="small">&nbsp;&middot;&nbsp;Concept search</span><input type="checkbox" id="semanticvectorquery" value="yes" title="Make a latent semantic analysis query">
		</span>
		"""

	cm = """
		<span id="semanticvectornnquerycheckbox">
			<span class="small">&nbsp;&middot;&nbsp;Concept map</span><input type="checkbox" id="nearestneighborsquery" value="yes" title="Make a nearest neighbor query">
		</span>
		"""

	tf = """
		<span id="tensorflowgraphcheckbox">
			<span class="small">&nbsp;&middot;&nbsp;tensor flow graph:</span>
			<span class="small">tf</span><input type="checkbox" id="tensorflowgraph" value="yes" title="Make an associative graph of all the selected words">
		</span>
		"""

	if hipparchia.config['SEMANTICVECTORSENABLED'] != 'yes':
		return ''

	textmapper = {'LITERALCOSINEDISTANCEENABLED': cdc,
	              'CONCEPTSEARCHINGENABLED': cs,
	              'CONCEPTMAPPINGENABLED': cm,
	              'TENSORFLOWVECTORSENABLED': tf }

	vectorhtml = list()
	for conf in textmapper:
		if hipparchia.config[conf] == 'yes':
			vectorhtml.append(textmapper[conf])

	vectorhtml = '\n'.join(vectorhtml)

	return vectorhtml
