# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import Dict, List

from flask import session

from server import hipparchia
from server.dbsupport.lexicaldbfunctions import findcountsviawordcountstable
from server.hipparchiaobjects.dbtextobjects import MorphPossibilityObject
from server.hipparchiaobjects.wordcountobjects import dbHeadwordObject, dbWordCountObject


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


	sections = {'authors': {'items': authors, 'classone': 'authorsummary', 'classtwo': 'authorsum', 'label': 'Citations from'},
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


def formatparsinginformation(possibilitieslist: List[MorphPossibilityObject]) -> str:
	"""
	sample output:

	(1)  fores (from fores, to bore):
	pres subj act 2nd sg
	(2)  fores (from fores):
	[a] fem acc pl
	[b] fem nom/voc pl
	(3)  fores (from fores):
	imperf subj act 2nd sg
	(4)  fores (from fores, a door):
	[a] masc/fem acc pl
	[b] masc/fem nom/voc pl
	[c] fem acc pl
	[d] fem nom/voc pl

	:param possibilitieslist:
	:return:
	"""

	morphabletemplate = """
	<table class="morphtable">
		<tbody>
			{trs}
		</tbody>
	</table>
	"""

	xdftemplate = """
	<span class="dictionaryform">{df}</span>&nbsp;:&nbsp;
	from <span class="baseform">{bf}</span>
	<span class="baseformtranslation">{xlate}</span>{xref}:
	"""

	distinct = set([p.xref for p in possibilitieslist])

	count = 0
	countchar = int('0030', 16)  # '1' (after you add 1)
	subcountchar = int('0061', 16)  # 'a' (when counting from 0)
	if len(distinct) > 1:
		obsvstring = '\n<a class="parsing" href="{link}"><span class="obsv">({ct})&nbsp;{xdf}</span></a>'
	else:
		obsvstring = '\n<a class="parsing" href="{link}"><span class="obsv">{xdf}</span></a>'
	morphhtml = list()

	for d in distinct:
		count += 1
		outputlist = list()
		subentries = [p for p in possibilitieslist if p.xref == d]
		subentries = sorted(subentries, key=lambda x: x.number)

		firstsubentry = subentries[0]

		bf = firstsubentry.getbaseform()
		if firstsubentry.gettranslation() and firstsubentry.gettranslation() != ' ':
			xlate = '&nbsp;(“{tr}”)'.format(tr=firstsubentry.gettranslation())
		else:
			xlate = str()

		if session['debugparse']:
			xrefinfo = '<code>[{x}]</code>'.format(x=firstsubentry.xref)
		else:
			xrefinfo = str()

		xdf = xdftemplate.format(df=firstsubentry.observed, bf=bf, xlate=xlate, xref=xrefinfo)
		outputlist.append(obsvstring.format(ct=chr(count + countchar), xdf=xdf, link="#{a}_{b}".format(a=bf, b=firstsubentry.xref)))

		if len(subentries) == 1:
			analysischunks = firstsubentry.getanalysislist()[0].split(' ')
			analysischunks = ['\n<td class="morphcell">{a}</td>'.format(a=a) for a in analysischunks]
			tr = '<tr><td class="morphcell invisible">[{ct}]</td>{tds}\n</tr>'.format(ct=chr(subcountchar), tds=''.join(analysischunks))
			outputlist.append(morphabletemplate.format(trs=tr))
		else:
			rows = list()
			for e in range(len(subentries)):
				analysischunks = subentries[e].getanalysislist()[0].split(' ')
				analysischunks = ['<td class="morphcell">{a}</td>'.format(a=a) for a in analysischunks]
				analysischunks = ['<td class="morphcell labelcell">[{ct}]</td>'.format(ct=chr(e + subcountchar))] + analysischunks
				tr = '<tr>{tds}</tr>'.format(tds=''.join(analysischunks))
				rows.append(tr)
			outputlist.append(morphabletemplate.format(trs='\n'.join(rows)))
		distincthtml = '\n'.join(outputlist)
		morphhtml.append(distincthtml)

	morphhtml = '\n'.join(morphhtml)

	return morphhtml


def getobservedwordprevalencedata(dictionaryword):
	"""

	:param dictionaryword:
	:return:
	"""

	if not session['available']['wordcounts_0']:
		return str()

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

	if isinstance(w, dbHeadwordObject):

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

		if hipparchia.config['COLLAPSEDGENRECOUNTS']:
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
