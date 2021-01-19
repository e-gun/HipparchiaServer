# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import json
import re

from typing import List

from server.formatting.jsformatting import generatevectorjs, insertbrowserclickjs
from server.formatting.miscformatting import htmlcommentdecorator
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.hipparchiaobjects.searchobjects import SearchOutputObject, SearchObject
from server.hipparchiaobjects.vectorobjects import VectorValues
from server.startup import authordict, workdict


@htmlcommentdecorator
def formatlsimatches(listofmatches: List[dict]) -> str:
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


@htmlcommentdecorator
def formatnnmatches(listofneighbors: List[tuple], vectorvalues: VectorValues):
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

	xtrarowtemplate = """
	<tr class="vectorrow">
		<td class="vectorscore"></td>
		<td class="vectorword"><spance class="small">(not showing {n} {wtw} above the cutoff)</span></td>
	</tr>
	"""

	cap = vectorvalues.neighborscap
	numberofungraphedtodisplay = 10
	surplus = len(listofneighbors) - cap
	ungraphed = listofneighbors[cap:cap + numberofungraphedtodisplay]
	listofneighbors = listofneighbors[:cap]

	try:
		firstrow = firstrowtemplate.format(s=round(listofneighbors[0][1], 3), w=listofneighbors[0][0], n=len(listofneighbors)+len(ungraphed))
	except IndexError:
		firstrow = firstrowtemplate.format(s='', w='no most common neighbors found', n=1)

	rows = [firstrow] + [rowtemplate.format(s=round(n[1], 3), w=n[0]) for n in listofneighbors[1:]]
	if ungraphed:
		rows.append(rowtemplate.format(s='', w='(next {n} words)'.format(n=numberofungraphedtodisplay)))
		rows += [rowtemplate.format(s=round(n[1], 3), w=n[0]) for n in ungraphed]

	if surplus > 0:
		wtw = 'word that was'
		if surplus > 1:
			wtw = 'words that were'
		cut = vectorvalues.nearestneighborcutoffdistance
		rows.append(xtrarowtemplate.format(n=surplus, wtw=wtw, c=cut))

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


@htmlcommentdecorator
def formatnnsimilarity(termone: str, termtwo: str, similarityscore: float) -> str:
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


@htmlcommentdecorator
def skformatmostimilar(similaritiesdict: dict) -> str:
	"""

	{id: (scoreA, lineobjectA1, sentA1, lindebjectA2, sentA2), id2: (scoreB, lineobjectB1, sentB1, lineobjectB2, sentB2), ... }
	         0          1          2         3          4
	:param similaritiesdict:
	:return:
	"""

	rowtemplate = """
	<tr class="vectorrow">
		<td class="vectornumber">[{n}]</td>
		<td class="vectorscore">{s}</td>
		<td class="vectoronelocus">{locone}</td>	
		<td class="vectoronesentence">{sentone}</td>
		<td class="vectortwosentence">{senttwo}</td>
		<td class="vectortwolocus">{loctwo}</td>
		
	</tr>
	"""

	rows = list()
	for key in sorted(similaritiesdict.keys()):
		rows.append(rowtemplate.format(n=key,
		                               s=round(similaritiesdict[key][0], 2),
		                               sentone= similaritiesdict[key][2],
		                               locone=locusformat(similaritiesdict[key][1]),
		                               loctwo=locusformat(similaritiesdict[key][3]),
		                               senttwo=similaritiesdict[key][4]))

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


def locusformat(dblineobject: dbWorkLine) -> str:
	"""

	return a prolix citation from a dblineobject

	need access to authordict & workdict

	:param dblineobject:
	:return:
	"""

	au = authordict[dblineobject.authorid].name
	wk = workdict[dblineobject.wkuinversalid].title
	loc = dblineobject.locus()
	uid = dblineobject.getbrowserurl()

	citationtext = '{a}, <span class="italic">{w}</span>, <browser id="{d}">{l}</browser>'.format(a=au, w=wk, l=loc, d=uid)

	return citationtext


def nearestneighborgenerateoutput(findshtml: str, mostsimilar: list, imagename: str, workssearched: int, searchobject: SearchObject) -> str:
	"""

	:param findshtml:
	:param mostsimilar:
	:param imagename:
	:param workssearched:
	:param searchobject:
	:param activepoll:
	:param starttime:
	:return:
	"""

	vectorsearchwaslemmatized = True

	so = searchobject
	activepoll = so.poll
	output = SearchOutputObject(so)
	output.image = imagename

	findsjs = generatevectorjs()

	try:
		lm = so.lemma.dictionaryentry
	except AttributeError:
		# AttributeError: 'NoneType' object has no attribute 'dictionaryentry'
		vectorsearchwaslemmatized = False
		lm = so.seeking

	try:
		pr = so.proximatelemma.dictionaryentry
	except AttributeError:
		# proximatelemma is None
		pr = None

	if vectorsearchwaslemmatized:
		extrastringone = 'all forms of '
		ht = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=lm)
	else:
		extrastringone = str()
		ht = '<span class="sought">»{skg}«</span>'.format(skg=lm)

	output.title = 'Neighbors for {es}»{skg}«'.format(skg=lm, pr=pr, es=extrastringone)
	output.found = findshtml
	output.js = findsjs

	try:
		output.setresultcount(len(mostsimilar), 'proximate terms to graph')
	except TypeError:
		pass

	output.setscope(workssearched)
	output.thesearch = '{es}»{skg}«'.format(skg=lm, es=extrastringone)
	output.htmlsearch = ht
	output.sortby = 'proximity'
	output.image = imagename
	output.searchtime = so.getelapsedtime()
	activepoll.deactivate()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


@htmlcommentdecorator
def analogiesgenerateoutput(searchobject, findstuples: list) -> str:
	"""

	findstuples: [(word1, value1), (word2, value2), ...]

	:param searchobject:
	:param findstuples:
	:return:
	"""

	so = searchobject
	output = SearchOutputObject(so)

	if so.session['baggingmethod'] != 'unlemmatized':
		a = so.lemmaone.dictionaryentry
		b = so.lemmatwo.dictionaryentry
		c = so.lemmathree.dictionaryentry
	else:
		a = so.seeking
		b = so.proximate
		c = so.termthree

	tabletemplate = """
	<table class="vectortable outline">
	{thdr}
	{rows}
	<table>
	"""

	thdrtemplate = """
	<tr>
		<th>{a}</th>
		<th>{b}</th>
		<th>{c}</th>
	</tr>
	"""

	meth = searchobject.session['baggingmethod']

	thdr = thdrtemplate.format(a='Bagging method:', b=meth, c=str())

	rowtemplate = """
	<tr>
		<td>{wrd}</td>
		<td></td>
		<td>{val}</td>
	</tr>
	"""

	therows = [rowtemplate.format(wrd=t[0], val=t[1]) for t in findstuples]
	therows = '\n'.join(therows)

	thetable = tabletemplate.format(thdr=thdr, rows=therows)
	output.found = thetable

	activepoll = so.poll
	output.title = '{a} : {b} :: {c} : ???'.format(a=a, b=b, c=c)

	output.searchtime = so.getelapsedtime()
	activepoll.deactivate()
	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


def lsiformatoutput(findshtml: str, workssearched: int, matches: list, searchobject: SearchObject) -> str:
	"""

	should use OutputObject() instead

	:param findshtml:
	:param workssearched:
	:param searchobject:
	:param activepoll:
	:param starttime:
	:return:
	"""

	so = searchobject
	activepoll = so.poll
	output = SearchOutputObject(so)

	output.found = findshtml
	output.js = insertbrowserclickjs('browser')
	output.setscope(workssearched)
	output.title = 'Sentences that are reminiscent of »{skg}«'.format(skg=so.seeking)
	output.thesearch = output.title
	output.htmlsearch = 'sentences that are reminiscent of <span class="sought">»{skg}«</span>'.format(skg=so.seeking)
	output.resultcount = '{n} sentences above the cutoff'.format(n=len(matches))
	output.searchtime = so.getelapsedtime()

	activepoll.deactivate()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


def ldatopicsgenerateoutput(ldavishtmlandjs: str, workssearched: int, settings: dict, searchobject: SearchObject):
	"""

	pyLDAvis.prepared_data_to_html() outputs something that is almost pure JS and looks like this:

		<link rel="stylesheet" type="text/css" href="https://cdn.rawgit.com/bmabey/pyLDAvis/files/ldavis.v1.0.0.css">


		<div id="ldavis_el7428760626948328485476648"></div>
		<script type="text/javascript">

		var ldavis_el7428760626948328485476648_data = {"mdsDat": ...

		}
		</script>


	instance = {
		'maxfeatures': 2000,
		'components': 15,  # topics
		'maxfreq': .75,  # fewer than n% of sentences should have this word (i.e., purge common words)
		'minfreq': 5,  # word must be found >n times
		'iterations': 12,
		'mustbelongerthan': 3
	}

	:param ldavishtmlandjs:
	:param workssearched:
	:param settings:
	:param searchobject:
	:return:
	"""

	so = searchobject
	activepoll = so.poll
	output = SearchOutputObject(so)

	lines = ldavishtmlandjs.split('\n')
	lines = [re.sub(r'\t', str(), l) for l in lines if l]

	lines.reverse()

	thisline = str()
	html = list()

	while not re.search(r'<script type="text/javascript">', thisline):
		html.append(thisline)
		try:
			thisline = lines.pop()
		except IndexError:
			# oops, we never found the script...
			thisline = '<script type="text/javascript">'

	# we cut '<script>'; now drop '</script>'
	lines.reverse()
	js = lines[:-1]

	findshtml = '\n'.join(html)
	findsjs = '\n'.join(js)

	ldacssurl = r'https://cdn.rawgit.com/bmabey/pyLDAvis/files/ldavis.v1.0.0.css'
	ldacsslocal = '/css/ldavis.css'
	findshtml = re.sub(ldacssurl, ldacsslocal, findshtml)

	# brittle: ldavis might change its URLs between versions, etc.
	# should probably make this conditional upon the presence of the file locally...
	ldajsurl = r'https://cdn.rawgit.com/bmabey/pyLDAvis/files/ldavis.v1.0.0.js'
	ldajslocal = '/static/jsforldavis.js'
	findsjs = re.sub(ldajsurl, ldajslocal, findsjs)

	# this next will break the reloaded figure: hm...
	# d3jsurl = r'https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min'
	# d3jslocal = '/static/jsd3'
	# findsjs = re.sub(d3jsurl, d3jslocal, findsjs)
	#
	# print('findsjs',findsjs)

	who = str()
	where = '{n} authors'.format(n=searchobject.numberofauthorssearched())

	if searchobject.numberofauthorssearched() == 1:
		a = authordict[searchobject.searchlist[0][:6]]
		who = a.akaname
		where = who

	if workssearched == 1:
		try:
			w = workdict[searchobject.searchlist[0]]
			w = w.title
		except KeyError:
			w = str()
		where = '{a}, <worktitle>{w}</worktitle>'.format(a=who, w=w)

	output.title = 'Latent Dirichlet Allocation'
	output.found = findshtml
	output.js = findsjs

	output.setscope(workssearched)
	output.sortby = 'weight'
	output.thesearch = 'thesearch'.format(skg='')
	output.resultcount = 'the following topics'
	output.htmlsearch = '{n} topics in {w}'.format(n=settings['components'], w=where)
	output.searchtime = so.getelapsedtime()
	activepoll.deactivate()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput

