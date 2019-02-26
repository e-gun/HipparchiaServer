# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import json
import re

from typing import List

from server import hipparchia
from server.formatting.jsformatting import generatevectorjs, insertbrowserclickjs
from server.hipparchiaobjects.dbtextobjects import dbWorkLine
from server.hipparchiaobjects.searchobjects import SearchOutputObject, SearchObject
from server.hipparchiaobjects.vectorobjects import VectorValues
from server.semanticvectors.vectorhelpers import vectordefaults, vectorranges, vectorlabels
from server.startup import authordict, workdict


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
	uid = dblineobject.url

	citationtext = '{a}, <span class="italic">{w}</span>, <browser id="{d}">{l}</browser>'.format(a=au, w=wk, l=loc, d=uid)

	return citationtext


def vectorhtmlforfrontpage() -> str:
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
			<span class="small">Concept search</span><input type="checkbox" id="semanticvectorquery" value="yes" title="Make a latent semantic analysis query">
		</span>
		"""

	cm = """
		<span id="semanticvectornnquerycheckbox">
			<span class="small">Concept map</span><input type="checkbox" id="nearestneighborsquery" value="yes" title="Make a nearest neighbor query">
		</span>
		"""

	tf = """
		<span id="tensorflowgraphcheckbox">
			<span class="small">tensor flow graph:</span>
			<input type="checkbox" id="tensorflowgraph" value="yes" title="Make an associative graph of all the selected words">
		</span>
		"""

	ss = """
		<span id="sentencesimilaritycheckbox">
			<span class="small">sentence similarities</span>
			<input type="checkbox" id="sentencesimilarity" value="yes" title="Find sentence similarities in and between works">
		</span>
	"""

	lda = """
		<span id="topicmodelcheckbox">
			<span class="small">Topic map</span>
			<input type="checkbox" id="topicmodel" value="yes" title="Find topics within a search zone">
		</span>
	"""

	if hipparchia.config['SEMANTICVECTORSENABLED'] != 'yes':
		return str()

	textmapper = {'LITERALCOSINEDISTANCEENABLED': cdc,
	              'CONCEPTSEARCHINGENABLED': cs,
	              'CONCEPTMAPPINGENABLED': cm,
	              # 'TENSORFLOWVECTORSENABLED': tf,
	              # 'SENTENCESIMILARITYENABLED': ss,
	              'TOPICMODELINGENABLED': lda}

	vectorhtml = list()
	for conf in textmapper:
		if hipparchia.config[conf] == 'yes':
			vectorhtml.append(textmapper[conf])

	vectorhtml = '\n'.join(vectorhtml)

	return vectorhtml


def vectorhtmlforoptionsbar() -> str:
	"""

	if we are doing vectors, then allow values to be set

	need html (and js...) support for this

	:return:
	"""

	if hipparchia.config['SEMANTICVECTORSENABLED'] != 'yes':
		emptyframe = """
		<div id="vectoroptionsetter"></div>
		"""
		return emptyframe

	framedcontents = """
	<div id="vectoroptionsetter" class="sidenavigation">
		<div id="vector_upperleftbuttons">
			<span id="vectoralt_openoptionsbutton" class="ui-icon ui-icon-gear" title="Configuration options"></span>
			<span id="close_vector_options_button" class="ui-icon ui-icon-arrowthick-1-sw" title="Vector options"></span>
			<span id="vectoralt_moretools" title="Lexical tools" class="ui-icon ui-icon-wrench"></span>
			<span id="vectoralt_clear_button" class="ui-icon ui-icon-close" title="Reset session/Clear search"></span>
		</div>
		<p class="optionlabel">Semantic Vector Settings</p>
		{contents}
	</div>
	"""

	fieldtemplate = """
	<fieldset id="{k}field">
		<legend>{lg}</legend>
		<input id="{k}" type="text" value="{d}" width="20px;">
	</fieldset>
	"""

	legendtemplate = '{lb} ({min} - {max})'

	htmlsupplement = list()
	for k in vectordefaults.keys():
		r = list(vectorranges[k])
		m = r[0]
		x = r[-1]
		lg = legendtemplate.format(lb=vectorlabels[k], min=m, max=x)
		htmlsupplement.append(fieldtemplate.format(k=k, lg=lg, d=vectordefaults[k]))

	htmlsupplement = '\n'.join(htmlsupplement)

	htmlsupplement = framedcontents.format(contents=htmlsupplement)

	return htmlsupplement


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

	so = searchobject
	activepoll = so.poll
	output = SearchOutputObject(so)
	output.image = imagename

	findsjs = generatevectorjs()

	lm = so.lemma.dictionaryentry
	try:
		pr = so.proximatelemma.dictionaryentry
	except AttributeError:
		# proximatelemma is None
		pr = None

	output.title = 'Neighbors for all forms of »{skg}«'.format(skg=lm, pr=pr)
	output.found = findshtml
	output.js = findsjs

	try:
		output.setresultcount(len(mostsimilar), 'proximate terms to graph')
	except TypeError:
		pass

	output.setscope(workssearched)
	output.thesearch = 'all forms of »{skg}«'.format(skg=lm)
	output.htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=lm)
	output.sortby = 'proximity'
	output.image = imagename
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
	lines = [re.sub(r'\t', '', l) for l in lines if l]

	lines.reverse()

	thisline = ''
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
			w = ''
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

