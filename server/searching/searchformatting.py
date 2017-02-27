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
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject, setconnection
from server.formatting_helper_functions import formatpublicationinfo
from server.hipparchiaclasses import FormattedSearchResult


def cleansearchterm(seeking):
	"""
	turn sigma into antisigma, etc
	:param searchterm:
	:return:
	"""

	seeking = re.sub('σ|ς', 'ϲ', seeking)
	if session['accentsmatter'] == 'no':
		seeking = re.sub('v', 'u', seeking)

	# possible, but not esp. desirable:
	# seeking = re.sub('VvUu', '(u|v|U|v)', seeking)

	return seeking


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


def aggregatelines(firstline, lastline, cursor, audbname):
	"""
	build searchable clumps of words spread over various lines

	:param firstline:
	:param lastline:
	:param cursor:
	:param workdbname:
	:return:
	"""

	# transitional until all code is 'monolithic'
	audbname = audbname[0:6]

	query = 'SELECT * FROM ' + audbname + ' WHERE index >= %s AND index <= %s'
	data = (firstline, lastline)
	cursor.execute(query, data)
	lines = cursor.fetchall()

	lineobjects = [dblineintolineobject(l) for l in lines]

	aggregate = ''
	if session['accentsmatter'] == 'yes':
		for line in lineobjects:
			aggregate += line.polytonic + ' '
	else:
		for line in lineobjects:
			aggregate += line.stripped + ' '

	aggregate = re.sub(r'\s\s', r' ', aggregate)

	return aggregate


def formatauthinfo(authorobject):
	"""
	ao data into html
	:param authorobject:
	:return:
	"""
	n = '<span class="emph">{n}</span>'.format(n=authorobject.shortname)
	d = '[id: {id}]<br />'.format(id=authorobject.universalid[2:])
	if authorobject.genres is not None and authorobject.genres != '':
		g = 'classified among: {g}; '.format(g=authorobject.genres)
	else:
		g = ''

	if authorobject.universalid[0:2] in ['gr', 'in', 'dp']:
		try:
			if float(authorobject.converted_date) == 2000:
				fl = '"Varia" are not assigned to a date'
			elif float(authorobject.converted_date) == 2500:
				fl = '"Incerta" are not assigned to a date'
			elif float(authorobject.converted_date) > 0:
				fl = 'assigned to approx date: {fl} C.E.'.format(fl=str(authorobject.converted_date))
				fl += ' (derived from "{rd}")'.format(rd=authorobject.recorded_date)
			elif float(authorobject.converted_date) < 0:
				fl = 'assigned to approx date: {fl} B.C.E.'.format(fl=str(authorobject.converted_date[1:]))
				fl += ' (derived from "{rd}")'.format(rd=authorobject.recorded_date)
		except:
			# there was no f and so no int(f)
			fl = ''
	else:
		fl = ''

	authinfo = n + '&nbsp;' + d + '&nbsp;' + g + fl

	return authinfo


def woformatworkinfo(workobject):
	"""
	dbdata into html
	send me: universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""

	p = formatpublicationinfo(workobject.publication_info)

	n = '({n})&nbsp;'.format(n=workobject.universalid[-3:])
	t = '<span class="title">{t}</span> '.format(t=workobject.title)

	if workobject.workgenre is not None:
		g = '[{g}]&nbsp;'.format(g=workobject.workgenre)
	else:
		g = ''

	if workobject.wordcount is not None:
		c = '[' + format(workobject.wordcount, ',d') + ' wds]'
	else:
		c = ''

	try:
		dateval = int(workobject.converted_date)
	except:
		dateval = 9999

	if dateval < 1500:
		if dateval > 0:
			suffix = 'CE'
			d = '(assigned to {cd} {fx})'.format(cd=str(workobject.converted_date), fx=suffix)
		else:
			suffix = 'BCE'
			d = '(assigned to {cd} {fx})'.format(cd=str(workobject.converted_date[1:]), fx=suffix)
	else:
		d = ''

	if len(p) > 0:
		workinfo = n + t + g + c + d + '<br />' + p + '<br />'
	else:
		workinfo = n + t + g + c + d + '<br />'

	return workinfo


def formatauthorandworkinfo(authorname, workobject):
	"""
	dbdata into html
	send me: authorname + universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""

	a = authorname
	t = '<span class="italic">{t}</span> '.format(t=workobject.title)

	c = workobject.wordcount

	if c is not None:
		c = '[' + format(c, ',d') + ' wds]'
	else:
		c = ''

	authorandworkinfo = a + ', ' + t + c + '<br />\n'

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

	workbundles = []
	if len(hitdict) > int(session['maxresults']):
		limit = int(session['maxresults'])
	else:
		limit = len(hitdict)

	criteria = {'ctx': linesofcontext, 'seek': seeking, 'prox': proximate, 'type': searchtype}

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

	workers = hipparchia.config['WORKERS']

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
		except:
			# IndexError: pop from empty list
			bundle = None

		if bundle is not None:
			citwithcontext = formattedcitationincontext(bundle['lo'], bundle['wo'], bundle['ao'], criteria['ctx'],
														criteria['seek'], criteria['prox'], criteria['type'], curs)
			citwithcontext.hitnumber = bundle['hitnumber']
			activepoll.remain(bundle['hitnumber'])

			if bundle['hitnumber'] % 100 == 0:
				dbconnection.commit()

			if citwithcontext.formattedlines != []:
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

	if workobject.universalid[0:2] not in ['in', 'dp', 'ch']:
		name = authorobject.shortname
	else:
		name = authorobject.idxname

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
			if re.search(cleansearchterm(proximate), foundline.accented) is not None or re.search(cleansearchterm(proximate), foundline.stripped) is not None:
				foundline.accented = highlightsearchterm(foundline, proximate, 'proximate')
		citationincontext.formattedlines.append(foundline)

	return citationincontext
