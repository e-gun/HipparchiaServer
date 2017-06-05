# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Process, Manager

from flask import session

from server import hipparchia
from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject, setconnection, setthreadcount
from server.hipparchiaobjects.helperobjects import FormattedSearchResult


def highlightsearchterm(lineobject, searchterm, spanname):
	"""
	html markup for the search term in the line
	in order to highlight a polytonic word that you found via a unaccented search you need to convert:
		ποταμον
	into:
		((π|Π)(ο|ὀ|ὁ|ὂ|ὃ|ὄ|ὅ|ό|ὸ|Ο|Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ)(τ|Τ)(α|ἀ|ἁ|ἂ|ἃ|ἄ|ἅ|ἆ|ἇ|ᾀ|ᾁ|ᾂ|ᾃ|ᾄ|ᾅ|ᾆ|ᾇ|ᾲ|ᾳ|ᾴ|ᾶ|ᾷ|ᾰ|ᾱ|ὰ|ά|ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ|Α)(μ|Μ)ό(ν|Ν))

	:param lineobject:
	:param searchterm:
	:param spanname:
	:return:
	"""

	line = lineobject.accented

	equivalents = {
		'α': '(α|ἀ|ἁ|ἂ|ἃ|ἄ|ἅ|ἆ|ἇ|ᾀ|ᾁ|ᾂ|ᾃ|ᾄ|ᾅ|ᾆ|ᾇ|ᾲ|ᾳ|ᾴ|ᾶ|ᾷ|ᾰ|ᾱ|ὰ|ά|ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ|Α)',
		'β': '(β|Β)',
		'ψ': '(ψ|Ψ)',
		'δ': '(δ|Δ)',
		'ε': '(ε|ἐ|ἑ|ἒ|ἓ|ἔ|ἕ|ὲ|έ|Ε|Ἐ|Ἑ|Ἒ|Ἓ|Ἔ|Ἕ)',
		'φ': '(φ|Φ)',
		'γ': '(γ|Γ)',
		'η': '(η|ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|ή|ἡ|ἦ|Η|ᾘ|ᾙ|ᾚ|ᾛ|ᾜ|ᾝ|ᾞ|ᾟ|Ἠ|Ἡ|Ἢ|Ἣ|Ἤ|Ἥ|Ἦ|Ἧ)',
		'ι': '(ι|ἰ|ἱ|ἲ|ἳ|ἴ|ἵ|ἶ|ἷ|ὶ|ί|ῐ|ῑ|ῒ|ΐ|ῖ|ῗ|ΐ|Ἰ|Ἱ|Ἲ|Ἳ|Ἴ|Ἵ|Ἶ|Ἷ|Ι)',
		'ξ': '(ξ|Ξ)',
		'κ': '(κ|Κ)',
		'λ': '(λ|Λ)',
		'μ': '(μ|Μ)',
		'ν': '(ν|Ν)',
		'ο': '(ο|ὀ|ὁ|ὂ|ὃ|ὄ|ὅ|ό|ὸ|Ο|Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ)',
		'π': '(π|Π)',
		'ρ': '(ρ|Ρ|ῥ|Ῥ)',
		'ϲ': '(ϲ|Σ)',
		'σ': '(ϲ|Σ)',
		'ς': '(ϲ|Σ)',
		'τ': '(τ|Τ)',
		'υ': '(υ|ὐ|ὑ|ὒ|ὓ|ὔ|ὕ|ὖ|ὗ|ϋ|ῠ|ῡ|ῢ|ΰ|ῦ|ῧ|ύ|ὺ|Ὑ|Ὓ|Ὕ|Ὗ|Υ)',
		'ω': '(ω|ὠ|ὡ|ὢ|ὣ|ὤ|ὥ|ὦ|ὧ|ᾠ|ᾡ|ᾢ|ᾣ|ᾤ|ᾥ|ᾦ|ᾧ|ῲ|ῳ|ῴ|ῶ|ῷ|ώ|ὼ|Ω|ᾨ|ᾩ|ᾪ|ᾫ|ᾬ|ᾭ|ᾮ|ᾯ|Ὠ|Ὡ|Ὢ|Ὣ|Ὤ|Ὥ|Ὦ|Ὧ|Ω)',
		'χ': '(χ|Χ)',
		'θ': '(θ|Θ)',
		'ζ': '(ζ|Ζ)',
		'a': '(a|á|ä)',
		'e': '(e|é|ë)',
		'i': '(i|í|ï)',
		'o': '(o|ó|ö)',
		'u': '(u|ü|v)',
		'v': '(u|ü|v)'
	}

	newline = line

	line = newline
	accentedsearch = ''
	searchterm = re.sub(r'(^\s|\s$)', '', searchterm)
	for c in searchterm:
		try:
			c = equivalents[c]
		except:
			pass
		accentedsearch += c
	# accentedsearch = '(^|)('+accentedsearch+')($|)'
	accentedsearch = '(' + accentedsearch + ')'

	find = re.search(accentedsearch, line)
	try:
		newline = '{ls}<span class="{sp}">{fg}</span>{le}'.format(ls=line[0:find.start()], sp=spanname, fg=find.group(), le=line[find.end():])
	except:
		# the find was almost certainly a hyphenated last word: 'pro-' instead of 'profuit'
		hyph = lineobject.hyphenated
		find = re.search(accentedsearch, hyph)
		try:
			newline = line+'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(&nbsp;match:&nbsp;{hs}<span class="{sn}">{fg}</span>{he}&nbsp;)'.format(hs=hyph[0:find.start()], sn=spanname, fg=find.group(), he=hyph[find.end():])
		except:
			pass
		# print('nofind',accentedsearch, line, lineobject.lastword('contents'))

	return newline


def formatauthorandworkinfo(authorname, workobject):
	"""
	dbdata into html
	send me: authorname + universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""

	if workobject.wordcount:
		c = '[' + format(workobject.wordcount, ',d') + ' wds]'
	else:
		c = ''

	authorandworkinfo = '{a}, <span class="italic">{t}</span> {c}<br />'.format(a=authorname, t=workobject.title, c=c)

	return authorandworkinfo


def mpresultformatter(hitdict, authordict, workdict, seeking, proximate, searchtype, activepoll):
	"""
	if you have lots of results, they don't get formatted as fast as they could:
	single threaded is fine if all from same author, but something like 1500 hits of αξιολ will bounce you around a lot
		22s single threaded to do search + format
		12s multi-threaded to do search + format

	the hitdict is a collection of line objects where the key is the proper sort order for the results
		hitdict {0: <server.hipparchiaclasses.dbWorkLine object at 0x103dd17b8>, 1: <server.hipparchiaclasses.dbWorkLine object at 0x103dd1780>, 3: ...}

	returns a sorted list of FormattedSearchResult objects

	:return:
	"""

	# for h in hitdict.keys():
	#	print(h,hitdict[h].universalid, hitdict[h].accented)

	linesofcontext = int(session['linesofcontext'])

	activepoll.allworkis(len(hitdict))
	activepoll.remain(len(hitdict))

	if len(hitdict) > int(session['maxresults']):
		limit = int(session['maxresults'])
	else:
		limit = len(hitdict)

	criteria = {'ctx': linesofcontext, 'seek': seeking, 'prox': proximate, 'type': searchtype}

	workbundles = []
	for i in range(0, limit):
		lineobject = hitdict[i]
		authorobject = authordict[lineobject.wkuinversalid[0:6]]
		wid = lineobject.wkuinversalid
		workobject = workdict[wid]
		workbundles.append({'hitnumber': i + 1, 'lo': lineobject, 'wo': workobject, 'ao': authorobject})

	manager = Manager()
	allfound = manager.dict()
	bundles = manager.list(workbundles)
	criteria = manager.dict(criteria)

	workers = setthreadcount()

	jobs = [Process(target=formattingworkpile, args=(bundles, criteria, activepoll, allfound))
			for i in range(workers)]

	for j in jobs: j.start()
	for j in jobs: j.join()

	# allfound = { 1: <server.hipparchiaclasses.FormattedSearchResult object at 0x111e73160>, 2: ... }
	keys = sorted(allfound.keys())
	finds = [allfound[k] for k in keys]

	return finds


def formattingworkpile(bundles, criteria, activepoll, allfound):
	"""
	the work for the workers to send to formattedcittationincontext()

	a bundle:
		{'hitnumber': 3, 'wo': <server.hipparchiaclasses.dbOpus object at 0x1109ad240>, 'ao': <server.hipparchiaclasses.dbAuthor object at 0x1109ad0f0>, 'lo': <server.hipparchiaclasses.dbWorkLine object at 0x11099d9e8>}

	criteria:
		{'seek': 'οἵ ῥά οἱ', 'type': 'phrase', 'ctx': 4, 'prox': ''}

	:param workbundles:
	:return:
	"""
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	while len(bundles) > 0:
		try:
			bundle = bundles.pop()
		except IndexError:
			# IndexError: pop from empty list
			bundle = None

		if bundle:
			citwithcontext = formattedcitationincontext(bundle['lo'], bundle['wo'], bundle['ao'], criteria['ctx'],
														criteria['seek'], criteria['prox'], criteria['type'], curs)
			citwithcontext.hitnumber = bundle['hitnumber']
			activepoll.remain(bundle['hitnumber'])

			if bundle['hitnumber'] % hipparchia.config['MPCOMMITCOUNT']  == 0:
				dbconnection.commit()

			if citwithcontext.lineobjects != []:
				allfound[bundle['hitnumber']] = citwithcontext

	dbconnection.commit()
	curs.close()

	return allfound


def formattedcitationincontext(lineobject, workobject, authorobject, linesofcontext, searchterm, proximate,
							   searchtype, curs):
	"""
	take a hit
		turn it into a focus line
		surround it by some context

	in:
		lineobject

	out:
		FormattedSearchResult object

	:param line:
	:param workdbname:
	:param authorobject:
	:param linesofcontext:
	:param searchterm:
	:param cursor:
	:return:
	"""

	highlightline = lineobject.index
	citation = locusintocitation(workobject, lineobject.locustuple())

	name = formatname(workobject, authorobject)
	title = workobject.title

	citationincontext = FormattedSearchResult(-1, name, title, citation, lineobject.universalid, [])

	environs = simplecontextgrabber(workobject, highlightline, linesofcontext, curs)

	for foundline in environs:
		foundline = dblineintolineobject(foundline)
		if foundline.index == highlightline:
			foundline.accented = highlightsearchterm(foundline, searchterm, 'match')
			foundline.accented = '<span class="highlight">{fla}</span>'.format(fla=foundline.accented)
		if proximate != '' and searchtype == 'proximity':
			# negative proximity ('not near') does not need anything special here: you simply never meet the condition
			if re.search(proximate, foundline.accented) or re.search(proximate, foundline.stripped):
				foundline.accented = highlightsearchterm(foundline, proximate, 'proximate')
		citationincontext.lineobjects.append(foundline)

	return citationincontext


def htmlifysearchfinds(listofsearchresultobjects):
	"""
	it is too painful to let JS turn this information into HTML
	the Flask template used to do this work, now this does it

	send me a list of FormattedSearchResult objects

	:param listofsearchresultobjects:
	:return:
	"""

	resultsashtml = []

	linehtmltemplate = '<span class="locus">{lc}</span>&nbsp;<span class="foundtext">{ft}</span><br />'

	if hipparchia.config['DBDEBUGMODE'] == 'yes':
		linehtmltemplate = '<smallcode>{id}</smallcode>&nbsp;' + linehtmltemplate

	for ro in listofsearchresultobjects:
		if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
			h = [linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.showlinehtml()) for ln in ro.lineobjects]
		else:
			h = [linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.accented) for ln in ro.lineobjects]
		resultsashtml.append(ro.getlocusthml() + '\n'.join(h))

	html = '\n'.join(resultsashtml)

	return html


def jstoinjectintobrowser(listofsearchresultobjects):
	"""
	the clickable urls don't work without inserting new js into the page to catch the clicks
	need to match the what we used to get via the flask template
	:return:
	"""

	listofurls = [ro.clickurl for ro in listofsearchresultobjects]

	jso = ['document.getElementById("{u}").onclick = openbrowserfromclick;'.format(u=url) for url in listofurls]
	jsoutput = '\n'.join(jso)

	return jsoutput


def nocontextresultformatter(hitdict, authordict, workdict, seeking, proximate, searchtype, activepoll):
	"""

	simply spit out the finds, don't put them in context: speedier and visually more compact

	:param hitdict:
	:param authordict:
	:param workdict:
	:param seeking:
	:param proximate:
	:param searchtype:
	:param activepoll:
	:return:
	"""

	if len(hitdict) > int(session['maxresults']):
		limit = int(session['maxresults'])
	else:
		limit = len(hitdict)

	searchresultobjects = []

	for i in range(0, limit):
		lineobject = hitdict[i]
		authorobject = authordict[lineobject.wkuinversalid[0:6]]
		wid = lineobject.wkuinversalid
		workobject = workdict[wid]
		name = formatname(workobject, authorobject)
		citation = locusintocitation(workobject, lineobject.locustuple())

		lineobject.accented = highlightsearchterm(lineobject, seeking, 'match')
		if proximate != '' and searchtype == 'proximity':
			# negative proximity ('not near') does not need anything special here: you simply never meet the condition
			if re.search(proximate, lineobject.accented) or re.search(proximate, lineobject.stripped):
				lineobject.accented = highlightsearchterm(lineobject, proximate, 'proximate')

		searchresultobjects.append(FormattedSearchResult(i+1, name, workobject.title, citation, lineobject.universalid, [lineobject]))

	return searchresultobjects


def nocontexthtmlifysearchfinds(listofsearchresultobjects):
	"""
	it is too painful to let JS turn this information into HTML
	the Flask template used to do this work, now this does it

	send me a list of FormattedSearchResult objects (each should contain only one associated line)

	:param listofsearchresultobjects:
	:return:
	"""

	resultsashtml = ['<table>']

	linehtmltemplate = '<span class="foundtext">{ft}</span>'

	tabelrowtemplate = """
	<tr class="{rs}">
		<td>{cit}
		</td>
		<td class="leftpad">
			{h}
		</td>
	</tr>
	"""


	if hipparchia.config['DBDEBUGMODE'] == 'yes':
		linehtmltemplate = '<smallcode>{id}</smallcode>&nbsp;' + linehtmltemplate

	count = 0
	for ro in listofsearchresultobjects:
		count += 1
		if count % 3 == 0:
			rowstyle = 'nthrow'
		else:
			rowstyle = 'regular'
		ln = ro.lineobjects[0]
		if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
			h = linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.showlinehtml())
		else:
			h = linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.accented)

		citation = ro.citationhtml(ln.locus())
		resultsashtml.append(tabelrowtemplate.format(rs=rowstyle, cit=citation, h=h))

	resultsashtml.append('</table>')

	html = '\n'.join(resultsashtml)

	return html


def formatname(workobject, authorobject):
	"""
	
	shift name depending on type of hit
	
	neede by
		formattedcitationincontext()
		nocontexthtmlifysearchfinds()
	
	:param workobject: 
	:param authorobject: 
	:return: 
	"""

	if workobject.isliterary():
		name = authorobject.shortname
	else:
		name = '[<span class="date">{d}</span>] {n}'.format(n=authorobject.idxname, d=workobject.bcedate())

	return name


def getpublicationinfo(workobject, cursor):
	"""
	what's in a name?
	:param workobject:
	:return: html for the bibliography
	"""

	uid = workobject.universalid
	query = 'SELECT publication_info FROM works WHERE universalid = %s'
	data = (uid,)
	cursor.execute(query, data)
	pi = cursor.fetchone()
	pi = pi[0]

	publicationhtml = formatpublicationinfo(pi)

	return publicationhtml


def formatpublicationinfo(pubinfo):
	"""
	in:
		<volumename>FHG </volumename>4 <press>Didot </press><city>Paris </city><year>1841–1870</year><pages>371 </pages><pagesintocitations>Frr. 1–2</pagesintocitations><editor>Müller, K. </editor>
	out:
		<span class="pubvolumename">FHG <br /></span><span class="pubpress">Didot , </span><span class="pubcity">Paris , </span><span class="pubyear">1841–1870. </span><span class="pubeditor"> (Müller, K. )</span>

	:param pubinfo:
	:return:
	"""

	maxlinelen = 120

	tags = [
		{'volumename': ['', '. ']},
		{'press': ['', ', ']},
		{'city': ['', ', ']},
		{'year': ['', '. ']},
		{'series': ['', '']},
		{'editor': [' (', ')']},
		# {'pages':[' (',')']}
	]

	publicationhtml = ''

	for t in tags:
		tag = next(iter(t.keys()))
		val = next(iter(t.values()))
		seek = re.compile('<' + tag + '>(.*?)</' + tag + '>')
		if re.search(seek, pubinfo):
			found = re.search(seek, pubinfo)
			foundinfo = avoidlonglines(found.group(1), maxlinelen, '<br />', [])
			publicationhtml += '<span class="pub{t}">{va}{fi}{vb}</span>'.format(t=tag, va=val[0], fi=foundinfo, vb=val[1])

	return publicationhtml


def avoidlonglines(string, maxlen, splitval, stringlist=[]):
	"""

	Authors like Livy can swallow the browser window by sending 351 characters worth of editors to one of the lines

	break up a long line into multiple lines by splitting every N characters

	splitval will be something like '<br />' or '\n'

	:param string:
	:param maxlen:
	:return:
	"""

	breakcomeswithinamarkupseries = re.compile(r'^\s[^\s]{1,}>')

	if len(string) < maxlen:
		stringlist.append(string)
		newstringhtml = splitval.join(stringlist)
	else:
		searchzone = string[0:maxlen]
		stop = False
		stopval = len(string)

		for c in range(maxlen-1,-1,-1):
			if searchzone[c] == ' ' and stop == False and re.search(breakcomeswithinamarkupseries, string[c:]) is None:
				stop = True
				stringlist.append(string[0:c])
				stopval = c
		newstringhtml = avoidlonglines(string[stopval+1:], maxlen, splitval, stringlist)

	return newstringhtml