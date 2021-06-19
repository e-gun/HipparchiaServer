# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from flask import session

from server import hipparchia
from server.dbsupport.lexicaldbfunctions import findcountsviawordcountstable
from server.formatting.miscformatting import htmlcommentdecorator
from server.hipparchiaobjects.dbtextobjects import MorphPossibilityObject
from server.hipparchiaobjects.wordcountobjects import dbHeadwordObject, dbWordCountObject


@htmlcommentdecorator
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
	flagged = wordentryobject.flaggedsenselist
	phrases = wordentryobject.phraselist

	labelformultipleitems = '<div class="{cl}"><span class="lexiconhighlight">{lb}</span><br />'
	labelforoneitem = '<span class="{cl}">{item}</span><br />'
	itemtext = '\t<span class="{cl}">({ct})&nbsp;{item}</span><br />'


	sections = {'authors': {'items': authors, 'classone': 'authorsummary', 'classtwo': 'authorsum', 'label': 'Citations from'},
				 'quotes': {'items': quotes, 'classone': 'quotessummary', 'classtwo': 'quotesum', 'label': 'Quotes'},
				 'senses': {'items': senses, 'classone': 'sensesummary', 'classtwo': 'sensesum', 'label': 'Senses'},
				 'phrases': {'items': phrases, 'classone': 'phrasesummary', 'classtwo': 'phrasesum', 'label': 'Phrases'},
	             'flaggedsenses': {'items': flagged, 'classone': 'quotessummary', 'classtwo': 'quotesum', 'label': 'Flagged Senses'},
				}

	outputlist = list()

	summarizing = ['senses', 'flaggedsenses', 'phrases', 'authors', 'quotes']

	if not session['phrasesummary']:
		summarizing.remove('phrases')

	for section in summarizing:
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
	summarystring = summarystring + '<br>'

	return summarystring


@htmlcommentdecorator
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
	<span class="obsv">
		<span class="dictionaryform">{df}</span>&nbsp;:&nbsp;
		<a class="parsing" href="RE_SUB_LINK"><span class="obsv">
			from <span class="baseform">{bf}</span>
			<span class="baseformtranslation">{xlate}</span>{xref}
		</a>
	</span>
	"""

	distinct = set([p.xref for p in possibilitieslist])

	count = 0
	countchar = int('0030', 16)  # '1' (after you add 1)
	subcountchar = int('0061', 16)  # 'a' (when counting from 0)
	if len(distinct) > 1:
		obsvstring = '\n({ct})&nbsp;{xdf}'
	else:
		obsvstring = '\n{xdf}'
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
		xdf = re.sub(r'RE_SUB_LINK', '#{a}_{b}'.format(a=bf, b=firstsubentry.xref), xdf)
		outputlist.append(obsvstring.format(ct=chr(count + countchar), xdf=xdf))

		if len(subentries) == 1:
			analysischunks = firstsubentry.anal.split(' ')
			analysischunks = ['\n<td class="morphcell">{a}</td>'.format(a=a) for a in analysischunks]
			tr = '<tr><td class="morphcell invisible">[{ct}]</td>{tds}\n</tr>'.format(ct=chr(subcountchar), tds=str().join(analysischunks))
			outputlist.append(morphabletemplate.format(trs=tr))
		else:
			rows = list()
			analyses = list()
			for e in range(len(subentries)):
				# unfortunately you can get dupes in here...
				anal = subentries[e].anal.split(' ')  # e.g. ['masc', 'acc', 'sg']
				formatted = ['<td class="morphcell">{a}</td>'.format(a=a) for a in anal]
				analyses.append(str().join(formatted))
				analyses = list(set(analyses))
			analysiscount = len(analyses)
			if analysiscount > 1:
				for a in range(analysiscount):
					label = ['<td class="morphcell labelcell">[{ct}]</td>'.format(ct=chr(a + subcountchar))]
					analysischunks = label + [analyses[a]]
					tr = '<tr>{tds}</tr>'.format(tds=str().join(analysischunks))
					rows.append(tr)
			elif analysiscount == 1:
				rows.append('<tr>{tds}</tr>'.format(tds=analyses[0]))
			outputlist.append(morphabletemplate.format(trs='\n'.join(rows)))
		distincthtml = '\n'.join(outputlist)
		morphhtml.append(distincthtml)

	morphhtml = '\n'.join(morphhtml)

	return morphhtml


def getobservedwordprevalencedata(dictionaryword) -> str:
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


@htmlcommentdecorator
def formatprevalencedata(wordcountobject) -> str:
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
