# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from flask import session

from server import hipparchia
from server.dbsupport.lexicaldbfunctions import querytotalwordcounts, probedictionary, findcountsviawordcountstable, \
	grablemmataobjectfor, findparserxref
from server.formatting.jsformatting import dictionaryentryjs, insertlexicalbrowserjs
from server.formatting.lexicaformatting import formatdictionarysummary, \
	formatgloss, formatmicroentry, grabheadmaterial, insertbrowserlookups
from server.hipparchiaobjects.dbtextobjects import dbMorphologyObject
from server.hipparchiaobjects.wordcountobjects import dbHeadwordObject, dbWordCountObject


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
	glossstr = '<br />\n<p class="dictionaryheading">{ent}<span class="metrics">[gloss]</span></p>'
	notfoundstr = '<br />\n<p class="dictionaryheading">nothing found under <span class="prevalence">{skg}</span></p>\n'
	itemnotfoundstr = '<br />\n<p class="dictionaryheading">({ct}) nothing found under <span class="prevalence">{skg}</span></p>\n'

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

			definition = ''

			w.runbodyxrefsuite()
			w.bsinsertclickablelookups()
			sensehierarchy = w.bsreturnsensehierarchy()
			subcount += 1

			if not w.isagloss():
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

				if len(w.authorlist + w.senselist + w.quotelist) == 0:
					# either you have turned off summary info or this is basically just a gloss entry
					outputlist.append(formatmicroentry(definition))
				else:
					outputlist.append(formatdictionarysummary(w))
					w.grabheadmaterial()
					outputlist.append('<br /><br />\n<span class="lexiconhighlight">Full entry:</span><br />')
					if sensehierarchy:
						outputlist.extend(sensehierarchy)
					# else:
					# 	outputlist.append(formatmicroentry(definition))
			else:
				outputlist.append(glossstr.format(ent=w.entry))
				outputlist.append(formatgloss(definition))

			# add in next / previous links
			outputlist.append(navtemplate.format(p=w.preventry, n=w.nextentry))

			cleanedentry = '\n'.join(outputlist)
			clickableentry = insertlexicalbrowserjs(cleanedentry)
			# w.printclasses()

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


"""
[probably not] TODO: clickable INS or DDP xrefs in dictionary entries

it looks like we are now in a position where we have the data to make *some* of these papyrus xrefs work

but you will end up with too many dead ends? a test case eventuated in more sorrow than joy

example:

	κύριοϲ

	3  of gods, esp. in the East, Ϲεκνεβτῦνιϲ ὁ κ. θεόϲ PTeb.284.6 (i B.C.);
	Κρόνοϲ κ. CIG4521 (Abila, i A.D.); Ζεὺϲ κ. Supp.Epigr.2.830 (Damascus,
	iii A.D.); κ. Ϲάραπιϲ POxy.110.2 (ii A.D); ἡ κ. Ἄρτεμιϲ IG 4.1124
	(Tibur, ii A.D.); of deified rulers, τοῦ κ. βαϲιλέοϲ θεοῦ OGI86.8
	(Egypt, i B.C.); οἱ κ. θεοὶ μέγιϲτοι, of Ptolemy XIV and Cleopatra,
	Berl.Sitzb.1902.1096: hence, of rulers in general, βαϲιλεὺϲ Ἡρώδηϲ κ.
	OGI415 (Judaea, i B.C.); of Roman Emperors, BGU1200.11 (Augustus),
	POxy.37 i 6 (Claudius), etc.


[success] PTeb.284.6
	select universalid,title from works where title like '%PTeb%284'
		"dp8801w056";"PTebt (Vol 1) - 284"

	select marked_up_line from dp8801 where wkuniversalid='dp8801w056' and level_00_value='6'
		"ὁ κύριοϲ θεὸϲ καταβή-"


[success] BGU1200.11 can be had by:

	select universalid,title from works where title like '%BGU%1200%'
		"dp0004w057"; "BGU (Vol 4) - 1200"

	select marked_up_line from dp0004 where wkuniversalid='dp0004w057' and level_00_value='11'
		"ὑπὲρ τοῦ θε̣[οῦ] καὶ κυρίου Αὐτοκράτοροϲ Κ̣α̣[ίϲαροϲ καθηκούϲαϲ]"


[fail] Supp.Epigr.2.830

	select universalid,title from works where title like '%Supp%Epigr%830%'
		"in001aw1en";"Attica (Suppl. Epigr. Gr. 1-41 [SEG]) - 21:830"
		[not v2, not damascus, not ii AD, ...]


[fail] CIG4521:

	select universalid,title from works where title like '%CIG%45%'
		"ch0201w01v";"Constantinople [Chr.] (CIG IV [part]) - 9445"
		"ch0305w02z";"Greece [Chr.] (Attica [various sources]) - CIG 9345"


[fail] Berl.Sitzb.1902.1096:
	select universalid,title from works where title like '%Berl%Sitzb%'
		[nothing returned]


[fail] POxy.37 i 6:
	select universalid,title from works where title like '%POxy% 37'
		"dp6f01w035";"POxy (Vol 1) - 37"
	you'll get stuck in the end:
		"<hmu_roman_in_a_greek_text>POxy 1,37=CPapGr 1,19</hmu_roman_in_a_greek_text>"


[fail (but mabe LSJ failed?)] POxy.110.2:
	select universalid,title from works where title like '%POxy% 102'
		"dp6f01w003";"POxy (Vol 1) - 102"

	select * from dp6f01 where wkuniversalid='dp6f01w003' and stripped_line like '%κυρ%'
		three hits; none of them about Sarapis...
		"<hmu_metadata_provenance value="Oxy" /><hmu_metadata_date value="AD 306" /><hmu_metadata_documentnumber value="65" />ἐπὶ ὑπάτων τ[ῶν] κ[υ]ρίων ἡ[μ]ῶν Αὐτοκρατόρων"


"""
