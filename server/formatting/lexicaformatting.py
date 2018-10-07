# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import Dict, List

from flask import session

from server import hipparchia
from server.dbsupport.lexicaldbfunctions import probedictionary, grablemmataobjectfor, findparserxref, \
	querytotalwordcounts, findcountsviawordcountstable
from server.formatting.jsformatting import insertlexicalbrowserjs, dictionaryentryjs
from server.hipparchiaobjects.dbtextobjects import dbMorphologyObject
from server.hipparchiaobjects.wordcountobjects import dbWordCountObject, dbHeadwordObject


def formatdictionarysummary(wordentryobject) -> str:
	"""

	turn three lists into html formatting for the summary material that will be inserted at the top of a
	dictionary entry

	:param summarydict:
	:return:
	"""

	authors = wordentryobject.authorlist
	senses = wordentryobject.senselist
	quotes = wordentryobject.quotelist

	labelformultipleitems = '<div class="{cl}"><span class="lexiconhighlight">{lb}</span><br />'
	labelforoneitem = '<span class="{cl}">{item}</span><br />'
	itemtext = '\t<span class="{cl}">({ct})&nbsp;{item}</span><br />'


	sections = {'authors': {'items': authors, 'classone': 'authorsummary', 'classtwo': 'authorsum', 'label': 'Used by'},
				 'quotes': {'items': quotes, 'classone': 'quotessummary', 'classtwo': 'quotesum', 'label': 'Quotes'},
				 'senses': {'items': senses, 'classone': 'sensesummary', 'classtwo': 'sensesum', 'label': 'Senses'}
				}

	outputlist = list()

	for section in ['senses', 'authors', 'quotes']:
		sec = sections[section]
		items = sec['items']
		classone = sec['classone']
		classtwo = sec['classtwo']
		label = sec['label']
		if len(items) > 0:
			outputlist.append(labelformultipleitems.format(cl=classone, lb=label))
		if len(items) == 1:
			outputlist.append(labelforoneitem.format(cl=classtwo, item=items[0]))
		else:
			count = 0
			for i in items:
				count += 1
				outputlist.append(itemtext.format(cl=classtwo, item=i, ct=count))
		if len(items) > 0:
			outputlist.append('</div>')

	summarystring = '\n'.join(outputlist)

	return summarystring


def lexicaldbquickfixes(listofnames: list) -> Dict[str, str]:
	"""
	persus' euripides work numbers are wrong
	deal with that here
	and anything else that pops up
	build a lit of swaps
	:param listofnames:
	:return:
	"""
	
	"""
		perseus
		001 Cyc
		002 Alc
		003 Med
		004 Her
		005 Hip
		006 And
		007 Hec
		008 Sup
		009 HFb
		010 Ion
		011 Tr.
		012 El.
		013 IT
		014 Hel
		015 Ph.
		016 Or.
		017 Ba.
		018 IAb
		019 Rh.
		020 Fr.
		026 Hyp
		031 APb
	
		"gr0006w030";"Fragmenta Oenei"
		"gr0006w031";"Epigrammata"
		"gr0006w032";"Fragmenta Phaethontis incertae sedis"
		"gr0006w033";"Fragmenta"
		"gr0006w034";"Cyclops"
		"gr0006w035";"Alcestis"
		"gr0006w036";"Medea"
		"gr0006w037";"Heraclidae"
		"gr0006w038";"Hippolytus"
		"gr0006w039";"Andromacha"
		"gr0006w040";"Hecuba"
		"gr0006w041";"Supplices"
		"gr0006w042";"Electra"
		"gr0006w043";"Hercules"
		"gr0006w044";"Troiades"
		"gr0006w045";"Iphigenia Taurica"
		"gr0006w046";"Ion"
		"gr0006w047";"Helena"
		"gr0006w048";"Phoenisae"
		"gr0006w049";"Orestes"
		"gr0006w050";"Bacchae"
		"gr0006w051";"Iphigenia Aulidensis"
		"gr0006w052";"Rhesus"
		"gr0006w020";"Fragmenta"
		"gr0006w021";"Fragmenta papyracea"
		"gr0006w022";"Epinicium in Alcibiadem (fragmenta)"
		"gr0006w023";"Fragmenta Phaethontis"
		"gr0006w024";"Fragmenta Antiopes"
		"gr0006w025";"Fragmenta Alexandri"
		"gr0006w026";"Fragmenta Hypsipyles"
		"gr0006w027";"Fragmenta Phrixei (P. Oxy. 34.2685)"
		"gr0006w028";"Fragmenta fabulae incertae"
		"gr0006w029";"Fragmenta"

	"""
	
	substitutes = dict()
	dbfinder = re.compile(r'(..\d\d\d\dw\d\d\d)(.*)')
	
	fixer = {
		# perseus : hipparchia
		'gr0006w001': 'gr0006w034',
		'gr0006w002': 'gr0006w035',
		'gr0006w003': 'gr0006w036',
		'gr0006w004': 'gr0006w037',
		'gr0006w005': 'gr0006w038',
		'gr0006w006': 'gr0006w039',
		'gr0006w007': 'gr0006w040',
		'gr0006w008': 'gr0006w041',
		'gr0006w009': 'gr0006w043',
		'gr0006w010': 'gr0006w046',
		'gr0006w011': 'gr0006w044',
		'gr0006w012': 'gr0006w042',
		'gr0006w013': 'gr0006w045',
		'gr0006w014': 'gr0006w047',
		'gr0006w015': 'gr0006w048',
		'gr0006w016': 'gr0006w036',
		'gr0006w017': 'gr0006w050',
		'gr0006w018': 'gr0006w051',
		'gr0006w019': 'gr0006w052',
		'gr0006w020': 'gr0006w029',
		'gr0006w026': 'gr0006w026',
		'gr0006w031': 'gr0006w031'
	}

	for item in listofnames:
		db = re.search(dbfinder, item)
		if db.group(1) in fixer.keys():
			hipparchiadb = fixer[db.group(1)]
			substitutes[item] = hipparchiadb+db.group(2)

	return substitutes


def multiplelexicalmatchesintohtml(morphologyobject: dbMorphologyObject) -> List[dict]:
	"""

	you have found the word(s), now generate a collection of HTML lines to hand to the JS
	this is a sort of pseudo-page

	first do the parsing results; then do the dictionary results

	observedform:
		nubibus

	matcheslist:
		[('<possibility_1>χρημάτων, χρῆμα<xref_value>128139149</xref_value><transl>need</transl><analysis>neut gen pl</analysis></possibility_1>\n',)]

	interesting problem with alternative latin genitive plurals: they generate a double entry unless you are careful
		(1) iudicium (from jūdiciūm, judicium, a judgment):  neut gen pl
		(2) iudicium (from jūdicium, judicium, a judgment):  neut nom/voc/acc sg

	the xref values help here 42397893 & 42397893

	:param observedform:
	:param morphologyobject:
	:param cursor:
	:return:
	"""

	returnarray = list()
	entriestocheck = dict()
	possibilities = morphologyobject.getpossible()

	# the top part of the HTML: just the analyses
	count = 0
	for p in possibilities:
		count += 1
		# {'50817064': [('nūbibus,nubes', '<transl>a cloud</transl><analysis>fem abl pl</analysis>'), ('nūbibus,nubes', '<transl>a cloud</transl><analysis>fem dat pl</analysis>')], '50839960': [('nūbibus,nubis', '<transl>a cloud</transl><analysis>masc abl pl</analysis>'), ('nūbibus,nubis', '<transl>a cloud</transl><analysis>masc dat pl</analysis>')]}

		# print('theentry',p.entry, p.number, p.gettranslation(), p.getanalysislist())

		# there is a HUGE PROBLEM in the original data here:
		#   [a] 'ὑπό, ἐκ-ἀράω²': what comes before the comma is a prefix to the verb
		#   [b] 'ἠχούϲαϲ, ἠχέω': what comes before the comma is an observed form of the verb
		# when you .split() what do you have at wordandform[0]?

		# you have to look at the full db entry for the word:
		# the number of items in prefixrefs corresponds to the number of prefix checks you will need to make to recompose the verb

		returnarray.append({'value': p.formatconsolidatedgrammarentry(count)})

	# the next will trim the items to check by inducing key collisions
	# p.getbaseform(), p.entry, p.xref: judicium jūdiciūm, judicium 42397893
	# p.getbaseform(), p.entry, p.xref: judicium jūdicium, judicium 42397893

	distinct = dict()
	for p in possibilities:
		distinct[p.xref] = p.getbaseform()

	count = 0
	for d in distinct:
		count += 1
		entriestocheck[count] = distinct[d]

	# look up and format the dictionary entries
	if len(entriestocheck) == 1:
		# sending 0 as the count to browserdictionarylookup() prevents enumeration
		entryashtml = dictonaryentryashtml(0, entriestocheck[1])
		returnarray.append({'value': entryashtml})
	else:
		count = 0
		for entry in entriestocheck:
			count += 1
			entryashtml = dictonaryentryashtml(count, entriestocheck[entry])
			returnarray.append({'value': entryashtml})

	return returnarray


def dictonaryentryashtml(count, seekingentry):
	"""

	look up a word and return an htlm version of its dictionary entry

	count:
		1
	seekingentry:
		judicium
	entryxref:
		42397893

	:param count:
	:param seekingentry:
	:return:
	"""

	outputlist = list()
	clickableentry = str()

	newheadingstr = '<hr /><p class="dictionaryheading">{ent}'
	nextheadingstr = '<hr /><p class="dictionaryheading">({cv})&nbsp;{ent}'
	metricsstr = '&nbsp;<span class="metrics">[{me}]</span>'
	codestr = '&nbsp;<code>[ID: {x}]</code>'
	xrefstr = '&nbsp;<code>[XREF: {x}]</code>'
	notfoundstr = '<br />\n<p class="dictionaryheading">nothing found under <span class="prevalence">{skg}</span></p>\n'
	itemnotfoundstr = '<br />\n<p class="dictionaryheading">({ct}) nothing found under <span class="prevalence">{skg}</span></p>\n'
	fullentrystring = '<br /><br />\n<span class="lexiconhighlight">Full entry:</span><br />'

	navtemplate = """
	<table class="navtable">
	<tr>
		<td class="alignleft">
			<span class="label">Previous: </span>
			<dictionaryentry id="{p}">{p}</dictionaryentry>
		</td>
		<td>&nbsp;</td>
		<td class="alignright">
			<span class="label">Next: </span>
			<dictionaryentry id="{n}">{n}</dictionaryentry>
		</td>
	<tr>
	</table>
	"""

	if re.search(r'[a-z]', seekingentry):
		usedictionary = 'latin'
	else:
		usedictionary = 'greek'

	blankcursor = None
	wordobjects = probedictionary(usedictionary + '_dictionary', 'entry_name', seekingentry, '=', dbcursor=blankcursor, trialnumber=0)

	if wordobjects:
		if len(wordobjects) > 1:
			# supplement count above
			# (1a), (1b), (2) ...
			includesubcounts = True
		else:
			# just use count above
			# (1), (2), (3)...
			includesubcounts = False
		subcount = 0
		for w in wordobjects:
			if not w.isagloss():
				lemmaobject = grablemmataobjectfor(w.entry, usedictionary + '_lemmata', dbcursor=blankcursor)
				w.authorlist = w.generateauthorsummary()
				w.senselist = w.generatesensessummary()
				w.quotelist = w.generatequotesummary(lemmaobject)

			w.constructsensehierarchy()
			w.runbodyxrefsuite()
			w.insertclickablelookups()
			# next is optional, really: a good CSS file will parse what you have thus far
			# (HipparchiaServer v.1.1.2 has the old XML CSS)
			w.xmltohtmlconversions()

			subcount += 1

			if count == 0:
				outputlist.append(newheadingstr.format(ent=w.entry))
			else:
				if includesubcounts:
					countval = str(count) + chr(subcount + 96)
				else:
					countval = str(count)
				outputlist.append(nextheadingstr.format(cv=countval, ent=w.entry))
			if u'\u0304' in w.metricalentry or u'\u0306' in w.metricalentry:
				outputlist.append(metricsstr.format(me=w.metricalentry))
			if session['debuglex'] == 'yes':
				outputlist.append(codestr.format(x=w.id))
				xref = findparserxref(w)
				outputlist.append(xrefstr.format(x=xref))
			outputlist.append('</p>')

			if hipparchia.config['SHOWGLOBALWORDCOUNTS'] == 'yes':
				countobject = querytotalwordcounts(seekingentry)
				if countobject:
					outputlist.append('<p class="wordcounts">Prevalence (all forms): ')
					outputlist.append(formatprevalencedata(countobject))
					outputlist.append('</p>')

			awq = w.authorlist + w.senselist + w.quotelist
			zero = ['0 authors', '0 senses', '0 quotes']
			for z in zero:
				try:
					awq.remove(z)
				except ValueError:
					pass

			if len(awq) == 0:
				# print('zero authors, senses, quotes')
				# either you have turned off summary info or this is basically just a gloss entry
				outputlist.append(w.body)
			else:
				outputlist.append(formatdictionarysummary(w))
				outputlist.append('<p></p>\n')
				outputlist.append(w.grabheadmaterial())
				outputlist.append(fullentrystring)
				outputlist.append(w.grabnonheadmaterial())

			# add in next / previous links
			outputlist.append(navtemplate.format(p=w.preventry, n=w.nextentry))

			cleanedentry = '\n'.join(outputlist)
			clickableentry = insertlexicalbrowserjs(cleanedentry)
	else:
		if count == 0:
			cleanedentry = notfoundstr.format(skg=seekingentry)
		else:
			cleanedentry = itemnotfoundstr.format(ct=count, skg=seekingentry)
		clickableentry = cleanedentry

	entry = clickableentry + dictionaryentryjs()

	return entry


def getobservedwordprevalencedata(dictionaryword):
	"""

	:param dictionaryword:
	:return:
	"""

	if not session['available']['wordcounts_0']:
		return {'value': ''}

	wc = findcountsviawordcountstable(dictionaryword)

	try:
		thiswordoccurs = dbWordCountObject(*wc)
	except:
		return None

	if thiswordoccurs:
		# thiswordoccurs: <server.hipparchiaclasses.dbWordCountObject object at 0x10ad63b00>
		prevalence = 'Prevalence (this form): {pd}'.format(pd=formatprevalencedata(thiswordoccurs))
		thehtml = '<p class="wordcounts">{pr}</p>'.format(pr=prevalence)

		return thehtml
	else:
		return None


def formatprevalencedata(wordcountobject):
	"""

	html for the results

	:param wordcountobject:
	:return:
	"""

	w = wordcountobject
	thehtml = list()

	prevstr = '<span class="prevalence">{a}</span> {b:,}'
	roundedprevstr = '<span class="prevalence">{a}</span> {b:.0f}'
	roundedemphstr = '<span class="emph">{a}</span>&nbsp;({b:.0f})'
	relativestr = '<p class="wordcounts">Relative frequency: <span class="italic">{lb}</span></p>\n'

	maxval = 0
	for key in ['gr', 'lt', 'in', 'dp', 'ch']:
		if w.getelement(key) > maxval:
			maxval = w.getelement(key)
		if w.getelement(key) > 0:
			thehtml.append(prevstr.format(a=w.getlabel(key), b=w.getelement(key)))
	key = 'total'
	if w.getelement(key) != maxval:
		thehtml.append(prevstr.format(a=w.getlabel(key), b=w.getelement(key)))

	thehtml = [' / '.join(thehtml)]

	if type(w) == dbHeadwordObject:

		wts = [(w.getweightedcorpora(key), w.getlabel(key)) for key in ['gr', 'lt', 'in', 'dp', 'ch']]
		allwts = [w[0] for w in wts]
		if sum(allwts) > 0:
			thehtml.append('\n<p class="wordcounts">Weighted distribution by corpus: ')
			wts = sorted(wts, reverse=True)
			wts = [roundedprevstr.format(a=w[1], b=w[0]) for w in wts]
			thehtml.append(' / '.join(wts))
			thehtml.append('</p>')

		wts = [(w.getweightedtime(key), w.gettimelabel(key)) for key in ['early', 'middle', 'late']]
		wts = sorted(wts, reverse=True)
		if wts[0][0]:
			# None was returned if there is no time data for this (Latin) word
			thehtml.append('<p class="wordcounts">Weighted chronological distribution: ')
			wts = [roundedprevstr.format(a=w[1], b=w[0]) for w in wts]
			thehtml.append(' / '.join(wts))
			thehtml.append('</p>')

		if hipparchia.config['COLLAPSEDGENRECOUNTS'] == 'yes':
			genreinfotuples = w.collapsedgenreweights()
		else:
			genreinfotuples = w.sortgenresbyweight()

		if genreinfotuples:
			thehtml.append('<p class="wordcounts">Predominant genres: ')
			genres = list()
			for g in range(0, hipparchia.config['NUMBEROFGENRESTOTRACK']):
				git = genreinfotuples[g]
				if git[1] > 0:
					genres.append(roundedemphstr.format(a=git[0], b=git[1]))
			thehtml.append(', '.join(genres))

		key = 'frq'
		if w.gettimelabel(key) and re.search(r'core', w.gettimelabel(key)) is None:
			thehtml.append(relativestr.format(lb=w.gettimelabel(key)))

	thehtml = '\n'.join(thehtml)

	return thehtml
