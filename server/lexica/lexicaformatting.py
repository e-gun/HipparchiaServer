# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Process, Manager, Value
from bs4 import BeautifulSoup
from server import hipparchia
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.hipparchiaclasses import MPCounter
from server.dbsupport.dbfunctions import setconnection

def grabsenses(fullentry):
	"""
	look for all of the senses of a work in its dictionary entry
	:param fullentry:
	:return:
	"""
	sensing = re.compile(r'<sense.*?/sense>')
	senses = re.findall(sensing, fullentry)
	leveler = re.compile(r'<sense\s.*?level="(.*?)".*?>')
	nummer = re.compile(r'<sense.*?\sn="(.*?)".*?>')
	numbered = []
	i = 0
	
	for sense in senses:
		i += 1
		lvl = re.search(leveler,sense)
		num = re.search(nummer,sense)
		# note that the two dictionaries do not necc aree with one another (or themselves) when it comes to nesting labels
		if re.search(r'[A-Z]',num.group(1)) is not None:
			paragraphlevel = '1'
		elif re.search(r'[0-9]',num.group(1)) is not None:
			paragraphlevel = '3'
		elif re.search(r'[ivx]',num.group(1)) is not None:
			paragraphlevel = '4'
		elif re.search(r'[a-hj-w]',num.group(1)) is not None:
			paragraphlevel = '2'
		else:
			paragraphlevel = '1'
		
		
		try:
			rewritten = '<p class="level'+paragraphlevel+'"><span class="levelabel'+lvl.group(1)+'">'+num.group(1)+'</span>&nbsp;'+sense+'</p>\n'
		except:
			print('exception in grabsenses at sense number:',i)
			rewritten = ''
		numbered.append(rewritten)

	return numbered


def entrysummary(fullentry,lang, translationlabel):
	"""
	returns a collection of lists: all authors, senses, and quotes to be found in an entry
	:param fullentry:
	:return:
	"""
	
	soup = BeautifulSoup(fullentry, 'html.parser')
	a = soup.find_all('author')
	a = list(set(a))
	# the list is composed of objj. that are <class 'bs4.element.Tag'>
	a[:] = [value.string for value in a]
	notin = ['id.', 'ib.', 'Id.']
	a[:] = [value for value in a if value not in notin]
	a.sort()
	newa = []
	for au in a:
		newa.append(deabbreviateauthors(au, lang))
	a = newa

	s = soup.find_all(translationlabel)
	notin = ['ab', 'de', 'ex', 'ut', 'nihil', 'quam', 'quid']
	try:
		s[:] = [value.string for value in s]
		s[:] = [value for value in s if '.' not in value]
		s[:] = [value for value in s if value not in notin]
	except:
		s = []
	s = list(set(s))

	q = soup.find_all('quote')
	q[:] = [value.string for value in q]

	summary = (a,s,q)

	return summary


def grabheadmaterial(fullentry):
	"""
	find the information at the top of a dictionary entry: used to get the basic info about the word
	:param fullentry:
	:return:
	"""
	heading = re.compile(r'(.*?)\<sense')
	head = re.search(heading,fullentry)

	try:
		return head.group(0)
	except:
		try:
			return ''
		except:
			print('failed to grabheadmaterial()\n\t',fullentry)
			return ''


def deabbreviateauthors(authorabbr, lang):
	"""
	try to turn an author abbreviation into an author name
	:param authorabbr:
	:param lang:
	:return:
	"""
	if lang == 'latin':
		decoder = { 'Caes.':'Caesar',
		        'Cat.':'Catullus',
	            'Cic.':'Cicero',
	            'Enn.': 'Ennius',
	            'Fest.':'Festus',
	            'Gell.': 'Gellius',
	            'Hor.':'Horace',
	            'Juv.': 'Juvenal',
	            'Lact.':'Lactantius',
	            'Liv.':'Livy',
	            'Lucr.':'Lucretius',
	            'Macr.':'Macrobius',
	            'Mart.':'Martial',
	            'Nep.': 'Nepos',
	            'Non.':'Nonius',
	            'Ov.':'Ovid',
	            'Pall.':'Palladius',
	            'Pers.':'Persius',
	            'Petr.':'Petronius',
	            'Phaed.':'Phaedrus',
	            'Plaut.':'Plautus',
	            'Plin.':'Pliny',
	            'Prop.':'Propertius',
	            'Quint.':'Quintilian',
	            'Sall.':'Sallust',
	            'Sen.':'Seneca',
	            'Stat.':'Statius',
	            'Suet.':'Suetonius',
	            'Tac.':'Tacitus',
	            'Ter.':'Terence',
	            'Varr.':'Varro',
	            'Vell.':'Velleius',
	            'Verg.':'Vergil',
		        'Vitr.':'Vitruvius'

	            }
	elif lang == 'greek':
		decoder = { 'A.': 'Aeschylus',
		            'Aeschin.': 'Aeschines',
		            'And.': 'Andocides',
		            'Antiph.': 'Antiphon',
					'Ar.': 'Aristophanes',
		            'Arist.': 'Aristotle',
		            'Ath.': 'Athenaeus',
		            'B.': 'Bacchylides',
		            'Call.': 'Callimachus',
		            'D.': 'Demosthenes',
		            'D.C.': 'Dio Cassius',
		            'D.H.': 'Dionysius of Halicarnassus',
		            'D.L.': 'Diogenes Laertius',
		            'E.': 'Euripides',
		            'Gal.': 'Galen',
		            'Hdt.': 'Herodotus',
		            'Hes.': 'Hesiod',
		            'Hom.': 'Homer',
		            'Hp.': 'Hippocrates',
		            'Il.': 'Homer (Iliad)',
		            'Is.': 'Isaeus',
		            'Isoc.': 'Isocrates',
		            'J.': 'Josephus',
		            'Jul.': 'Julian',
		            'Luc.': 'Lucian',
		            'LXX': 'Septuagint',
		            'Lycurg.': 'Lycurgus',
		            'Lys.': 'Lysias',
		            'Men.': 'Menander',
		            'Od.': 'Homer (Odyssey)',
		            'Paus.': 'Pausanias',
		            'Pi.':'Pindar',
		            'Pl.':'Plato',
		            'Plb.':'Polybius',
		            'Plot.': 'Plotinus',
		            'Plu.':'Plutarch',
		            'S.':'Sophocles',
		            'Sosith.': 'Sositheus',
		            'Th.': 'Thucydides',
		            'Theoc.': 'Theocritus',
		            'Thgn.': 'Theognis',
		            'Tim.': 'Timaeus',
		            'X.': 'Xenophon',
		            'Xenoph.': 'Xenophanes'
		            }
	else:
		decoder = {}

	if authorabbr in decoder:
		author = decoder[authorabbr]
	else:
		author = authorabbr
		
	return author


def formatdictionarysummary(authors,senses,quotes):
	"""
	turn three lists into html formatting for the summary material that will be inserted at the top of a dictionary entry
	:param authors:
	:param senses:
	:param quotes:
	:return:
	"""
	summary = ''
	if len(authors) > 0:
		summary += '<br \>\n<div class="authorsummary"><span class="highlight">Used by:</span><br \>\n'
		for a in authors:
			summary += '<span class="author">'+a+'</span><br \>\n'
	if len(senses) > 0:
		summary += '</div>\n<br \><div class="sensesummary"><span class="highlight">Senses:</span><br \>\n'
		for s in senses:
			summary += '<span class="sense">' + s + '</span><br \>\n'
	if len(quotes) > 0:
		summary += '</div>\n<br \><div class="quotesummary"><span class="highlight">Phrases:</span><br \>\n'
		for q in quotes:
			summary += '<span class="quote">' + q + '</span><br \>\n'
	summary += '</div><br \><br \>\n<span class="highlight">Full entry:</span><br \>'

	return summary


def formateconsolidatedentry(consolidatedentry):
	"""
	send me hit from findbyform() in the results browser

	consolidatedentry = (count,theword, thetransl, analysislist)

	example:
		(1, 'nūbibus,nubes', 'a cloud', ['fem abl pl', 'fem dat pl'])


	:param entrydata:
	:return:
	"""

	analysislist = consolidatedentry[3]

	analysis = '<p class="obsv">(' + str(consolidatedentry[0]) + ')&nbsp;'
	analysis += '<span class="dictionaryform">' + consolidatedentry[1] + '</span>: &nbsp;'
	if len(analysislist) == 1:
		analysis += '<span class="possibility">' + analysislist[0] + '</span>&nbsp;'
	else:
		count = 0
		for a in analysislist:
			count += 1
			analysis += '[' + chr(count+96) + ']&nbsp;<span class="possibility">' + a + '</span>; '
		analysis = analysis[:-2]
		analysis += '&nbsp;'
	if len(consolidatedentry[2]) > 1:
		analysis += '<span class="translation">('  + consolidatedentry[2] + ')</span>'

	return analysis


def formatgloss(entrybody):
	"""
	glosses don't work the same as standard dictionary entries. deal with them
	:param entrybody:
	:return:
	"""
	glosshtml = ''
	
	soup = BeautifulSoup(entrybody, 'html.parser')
	senses = soup.find_all('foreign')
	sources = soup.find_all('author')
	
	senses[:] = [value.string for value in senses]
	sources[:] = [value.string for value in sources]
	
	glosshtml += '<span class="highlight">Reported by:</span><br />\n'
	for s in sources:
		glosshtml += s + ', '
	glosshtml = glosshtml[:-2]
	
	glosshtml += '<br /><br />\n<span class="highlight">Senses:</span><br />'
	for s in senses:
		glosshtml += s + '<br />'
	
	return glosshtml


def formatmicroentry(entrybody):
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
		entryhtml += s + '<br />'
		
	entryhtml = entrybody
	
	return entryhtml


def insertbrowserlookups(htmlentry):
	"""
	there can be a big lag opening the entry for something like εχω: put off the click conversions until later...
	but debugging is a lot easier via impatientinsertbrowserlookups()
	
	:param htmlentry:
	:return:
	"""
	
	# first retag the items that should not click-to-browse
	
	biblios = re.compile(r'(<bibl.*?)(.*?)(</bibl>)')
	bibs = re.findall(biblios, htmlentry)
	bdict = {}
	
	for bib in bibs:
		if 'Perseus:abo' not in bib[1]:
			head = '<unclickablebibl'
			tail = '</unclickablebibl>'
		else:
			head = bib[0]
			tail = bib[2]
		bdict[('').join(bib)] = head + bib[1] + tail
	
	# print('here',bdict)
	for key in bdict.keys():
		htmlentry = re.sub(key, bdict[key], htmlentry)
	
	# now do the work of finding the lookups
	
	tlgfinder = re.compile(r'n="Perseus:abo:tlg,(\d\d\d\d),(\d\d\d):(.*?)"')
	phifinder = re.compile(r'n="Perseus:abo:phi,(\d\d\d\d),(\d\d\d):(.*?)"')
	
	clickableentry = re.sub(tlgfinder, r'id="gr\1w\2_PE_\3"', htmlentry)
	clickableentry = re.sub(phifinder, r'id="lt\1w\2_PE_\3"', clickableentry)
	
	return clickableentry
	

def insertbrowserjs(htmlentry):
	"""
	now: '<bibl id="gr0527w004_AT_36|11"...>
	you have something that document.getElementById can click, but no JS to support the click
	add the JS
	:param htmlentry:
	:return:
	"""
	
	# clickfinder = re.compile(r'<bibl id="(..\d\d\d\dw\d\d\d\_LN_.*?)"')
	clickfinder = re.compile(r'<bibl id="(..\d\d\d\dw\d\d\d\_PE_.*?)"')
	clicks = re.findall(clickfinder,htmlentry)
	
	if len(clicks) > 0:
		clickableentry = htmlentry + '\n<script>'
		for c in clicks:
			clickableentry += 'document.getElementById(\''+c+'\').onclick = openbrowserfromclick;\n'
		clickableentry += '</script>'
	else:
		clickableentry = htmlentry
	
	return clickableentry


def dbquickfixes(listofnames):
	"""
	persus' euripides work numbers are wrong
	deal with that here
	and anything else that pops up
	build a lit of swaps
	:param listofnames:
	:return:
	"""
	
	"""
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
	
	substitutes = {}
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
		'gr0006w019': 'gr0006w052'
	}
	for item in listofnames:
		db = re.search(dbfinder,item)
		if db.group(1) in fixer.keys():
			hipparchiadb = fixer[db.group(1)]
			substitutes[item] = hipparchiadb+db.group(2)

	return substitutes

