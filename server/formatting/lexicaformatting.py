# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import Dict

from bs4 import BeautifulSoup
from flask import session


def grabheadmaterial(fullentry: str) -> str:
	"""
	find the information at the top of a dictionary entry: used to get the basic info about the word
	:param fullentry:
	:return:
	"""
	heading = re.compile(r'(.*?)<sense')
	head = re.search(heading, fullentry)

	try:
		return head.group(1)
	except AttributeError:
		return str()


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
			outputlist.append('<div class="{cl}"><span class="lexiconhighlight">{lb}</span><br />'.format(cl=classone, lb=label))
		if len(items) == 1:
			outputlist.append('<span class="{cl}">{item}</span><br />'.format(cl=classtwo, item=items[0]))
		else:
			count = 0
			for i in items:
				count += 1
				outputlist.append('\t<span class="{cl}">({ct})&nbsp;{item}</span><br />'.format(cl=classtwo, item=i, ct=count))
		if len(items) > 0:
			outputlist.append('</div>')

	outputlist.append('<br /><br />\n<span class="lexiconhighlight">Full entry:</span><br />')

	summarystring = '\n'.join(outputlist)

	return summarystring


def formatgloss(entrybody: str) -> str:
	"""
	glosses don't work the same as standard dictionary entries. deal with them
	:param entrybody:
	:return:
	"""

	glosshtml = list()
	
	soup = BeautifulSoup(entrybody, 'html.parser')
	senses = soup.find_all('foreign')
	sources = soup.find_all('author')
	
	senses[:] = [value.string for value in senses]
	sources[:] = [value.string for value in sources]

	if sources:
		glosshtml.append('<span class="highlight">Reported by:</span><br />')
		glosshtml.append(', '.join(sources))

	if senses:
		glosshtml.append('<br /><br />\n<span class="highlight">Senses:</span><br />')
		glosshtml.append(', '.join(senses))

	glosshtml = '\n'.join(glosshtml)

	glosshtml = glosshtml + '<br>\n<br>\n' + entrybody

	return glosshtml


def formatmicroentry(entrybody: str) -> str:
	"""
	some entries work like glosses but are not labeled as glosses: no quote, authors, etc. just a synonym or synonyms listed
	deal with it

	:param entrybody:
	:return:
	"""

	entryhtml = ''
	
	soup = BeautifulSoup(entrybody, 'html.parser')
	senses = soup.find_all('foreign')
	senses[:] = [value.string for value in senses]
	
	entryhtml += '<span class="highlight">Senses:</span><br />'
	for s in senses:
		try:
			entryhtml += s + '<br />'
		except TypeError:
			# s was NoneType
			pass

	entryhtml = entrybody
	
	return entryhtml


def insertbrowserlookups(htmlentry: str) -> str:
	"""
	there can be a big lag opening the entry for something like εχω: put off the click conversions until later...
	but debugging is a lot easier via impatientinsertbrowserlookups()
	
	:param htmlentry:
	:return:
	"""
	
	# first retag the items that should not click-to-browse
	
	biblios = re.compile(r'(<bibl.*?)(.*?)(</bibl>)')
	bibs = re.findall(biblios, htmlentry)
	bdict = dict()
	
	for bib in bibs:
		if 'Perseus:abo' not in bib[1]:
			head = '<unclickablebibl'
			tail = '</unclickablebibl>'
		else:
			head = bib[0]
			tail = bib[2]
		bdict[''.join(bib)] = head + bib[1] + tail
	
	# print('here',bdict)
	for key in bdict.keys():
		htmlentry = re.sub(key, bdict[key], htmlentry)
	
	# now do the work of finding the lookups
	
	tlgfinder = re.compile(r'n="Perseus:abo:tlg,(\d\d\d\d),(\d\d\d):(.*?)"')
	phifinder = re.compile(r'n="Perseus:abo:phi,(\d\d\d\d),(\d\d\d):(.*?)"')
	
	clickableentry = re.sub(tlgfinder, r'id="gr\1w\2_PE_\3"', htmlentry)
	clickableentry = re.sub(phifinder, r'id="lt\1w\2_PE_\3"', clickableentry)
	
	return clickableentry


def dbquickfixes(listofnames: list) -> Dict[str, str]:
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
