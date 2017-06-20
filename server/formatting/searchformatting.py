# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque
from copy import deepcopy

from server import hipparchia
from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import dblineintolineobject, setconnection
from server.formatting.bibliographicformatting import formatname
from server.hipparchiaobjects.helperobjects import SearchResult


def buildresultobjects(hitdict, authordict, workdict, searchobject, activepoll):
	"""
	build result objects for the lines you have found

	this version will send you through bulkenvironsfetcher() which will ensure that you do not make 2500 queries for 2500 results

	instead you will make one query per author table

	this is MUCH faster: 25-50x faster if you go wild and allow for thousands of results

	the hitdict is a collection of line objects where the key is the proper sort order for the results
		hitdict {0: <server.hipparchiaclasses.dbWorkLine object at 0x103dd17b8>, 1: <server.hipparchiaclasses.dbWorkLine object at 0x103dd1780>, 3: ...}

	returns a sorted list of SearchResult objects

	:return:
	"""

	# for h in hitdict.keys():
	#	print(h,hitdict[h].universalid, hitdict[h].accented)

	so = searchobject

	hitdict = {h: hitdict[h] for h in hitdict if h < int(so.session['maxresults'])}

	resultlist = []
	for h in hitdict:
		lo = hitdict[h]
		wo = workdict[lo.wkuinversalid]
		ao = authordict[lo.authorid]
		n = formatname(wo, ao)
		t = wo.title
		c = locusintocitation(wo, lo.locustuple())
		resultlist.append(SearchResult(h+1, n, t, c, hitdict[h].universalid, [hitdict[h]]))

	if so.context == 0:
		# no need to find the environs
		return resultlist

	else:
		# aggregate hits by author table so we can search each table once instead of 100x
		hitlocations = {}
		for r in resultlist:
			table = r.lineobjects[0].authorid
			try:
				hitlocations[table].append(r)
			except:
				hitlocations[table] = [r]

		activepoll.allworkis(len(hitlocations))
		activepoll.remain(len(hitlocations))

		updatedresultlist = deque()
		count = 0

		for table in hitlocations:
			resultswithenvironments = bulkenvironsfetcher(table, hitlocations[table], so.context)
			updatedresultlist.extend(resultswithenvironments)
			count += 1
			activepoll.remain(len(hitlocations)-count)

		updatedresultlist = sorted(updatedresultlist, key=lambda x: x.hitnumber)

		# toss lines that are not part of this work: 10 lines of context in the inscriptions will grab neighboring
		# documents otherwise
		for r in updatedresultlist:
			r.lineobjects = [l for l in r.lineobjects if l.wkuinversalid == r.getworkid()]

		return updatedresultlist


def bulkenvironsfetcher(table, searchresultlist, context):
	"""

	given a list of SearchResult objects, populate the lineobjects of each SearchResult with their contexts

	:param hitlocations:
	:param context:
	:return:
	"""

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	tosearch = deque()
	reversemap = {}

	for r in searchresultlist:
		resultnumber = r.hitnumber
		focusline = r.getindex()
		environs = list(range(int(focusline - (context / 2)), int(focusline + (context / 2))+1))
		tosearch.extend(environs)
		rmap = {e: resultnumber for e in environs}
		reversemap.update(rmap)
		r.lineobjects = []

	tosearch = [str(x) for x in tosearch]

	tempquery = 'CREATE TEMPORARY TABLE {au}_includelist AS SELECT values AS includeindex FROM unnest(ARRAY[{lines}]) values'.format(
		au=table, lines = ','.join(tosearch))
	curs.execute(tempquery)

	q = 'SELECT * FROM {au} WHERE EXISTS (SELECT 1 FROM {au}_includelist incl WHERE incl.includeindex = {au}.index)'.format(au=table)
	curs.execute(q)
	results = curs.fetchall()
	lines = [dblineintolineobject(r) for r in results]
	indexedlines = {l.index: l for l in lines}

	for r in searchresultlist:
		environs = list(range(int(r.getindex() - (context / 2)), int(r.getindex() + (context / 2)) + 1))
		for e in environs:
			try:
				r.lineobjects.append(indexedlines[e])
			except KeyError:
				# you requested a line that was outside of the scope of the table
				# so there was no result and the key will not match a find
				pass

	curs.close()

	return searchresultlist


def flagsearchterms(searchresultobject, skg, prx, searchobject):
	"""

	take the list of lineobjects inside a searchresultobject and highlight the search terms

	skg and prx come from compilesearchtermequivalent()

	:param searchresultobject:
	:param searchobject:
	:return:
	"""
	so = searchobject

	linelist = searchresultobject.lineobjects
	highlightindex = searchresultobject.getindex()
	newlineobjects = []
	for foundline in linelist:
		# need a copy because otherwise you will see two+ highlighted lines in a result if this result abuts another one
		# a highlighted foundline2 of result2 is showing up in result1 in addition to foundline1
		fl = deepcopy(foundline)
		if fl.index == highlightindex:
			fl.accented = highlightsearchterm(fl, skg, 'match')
			if so.context > 0:
				fl.accented = '<span class="highlight">{fla}</span>'.format(fla=fl.accented)
		if so.proximate != '' and so.searchtype == 'proximity':
			# negative proximity ('not near') does not need anything special here: you simply never meet the condition
			if re.search(so.termtwo, fl.accented) or re.search(so.termtwo, fl.stripped):
				fl.accented = highlightsearchterm(fl, prx, 'proximate')
		newlineobjects.append(fl)

	return newlineobjects


def highlightsearchterm(lineobject, regexequivalent, spanname):
	"""

	html markup for the search term in the line so it can jump out at you

	regexequivalent is compiled via compilesearchtermequivalent()

	in order to properly highlight a polytonic word that you found via a unaccented search you need to convert:
		ποταμον
	into:
		([πΠ][οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ][τΤ][αἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ][μΜ][οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ][νΝ])

	:param lineobject:
	:param searchterm:
	:param spanname:
	:return:
	"""

	line = lineobject.accented
	newline = line
	line = newline

	find = re.search(regexequivalent, line)
	try:
		newline = '{ls}<span class="{sp}">{fg}</span>{le}'.format(ls=line[0:find.start()], sp=spanname, fg=find.group(), le=line[find.end():])
	except:
		# the find was almost certainly a hyphenated last word: 'pro-' instead of 'profuit'
		hyph = lineobject.hyphenated
		find = re.search(regexequivalent, hyph)
		try:
			newline = line+'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(&nbsp;match:&nbsp;{hs}<span class="{sn}">{fg}</span>{he}&nbsp;)'.format(hs=hyph[0:find.start()], sn=spanname, fg=find.group(), he=hyph[find.end():])
		except:
			pass
		# print('nofind',searchtermequivalent, line, lineobject.lastword('contents'))

	return newline


def compilesearchtermequivalent(searchterm):
	"""

	in order to properly highlight a polytonic word that you found via a unaccented search you need to convert:
		ποταμον
	into:
		([πΠ][οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ][τΤ][αἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ][μΜ][οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ][νΝ])

	NB: this function also takes care of capitalization issues: the search is always lower case, but results will be marked
	without regard to their case: 'Antonius', 'Kalendas', etc.

	:param searchterm:
	:return:
	"""

	# need to avoid having '\s' turn into '\[Ss]', etc.
	searchterm = re.sub(r'\\s', '😀', searchterm)
	searchterm = re.sub(r'\\w', '👽', searchterm)

	equivalents = {
		'α': '[αἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάᾈᾉᾊᾋᾌᾍᾎᾏἈἉἊἋἌἍἎἏΑ]',
		'β': '[βΒ]',
		'ψ': '[ψΨ]',
		'δ': '[δΔ]',
		'ε': '[εἐἑἒἓἔἕὲέΕἘἙἚἛἜἝ]',
		'φ': '[φΦ]',
		'γ': '[γΓ]',
		'η': '[ηᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἡἦΗᾘᾙᾚᾛᾜᾝᾞᾟἨἩἪἫἬἭἮἯ]',
		'ι': '[ιἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗΐἸἹἺἻἼἽἾἿΙ]',
		'ξ': '[ξΞ]',
		'κ': '[κΚ]',
		'λ': '[λΛ]',
		'μ': '[μΜ]',
		'ν': '[νΝ]',
		'ο': '[οὀὁὂὃὄὅόὸΟὈὉὊὋὌὍ]',
		'π': '[πΠ]',
		'ρ': '[ρΡῥῬ]',
		'ϲ': '[ϲϹ]',
		'σ': '[ϲϹ]',
		'ς': '[ϲϹ]',
		'τ': '[τΤ]',
		'υ': '[υὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺὙὛὝὟΥ]',
		'ω': '[ωὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼΩᾨᾩᾪᾫᾬᾭᾮᾯὨὩὪὫὬὭὮὯΩ]',
		'χ': '[χΧ]',
		'θ': '[θΘ]',
		'ζ': '[ζΖ]',
		'b': '[Bb]',
		'c': '[Cc]',
		'd': '[Dd]',
		'f': '[Ff]',
		'g': '[Gg]',
		'h': '[Hh]',
		'j': '[JjIi]',
		'k': '[Kk]',
		'l': '[Ll]',
		'm': '[Mm]',
		'n': '[Nn]',
		'p': '[Pp]',
		'q': '[Qq]',
		'r': '[Rr]',
		's': '[Ss]',
		't': '[Tt]',
		'w': '[Ww]',
		'x': '[Xx]',
		'y': '[Yy]',
		'z': '[Zz]',
		'a': '[Aaáä]',
		'e': '[Eeéë]',
		'i': '[IiíïJj]',
		'o': '[Ooóö]',
		'u': '[UuüVv]',
		'v': '[VvUuü]'
	}

	searchtermequivalent = ''
	searchterm = re.sub(r'(^\s|\s$)', '', searchterm)
	for c in searchterm:
		try:
			c = equivalents[c]
		except KeyError:
			pass
		searchtermequivalent += c
	# searchtermequivalent = '(^|)('+searchtermequivalent+')($|)'
	searchtermequivalent = re.sub(r'😀', '\s', searchtermequivalent)
	searchtermequivalent = re.sub(r'👽', '\w', searchtermequivalent)
	searchtermequivalent = '({s})'.format(s=searchtermequivalent)

	try:
		searchtermequivalent = re.compile(searchtermequivalent)
	except:
		# if you try something like '(Xἰ' you will produce an error:
		# sre_constants.error: missing ), unterminated subpattern at position 0
		searchtermequivalent = None

	return searchtermequivalent


def htmlifysearchfinds(listofsearchresultobjects):
	"""

	send me a list of SearchResult objects

	return some html

	:param listofsearchresultobjects:
	:return:
	"""

	resultsashtml = []

	linehtmltemplate = '<span class="locus">{lc}</span>&nbsp;<span class="foundtext">{ft}</span><br />'

	if hipparchia.config['DBDEBUGMODE'] == 'yes':
		linehtmltemplate = '<smallcode>{id}</smallcode>&nbsp;' + linehtmltemplate

	for ro in listofsearchresultobjects:
		firstline = ro.lineobjects[0]
		firstline.accented = unbalancedspancleaner(firstline.accented)
		if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
			passage = [linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.showlinehtml())
			           for ln in ro.lineobjects]
		elif hipparchia.config['COLORBRACKETEDTEXT'] == 'yes':
			passage = [linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.markeditorialinsersions())
			           for ln in ro.lineobjects]
		else:
			passage = [linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.accented)
			           for ln in ro.lineobjects]
		passage = unbalancedspancleaner('\n'.join(passage))
		resultsashtml.append(ro.getlocusthml())
		resultsashtml.append(passage)

	html = '\n'.join(resultsashtml)

	return html


def nocontexthtmlifysearchfinds(listofsearchresultobjects):
	"""

	send me a list of SearchResult objects

	return some html

	:param listofsearchresultobjects:
	:return:
	"""

	resultsashtml = ['<table>']

	linehtmltemplate = '<span class="foundtext">{ft}</span>'

	if hipparchia.config['DBDEBUGMODE'] == 'yes':
		linehtmltemplate = '<smallcode>{id}</smallcode>&nbsp;' + linehtmltemplate

	tabelrowtemplate = """
	<tr class="{rs}">
		<td>{cit}
		</td>
		<td class="leftpad">
			{h}
		</td>
	</tr>
	"""

	count = 0
	for ro in listofsearchresultobjects:
		count += 1
		if count % 3 == 0:
			rowstyle = 'nthrow'
		else:
			rowstyle = 'regular'
		ln = ro.lineobjects[0]
		ln.accented = unbalancedspancleaner(ln.accented)
		if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
			h = linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.showlinehtml())
		else:
			h = linehtmltemplate.format(id=ln.universalid, lc=ln.locus(), ft=ln.accented)

		citation = ro.citationhtml(ln.locus())
		resultsashtml.append(tabelrowtemplate.format(rs=rowstyle, cit=citation, h=h))

	resultsashtml.append('</table>')

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
	jsoutput = '\n\t'.join(jso)

	return jsoutput


def unbalancedspancleaner(html):
	"""

	unbalanced spans inside of result chunks: ask for 4 lines of context and search for »ἀδύνατον γ[άὰ]ρ«
	this will cough up two examples of the problem in Alexander, In Aristotelis analyticorum priorum librum i commentarium

	the first line of context shows spans closing here that were opened in a previous line

		<span class="locus">98.14</span>&nbsp;<span class="foundtext">ὅρων ὄντων πρὸϲ τὸ μέϲον.</span></span></span><br />

	the last line of the context is opening a span that runs into the next line of the text where it will close
	but since the next line does not appear, the span remains open. This will make the next results bold + italic + ...

		<span class="locus">98.18</span>&nbsp;<span class="foundtext"><hmu_roman_in_a_greek_text>p. 28a18 </hmu_roman_in_a_greek_text><span class="title"><span class="expanded">Καθόλου μὲν οὖν ὄντων, ὅταν καὶ τὸ Π καὶ τὸ Ρ παντὶ</span><br />

	the solution:
		open anything that needs opening: this needs to be done with the first line
		close anything left hanging: this needs to be done with the whole passage

	return the html with these supplemental tags

	:param html:
	:return:
	"""

	o = re.compile(r'<span')
	c = re.compile(r'</span>')

	opened = len(re.findall(o,html))
	closed = len(re.findall(c,html))

	supplement = ''

	if closed > opened:
		for i in range(0, closed - opened):
			supplement += '<span class="htmlbalancingsupplement">'
		html = supplement + html

	if opened > closed:
		for i in range(0,opened-closed):
			supplement += '</span>'
		html = html + supplement

	return html
