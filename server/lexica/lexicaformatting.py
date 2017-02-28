# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from string import punctuation
from bs4 import BeautifulSoup


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
		# note that the two dictionaries do not necc agree with one another (or themselves) when it comes to nesting labels
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
			rewritten = '<p class="level{pl}"><span class="levelabel{lv}">{nm}</span>&nbsp;{sn}</p>\n'.format(pl=paragraphlevel, lv=lvl.group(1),nm=num.group(1), sn=sense)
		except:
			print('exception in grabsenses at sense number:',i)
			rewritten = ''
		numbered.append(rewritten)

	return numbered


def entrysummary(fullentry, lang, translationlabel):
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
	a = [deabbreviateauthors(au, lang) for au in a]

	s = soup.find_all(translationlabel)
	notin = ['ab', 'de', 'ex', 'ut', 'nihil', 'quam', 'quid']
	try:
		s[:] = [value.string for value in s]
		s[:] = [value for value in s if '.' not in value]
		s[:] = [value for value in s if value not in notin]
	except:
		s = []

	# so 'go' and 'go,' are not both on the list
	depunct = '[{p}]$'.format(p=re.escape(punctuation))
	s = [re.sub(depunct, '',s) for s in s]
	s = list(set(s))
	s.sort()

	q = soup.find_all('quote')
	q[:] = [value.string for value in q]

	summarydict = {'authors':a, 'senses': s, 'quotes':q}

	return summarydict


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

	just hand this off to another fuction via language setting

	:param authorabbr:
	:param lang:
	:return:
	"""

	if lang == 'greek':
		authordict = deabrevviategreekauthors()
	elif lang == 'latin':
		authordict = deabrevviatelatinauthors()
	else:
		authordict = {}

	if authorabbr in authordict:
		author = authordict[authorabbr]
	else:
		author = authorabbr

	return author


def formatdictionarysummary(summarydict):
	"""
	turn three lists into html formatting for the summary material that will be inserted at the top of a dictionary entry
	:param authors:
	:param senses:
	:param quotes:
	:return:
	"""

	authors = summarydict['authors']
	senses = summarydict['senses']
	quotes = summarydict['quotes']

	sections = { 'authors': { 'items': authors, 'classone': 'authorsummary', 'classtwo': 'authorsum', 'label': 'Used by'},
				 'quotes': {'items': quotes, 'classone': 'quotessummary', 'classtwo': 'quotesum', 'label': 'Quotes'},
				 'senses': {'items': senses, 'classone': 'sensesummary', 'classtwo': 'sensesum', 'label': 'Senses'}
				 }

	summary = ''

	for section in ['authors', 'senses', 'quotes']:
		sec = sections[section]
		items = sec['items']
		classone = sec['classone']
		classtwo = sec['classtwo']
		label = sec['label']
		if len(items) > 0:
			summary += '<div class="'+classone+'"><span class="highlight">'+label+'</span><br \>\n'
		if len(items) == 1:
			summary += '<span class="'+classtwo+'">' + items[0] + '</span><br \>\n'
		else:
			count = 0
			for i in items:
				count += 1
				summary += '<span class="'+classtwo+'">('+str(count)+')&nbsp;' + i + '</span><br \>\n'

	summary += '</div><br \><br \>\n<span class="highlight">Full entry:</span><br \>'

	return summary


def formateconsolidatedgrammarentry(consolidatedentry):
	"""
	send me hit from findbyform() in the results browser

	consolidatedentry = {'count': count, 'form': wordandform[0], 'word': wordandform[1], 'transl': thetransl, 'anal': analysislist}

	example:
		 {'count': 1, 'form': 'ἀϲήμου', 'word': 'ἄϲημοϲ', 'transl': 'without mark', 'anal': ['masc/fem/neut gen sg']}

	:param entrydata:
	:return:
	"""

	analysislist = consolidatedentry['anal']

	analysis = '<p class="obsv">(' + str(consolidatedentry['count']) + ')&nbsp;'
	wordandtranslation = '<span class="dictionaryform">'+consolidatedentry['word'] + '</span>'
	if len(consolidatedentry['transl']) > 1:
		wordandtranslation += ', '  + consolidatedentry['transl']

	analysis += '<span class="dictionaryform">' + consolidatedentry['form'] + '</span> (from '+wordandtranslation+'): &nbsp;'
	if len(analysislist) == 1:
		analysis += '\n<br /><span class="possibility">' + analysislist[0] + '</span>&nbsp;'
	else:
		count = 0
		for a in analysislist:
			count += 1
			analysis += '\n<br />[' + chr(count+96) + ']&nbsp;<span class="possibility">' + a + '</span>'
		analysis += '&nbsp;'

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
		try:
			entryhtml += s + '<br />'
		except:
			# s was NoneType
			pass

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


def deabrevviategreekauthors():
	"""

	return a decoder dictionary

	copy the the appropriate segment at the top of of greek-lexicon_1999.04.0057.xml into a new file
	[lines 788 to 4767]

	then:

		grep "<item><hi rend=\"bold\">" tlg_authors_and_works.txt > tlg_authorlist.txt
		perl -pi -w -e 's/<\/hi>.*?\[/<\/hi>\[/g;' tlg_authorlist.txt
		perl -pi -w -e 's/<item><hi rend="bold">//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/hi>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<date>.*?<\/date>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<title>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/title>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/item>//g;' tlg_authorlist.txt

	what remains will look like:

		Aelius Dionysius[Ael.Dion.]

	then regex:
		^(.*?)\[(.*?)\]  ==> '\2': '\1',

	then all lines with single quotes and colons are good

		grep ":" tlg_authorlist.txt > tlg_authordict.txt

	there are some key collisions, but you are basically done after you whack those moles

	:param:
	:return: authordict
	"""
	authordict = {
		'Abyd.': 'Abydenus', 
		'Acerat.': 'Aceratus',
		'Acesand.': 'Acesander', 
		'Achae.': 'Achaeus', 
		'Ach.Tat.': 'Achilles Tatius',
		'Acus.': 'Acusilaus', 
		'Adam.': 'Adamantius', 
		'Ael.': 'Aelianus', 
		'Ael.Dion.': 'Aelius Dionysius', 
		'Aemil.': 'Aemilianus', 
		'Aen.Gaz.': 'Aeneas Gazaeus', 
		'Aen.Tact.': 'Aeneas Tacticus', 
		'Aesar.': 'Aesara',
		'Aeschin.': 'Aeschines', 
		'Aeschin.Socr.': 'Aeschines Socraticus', 
		'A.': 'Aeschylus', 
		'Aesch.Alex.': 'Aeschylus Alexandrinus', 
		'Aesop.': 'Aesopus',
		'Aët.': 'Aëtius', 
		'Afric.': 'Africanus, Julius', 
		'Agaclyt.': 'Agaclytus',
		'Agatharch.': 'Agatharchides', 
		'Agathem.': 'Agathemerus',
		'Agath.': 'Agathias', 
		'Agathin.': 'Agathinus', 
		'Agathocl.': 'Agathocles',
		'Alb.': 'Albinus', 
		'Alc.Com.': 'Alcaeus', 
		'Alc.': 'Alcaeus', 
		'Alc.Mess.': 'Alcaeus Messenius', 
		'Alcid.': 'Alcidamas', 
		'Alcin.': 'Alcinous',
		'Alciphr.': 'Alciphro', 
		'Alcm.': 'Alcman', 
		'Alexand.Com.': 'Alexander',
		'Alex.Aet.': 'Alexander Aetolus', 
		'Alex.Aphr.': 'Alexander Aphrodisiensis', 
		'Alex.Eph.': 'Alexander Ephesius', 
		'Alex.Polyh.': 'Alexander Polyhistor',
		'Alex.Trall.': 'Alexander Trallianus', 
		'Alex.': 'Alexis', 
		'Alph.': 'Alpheus', 
		'Alyp.': 'Alypius', 
		'Amips.': 'Amipsias', 
		'Ammian.': 'Ammianus', 
		'Amm.Marc.': 'Ammianus Marcellinus', 
		'Ammon.': 'Ammonius',
		'Anach.': 'Anacharsis', 
		'Anacr.': 'Anacreon', 
		'Anacreont.': 'Anacreontea',
		'Anan.': 'Ananius', 
		'Anaxag.': 'Anaxagoras',
		'Anaxandr.': 'Anaxandrides', 
		'Anaxandr.Hist.': 'Anaxandrides', 
		'Anaxarch.': 'Anaxarchus', 
		'Anaxil.': 'Anaxilas', 
		'Anaximand.Hist.': 'Anaximander', 
		'Anaximand.': 'Anaximander', 
		'Anaximen.': 'Anaximenes', 
		'Anaxipp.': 'Anaxippus', 
		'And.': 'Andocides', 
		'Androm.': 'Andromachus', 
		'Andronic.': 'Andronicus',
		'Andronic.Rhod.': 'Andronicus Rhodius', 
		'Androt.': 'Androtion', 
		'AB': 'Anecdota Graeca',
		'Anecd.Stud.': 'Anecdota Graeca et Latina',
		'Anon.': 'Anonymus',
		'Anon.Lond.': 'Anonymus Londnensis', 
		'Anon.Rhythm.': 'Anonymus Rhythmicus',
		'Anon.Vat.': 'Anonymus Vaticanus',
		'Antag.': 'Antagoras', 
		'Anthem.': 'Anthemius', 
		'Anticl.': 'Anticlides', 
		'Antid.': 'Antidotus', 
		'Antig.': 'Antigonus Carystius', 
		'Antig.Nic.': 'Antigonus Nicaeanus',
		'Antim.': 'Antimachus Colophonius', 
		'Antioch.Astr.': 'Antiochus Atheniensis', 
		'Antioch.': 'Antiochus',
		'Antioch.Hist.': 'Antiochus', 
		'Antip.Sid.': 'Antipater Sidonius', 
		'Antip.Stoic.': 'Antipater Tarsensis', 
		'Antip.Thess.': 'Antipater Thessalonicensis', 
		'Antiph.': 'Antiphanes', 
		'Antiphan.': 'Antiphanes Macedo',
		'Antiphil.': 'Antiphilus', 
		'Antipho Soph.': 'Antipho Sophista', 
		'Antipho Trag.': 'Antipho', 
		'Antisth.': 'Antisthenes', 
		'Antist.': 'Antistius', 
		'Ant.Lib.': 'Antoninus Liberalis', 
		'Anton.Arg.': 'Antonius Argivus',
		'Ant.Diog.': 'Antonius Diogenes', 
		'Antyll.': 'Antyllus', 
		'Anub.': 'Anubion', 
		'Anyt.': 'Anyte', 
		'Aphth.': 'Aphthonius', 
		'Apollinar.': 'Apollinarius', 
		'Apollod.Com.': 'Apollodorus', 
		'Apollod.Car.': 'Apollodorus Carystius', 
		'Apollod.Gel.': 'Apollodorus Gelous', 
		'Apollod.': 'Apollodorus',
		'Apollod.Lyr.': 'Apollodorus',
		'Apollod.Stoic.': 'Apollodorus Seleuciensis', 
		'Apollonid.': 'Apollonides', 
		'Apollonid.Trag.': 'Apollonides',
		'Apollon.': 'Apollonius',
		'Apollon.Cit.': 'Apollonius Citiensis', 
		'A.D.': 'Apollonius Dyscolus', 
		'Apollon.Perg.': 'Apollonius Pergaeus',
		'A.R.': 'Apollonius Rhodius',
		'Ap.Ty.': 'Apollonius Tyanensis', 
		'Apolloph.': 'Apollophanes', 
		'Apolloph.Stoic.': 'Apollophanes', 
		'Apostol.': 'Apostolius', 
		'App.': 'Appianus', 
		'Aps.': 'Apsines',
		'Apul.': 'Apuleius', 
		'Aq.': 'Aquila', 
		'Arab.': 'Arabius', 
		'Arar.': 'Araros', 
		'Arat.': 'Aratus', 
		'Arc.': 'Arcadius', 
		'Arcesil.': 'Arcesilaus', 
		'Arched.': 'Archedicus', 
		'Arched.Stoic.': 'Archedemus Tarsensis', 
		'Archemach.': 'Archemachus',
		'Archestr.': 'Archestratus', 
		'Arch.': 'Archias', 
		'Arch.Jun.': 'Archias Junior',
		'Archig.': 'Archigenes', 
		'Archil.': 'Archilochus', 
		'Archim.': 'Archimedes', 
		'Archimel.': 'Archimelus', 
		'Archipp.': 'Archippus', 
		'Archyt.Amph.': 'Archytas Amphissensis', 
		'Archyt.': 'Archytas Tarentinus', 
		'Aret.': 'Aretaeus', 
		'Aristaenet.': 'Aristaenetus',
		'Aristag.': 'Aristagoras', 
		'Aristag.Hist.': 'Aristagoras', 
		'Aristarch.': 'Aristarchus', 
		'Aristarch.Sam.': 'Aristarchus Samius', 
		'Aristarch.Trag.': 'Aristarchus', 
		'Aristeas Epic.': 'Aristeas', 
		'Aristid.': 'Aristides', 
		'Aristid.Mil.': 'Aristides Milesius', 
		'Aristid.Quint.': 'Aristides Quintilianus', 
		'Aristipp.': 'Aristippus', 
		'AristoStoic.': 'Aristo Chius', 
		'Aristobul.': 'Aristobulus', 
		'Aristocl.': 'Aristocles',
		'Aristocl.Hist.': 'Aristocles',
		'Aristodem.': 'Aristodemus', 
		'Aristodic.': 'Aristodicus', 
		'Aristomen.': 'Aristomenes', 
		'Aristonym.': 'Aristonymus',
		'Ar.': 'Aristophanes', 
		'Aristoph.Boeot.': 'Aristophanes Boeotus', 
		'Ar.Byz.': 'Aristophanes Byzantinus', 
		'Arist.': 'Aristoteles', 
		'Aristox.': 'Aristoxenus', 
		'Ar.Did.': 'Arius Didymus', 
		'Arr.': 'Arrianus', 
		'Artem.': 'Artemidorus Daldianus', 
		'Artemid.': 'Artemidorus Tarsensis', 
		'Arus.Mess.': 'Arusianus Messius', 
		'Ascens.Is.': 'Ascensio Isaiae',
		'Asclep.': 'Asclepiades', 
		'Asclep.Jun.': 'Asclepiades Junior', 
		'Asclep.Myrl.': 'Asclepiades Myrleanus',
		'Asclep.Tragil.': 'Asclepiades Tragilensis',
		'Ascl.': 'Asclepius', 
		'Asp.': 'Aspasius', 
		'Astramps.': 'Astrampsychus', 
		'Astyd.': 'Astydamas', 
		'Ath.': 'Athenaeus',
		'Ath.Mech.': 'Athenaeus',
		'Ath.Med.': 'Athenaeus', 
		'Athenodor.Tars.': 'Athenodorus Tarsensis', 
		'Atil.Fort.': 'Atilius Fortunatianus', 
		'Attal.': 'Attalus', 
		'Attic.': 'Atticus', 
		'Aus.': 'Ausonius', 
		'Autocr.': 'Autocrates', 
		'Autol.': 'Autolycus', 
		'Autom.': 'Automedon', 
		'Axionic.': 'Axionicus', 
		'Axiop.': 'Axiopistus', 
		'Babr.': 'Babrius', 
		'Bacch.': 'Bacchius',
		'B.': 'Bacchylides', 
		'Balbill.': 'Balbilla', 
		'Barb.': 'Barbucallos', 
		'Bass.': 'Bassus, Lollius', 
		'Bato Sinop.': 'Bato Sinopensis', 
		'Batr.': 'Batrachomyomachia',
		'Beros.': 'Berosus', 
		'Besant.': 'Besantinus', 
		'Blaes.': 'Blaesus',
		'Boeth.': 'Boethus', 
		'Boeth.Stoic.': 'Boethus Sidonius', 
		'Brut.': 'Brutus', 
		'Buther.': 'Butherus',
		'Cael.Aur.': 'Caelius Aurelianus',
		'Call.Com.': 'Callias', 
		'Call.Hist.': 'Callias', 
		'Callicrat.': 'Callicratidas',
		'Call.': 'Callimachus', 
		'Callinic.Rh.': 'Callinicus', 
		'Callin.': 'Callinus', 
		'Callistr.Hist.': 'Callistratus', 
		'Callistr.': 'Callistratus', 
		'Callix.': 'Callixinus', 
		'Canthar.': 'Cantharus', 
		'Carc.': 'Carcinus', 
		'Carm.Aur.': 'Carmen Aureum',
		'Carm.Pop.': 'Carmina Popularia',
		'Carneisc.': 'Carneiscus', 
		'Carph.': 'Carphyllides',
		'Caryst.': 'Carystius', 
		'Cass.': 'Cassius', 
		'Cass.Fel.': 'Cassius Felix', 
		'Cat.Cod.Astr.': 'Catalogus Codicum Astrologorum',
		'Ceb.': 'Cebes', 
		'Cels.': 'Celsus',
		'Cephisod.': 'Cephisodorus', 
		'Cerc.': 'Cercidas', 
		'Cercop.': 'Cercopes',
		'Cereal.': 'Cerealius', 
		'Certamen': 'Certamen Homeri et Hesiodi',
		'Chaerem.Hist.': 'Chaeremon', 
		'Chaerem.': 'Chaeremon', 
		'Chamael.': 'Chamaeleon',
		'Epist.Charact.': 'Characteres Epistolici',
		'Chares Iamb.': 'Chares', 
		'Chares Trag.': 'Chares',
		'Chariclid.': 'Chariclides',
		'Charis.': 'Charisius', 
		'Charixen.': 'Charixenes', 
		'Charond.': 'Charondas', 
		'Chionid.': 'Chionides', 
		'Choeril.': 'Choerilus', 
		'Choeril.Trag.': 'Choerilus', 
		'Choerob.': 'Choeroboscus', 
		'Chor.': 'Choricius', 
		'Chrysipp.Stoic.': 'Chrysippus', 
		'Chrysipp. Tyan.': 'Chrysippus Tyanensis', 
		'Cic.': 'Cicero, M. Tullius', 
		'Claudian.': 'Claudianus', 
		'Claud.Iol.': 'Claudius Iolaus',
		'Cleaenet.': 'Cleaenetus', 
		'Cleanth.Stoic.': 'Cleanthes', 
		'Clearch.Com.': 'Clearchus', 
		'Clearch.': 'Clearchus', 
		'Clem.Al.': 'Clemens Alexandrinus', 
		'Cleobul.': 'Cleobulus', 
		'Cleom.': 'Cleomedes', 
		'Cleon Sic.': 'Cleon Siculus',
		'Cleonid.': 'Cleonides', 
		'Cleostrat.': 'Cleostratus', 
		'Clidem. vel Clitodem.': 'Clidemus', 
		'Clin.': 'Clinias', 
		'Clitarch.': 'Clitarchus',
		'Clitom.': 'Clitomachus', 
		'Cod.Just.': 'Codex Justinianus', 
		'Cod.Theod.': 'Codex Theodosianus', 
		'Colot.': 'Colotes', 
		'Coluth.': 'Coluthus', 
		'Com.Adesp.': 'Comica Adespota',
		'Corinn.': 'Corinna', 
		'Corn.Long.': 'Cornelius Longus',
		'Corn.': 'Cornutus', 
		'Corp.Herm.': 'Corpus Hermeticum',
		'Crater.': 'Craterus', 
		'Crates Com.': 'Crates', 
		'Crates Hist.': 'Crates',
		'Crates Theb.': 'Crates Thebanus', 
		'Cratin.': 'Cratinus', 
		'Cratin.Jun.': 'Cratinus Junior', 
		'Cratipp.': 'Cratippus', 
		'Crin.': 'Crinagoras', 
		'Critias': 'Critias', 
		'Crito Com.': 'Crito', 
		'Crobyl.': 'Crobylus', 
		'Ctes.': 'Ctesias', 
		'Cyllen.': 'Cyllenius', 
		'Cyran.': 'Cyranus',
		'Cypr.': 'Cypria',
		'Cyr.': 'Cyrilli Glossarium',
		'Cyrill.': 'Cyrillus', 
		'Damag.': 'Damagetus', 
		'Dam.': 'Damascius', 
		'Damian.': 'Damianus',
		'Damoch.': 'Damocharis', 
		'Damocr.': 'Damocrates', 
		'Damocrit.': 'Damocritus', 
		'Damostr.': 'Damostratus',
		'Damox.': 'Damoxenus', 
		'Deioch.': 'Deiochus',
		'Demad.': 'Demades', 
		'Demetr.': 'Demetrius',
		'Demetr.Com.Nov.': 'Demetrius', 
		'Demetr.Com.Vet.': 'Demetrius', 
		'Demetr.Apam.': 'Demetrius Apamensis',
		'Demetr.Lac.': 'Demetrius Lacon',
		'Dem.Phal.': 'Demetrius Phalereus', 
		'Demetr.Troez.': 'Demetrius Troezenius', 
		'Democh.': 'Demochares', 
		'Democr.': 'Democritus',
		'Democr.Eph.': 'Democritus Ephesius',
		'Demod.': 'Demodocus', 
		'Demonic.': 'Demonicus',
		'Demoph.': 'Demophilus',
		'D.': 'Demosthenes', 
		'Dem.Bith.': 'Demosthenes Bithynus', 
		'Dem.Ophth.': 'Demosthenes Ophthalmicus', 
		'Dercyl.': 'Dercylus',
		'Dexipp.': 'Dexippus',
		'Diagor.': 'Diagoras', 
		'Dialex.': 'Dialexeis', 
		'Dicaearch.': 'Dicaearchus', 
		'Dicaearch.Hist.': 'Dicaearchus', 
		'Dicaeog.': 'Dicaeogenes', 
		'Did.': 'Didymus', 
		'Dieuch.': 'Dieuches',
		'Dieuchid.': 'Dieuchidas', 
		'Dig.': 'Digesta',
		'Din.': 'Dinarchus', 
		'Dinol.': 'Dinolochus', 
		'D.C.': 'Dio Cassius', 
		'D.Chr.': 'Dio Chrysostomus', 
		'Diocl.': 'Diocles', 
		'Diocl.Com.': 'Diocles', 
		'Diocl.Fr.': 'Diocles',
		'Diod.Com.': 'Diodorus', 
		'Diod.': 'Diodorus', 
		'Diod.Rh.': 'Diodorus',
		'Diod.Ath.': 'Diodorus Atheniensis', 
		'D.S.': 'Diodorus Siculus', 
		'Diod.Tars.': 'Diodorus Tarsensis', 
		'Diog.Apoll.': 'Diogenes Apolloniates', 
		'Diog.Ath.': 'Diogenes Atheniensis',
		'Diog.Bab.Stoic.': 'Diogenes Babylonius', 
		'Diog.': 'Diogenes Cynicus', 
		'D.L.': 'Diogenes Laertius', 
		'Diog.Oen.': 'Diogenes Oenoandensis', 
		'Diog.Sinop.': 'Diogenes Sinopensis', 
		'Diogenian.': 'Diogenianus',
		'Diogenian.Epicur.': 'Diogenianus Epicureus', 
		'Diom.': 'Diomedes',
		'Dionys.Com.': 'Dionysius', 
		'Dionys.': 'Dionysius',
		'Dionys.Trag.': 'Dionysius', 
		'Dion.Byz.': 'Dionysius Byzantius', 
		'Dion.Calliph.': 'Dionysius Calliphontis filius', 
		'Dionys.Eleg.': 'Dionysius Chalcus', 
		'D.H.': 'Dionysius Halicarnassensis', 
		'Dionys.Stoic.': 'Dionysius Heracleota', 
		'Dionys.Minor': 'Dionysius Minor',
		'D.P.': 'Dionysius Periegeta',
		'Dionys.Sam.': 'Dionysius Samius', 
		'D.T.': 'Dionysius Thrax', 
		'Diophan.': 'Diophanes',
		'Dioph.': 'Diophantus', 
		'Diosc.': 'Dioscorides', 
		'Diosc.Hist.': 'Dioscorides', 
		'Dsc.': 'Dioscorides (Dioscurides)', 
		'Diosc.Gloss.': 'Dioscorides Glossator',
		'Diotim.': 'Diotimus', 
		'Diotog.': 'Diotogenes',
		'Diox.': 'Dioxippus',
		'Diph.': 'Diphilus', 
		'Diph.Siph.': 'Diphilus Siphnius', 
		'Diyll.': 'Diyllus', 
		'Donat.': 'Donatus, Aelius', 
		'Doroth.': 'Dorotheus', 
		'Dosiad.': 'Dosiadas', 
		'Dosiad.Hist.': 'Dosiades',
		'Dosith.': 'Dositheus', 
		'Ecphantid.': 'Ecphantides', 
		'Ecphant.': 'Ecphantus',
		'Eleg.Alex.Adesp.': 'Elegiaca Alexandrina Adespota',
		'Emp.': 'Empedocles', 
		'1Enoch': 'Enoch', 
		'Ephipp.': 'Ephippus', 
		'Ephor.': 'Ephorus', 
		'Epic.Alex.Adesp.': 'Epica Alexandrina Adespota',
		'Epich.': 'Epicharmus', 
		'Epicr.': 'Epicrates', 
		'Epict.': 'Epictetus', 
		'Epicur.': 'Epicurus', 
		'Epig.': 'Epigenes',
		'Epil.': 'Epilycus', 
		'Epimenid.': 'Epimenides', 
		'Epin.': 'Epinicus', 
		'Erasistr.': 'Erasistratus', 
		'Eratosth.': 'Eratosthenes',
		'Erinn.': 'Erinna',
		'Eriph.': 'Eriphus', 
		'Erot.': 'Erotianus', 
		'Eryc.': 'Erycius', 
		'Etrusc.': 'Etruscus',
		'Et.Gen.': 'Etymologicum Genuinum',
		'Et.Gud.': 'Etymologicum Gudianum',
		'EM': 'Etymologicum Magnum',
		'Euang.': 'Euangelus',
		'Eubulid.': 'Eubulides',
		'Eub.': 'Eubulus', 
		'Euc.': 'Euclides', 
		'Eucrat.': 'Eucrates',
		'Eudem.': 'Eudemus', 
		'Eudox.': 'Eudoxus', 
		'Eudox.Com.': 'Eudoxus',
		'Eumel.': 'Eumelus', 
		'Eun.': 'Eunapius', 
		'Eunic.': 'Eunicus', 
		'Euod.': 'Euodus',
		'Euph.': 'Euphorio', 
		'Euphron.': 'Euphronius', 
		'Eup.': 'Eupolis', 
		'E.': 'Euripides', 
		'Euryph.': 'Euryphamus',
		'Eus.Hist.': 'Eusebius', 
		'Eus.': 'Eusebius Caesariensis', 
		'Eus.Mynd.': 'Eusebius Myndius',
		'Eust.': 'Eustathius', 
		'Eust.Epiph.': 'Eustathius Epiphaniensis', 
		'Eustr.': 'Eustratius', 
		'Euthycl.': 'Euthycles',
		'Eutoc.': 'Eutocius', 
		'Eutolm.': 'Eutolmius', 
		'Eutych.': 'Eutychianus', 
		'Even.': 'Evenus', 
		'Ezek.': 'Ezekiel', 
		'Favorin.': 'Favorinus',
		'Fest.': 'Festus', 
		'Firm.': 'Firmicus Maternus', 
		'Fortunat.Rh.': 'Fortunatianus', 
		'Gabriel.': 'Gabrielius', 
		'Gaet.': 'Gaetulicus, Cn. Lentulus', 
		'Gal.': 'Galenus', 
		'Gaud.Harm.': 'Gaudentius',
		'Gell.': 'Gellius, Aulus', 
		'Gem.': 'Geminus', 
		'Gp.': 'Geoponica',
		'Germ.': 'Germanicus Caesar', 
		'Glauc.': 'Glaucus',
		'Gloss.': 'Glossaria',
		'Gorg.': 'Gorgias', 
		'Greg.Cor.': 'Gregorius Corinthius', 
		'Greg.Cypr.': 'Gregorius Cyprius', 
		'Hadr.Rh.': 'Hadrianus', 
		'Hadr.': 'Hadrianus Imperator', 
		'Harmod.': 'Harmodius',
		'Harp.': 'Harpocratio', 
		'Harp.Astr.': 'Harpocratio', 
		'Hecat.Abd.': 'Hecataeus Abderita', 
		'Hecat.': 'Hecataeus Milesius', 
		'Hedyl.': 'Hedylus', 
		'Hegem.': 'Hegemon', 
		'Hegesand.': 'Hegesander',
		'Hegesian.': 'Hegesianax', 
		'Hegesipp.Com.': 'Hegesippus', 
		'Hegesipp.': 'Hegesippus',
		'Hld.': 'Heliodorus', 
		'Heliod.': 'Heliodorus', 
		'Heliod.Hist.': 'Heliodorus',
		'Hellad.': 'Helladius',
		'Hellanic.': 'Hellanicus', 
		'Hell.Oxy.': 'Hellenica Oxyrhynchia',
		'Hemerolog.Flor.': 'Hemerologium Florentinum',
		'Henioch.': 'Heniochus',
		'Heph.Astr.': 'Hephaestio', 
		'Heph.': 'Hephaestio',
		'Heracl.': 'Heraclas',
		'Heraclid.Com.': 'Heraclides',
		'Heraclid.Cum.': 'Heraclides Cumaeus', 
		'Heraclid.Lemb.': 'Heraclides Lembus', 
		'Heraclid.Pont.': 'Heraclides Ponticus', 
		'Heraclid.Sinop.': 'Heraclides Sinopensis',
		'Heraclid.': 'Heraclides Tarentinus', 
		'Heraclit.': 'Heraclitus',
		'Herill.Stoic.': 'Herillus Carthaginiensis', 
		'Herm.': 'Hermes Trismegistus',
		'Hermesian.': 'Hermesianax', 
		'Herm.Hist.': 'Hermias', 
		'Herm.Iamb.': 'Hermias',
		'Hermipp.': 'Hermippus', 
		'Hermipp.Hist.': 'Hermippus', 
		'Hermocl.': 'Hermocles', 
		'Hermocr.': 'Hermocreon',
		'Hermod.': 'Hermodorus',
		'Hermog.': 'Hermogenes', 
		'Herod.': 'Herodas', 
		'Hdn.': 'Herodianus',
		'Herodor.': 'Herodorus', 
		'Hdt.': 'Herodotus', 
		'Herod.Med.': 'Herodotus', 
		'Herophil.': 'Herophilus', 
		'Hes.': 'Hesiodus',
		'Hsch.Mil.': 'Hesychius Milesius', 
		'Hsch.': 'Hesychius', 
		'Hices.': 'Hicesius', 
		'Hierocl.': 'Hierocles', 
		'Hierocl.Hist.': 'Hierocles',
		'Hieronym.Hist.': 'Hieronymus Cardianus', 
		'Him.': 'Himerius', 
		'Hipparch.': 'Hipparchus', 
		'Hipparch.Com.': 'Hipparchus',
		'Hippias Erythr.': 'Hippias Erythraeus',
		'Hippiatr.': 'Hippiatrica',
		'Hp.': 'Hippocrates', 
		'Hippod.': 'Hippodamus',
		'Hippol.': 'Hippolytus', 
		'Hippon.': 'Hipponax', 
		'Hist.Aug.': 'Historiae Augustae Scriptores',
		'Hom.': 'Homerus',
		'Honest.': 'Honestus', 
		'Horap.': 'Horapollo', 
		'h.Hom.': 'Hymni Homerici',
		'Hymn.Mag.': 'Hymni Magici',
		'Hymn.Id.Dact.': 'Hymnus ad Idaeos Dactylos', 
		'Hymn.Is.': 'Hymnus ad Isim',
		'Hymn.Curet.': 'Hymnus Curetum', 
		'Hyp.': 'Hyperides', 
		'Hypsicl.': 'Hypsicles', 
		'Iamb.': 'Iamblichus', 
		'Iamb.Bab.': 'Iamblichus', 
		'Ibyc.': 'Ibycus', 
		'Il.': 'Ilias',
		'Il.Parv.': 'Ilias Parva',
		'Il.Pers.': 'Iliu Persis',
		'Iren.': 'Irenaeus', 
		'Is.': 'Isaeus', 
		'Isid.Trag.': 'Isidorus',
		'Isid.Aeg.': 'Isidorus Aegeates',
		'Isid.Char.': 'Isidorus Characenus', 
		'Isid.': 'Isidorus Hispalensis',
		'Isig.': 'Isigonus', 
		'Isoc.': 'Isocrates', 
		'Isyll.': 'Isyllus', 
		'Jo.Alex. vel Jo.Gramm.': 'Joannes Alexandrinus', 
		'Jo.Diac.': 'Joannes Diaconus',
		'Jo.Gaz.': 'Joannes Gazaeus', 
		'J.': 'Josephus', 
		'Jul.': 'Julianus Imperator', 
		'Jul. vel Jul.Aegypt.': 'Julianus Aegyptius', 
		'Jul.Laod.': 'Julianus Laodicensis', 
		'Junc.': 'Juncus', 
		'Just.': 'Justinianus', 
		'Juv.': 'Juvenalis, D. Junius', 
		'Lamprocl.': 'Lamprocles', 
		'Leo Phil.': 'Leo Philosophus', 
		'Leon.': 'Leonidas', 
		'Leonid.': 'Leonidas',
		'Leont.': 'Leontius', 
		'Leont. in Arat.': 'Leontius', 
		'Lesb.Gramm.': 'Lesbonax', 
		'Lesb.Rh.': 'Lesbonax', 
		'Leucipp.': 'Leucippus', 
		'Lex.Mess.': 'Lexicon Messanense',
		'Lex.Rhet.': 'Lexicon Rhetoricum',
		'Lex.Rhet.Cant.': 'Lexicon Rhetoricum Cantabrigiense',
		'Lex.Sabb.': 'Lexicon Sabbaiticum',
		'Lex. de Spir.': 'Lexicon de Spiritu',
		'Lex.Vind.': 'Lexicon Vindobonense',
		'Lib.': 'Libanius', 
		'Licymn.': 'Licymnius', 
		'Limen.': 'Limenius', 
		'Loll.': 'Lollius Bassus', 
		'Longin.': 'Longinus', 
		'Luc.': 'Lucianus',
		'Lucill.': 'Lucillius', 
		'Lyc.': 'Lycophron', 
		'Lycophronid.': 'Lycophronides', 
		'Lycurg.': 'Lycurgus', 
		'Lyd.': 'Lydus, Joannes Laurentius', 
		'Lync.': 'Lynceus',
		'Lyr.Adesp.': 'Lyrica Adespota',
		'Lyr.Alex.Adesp.': 'Lyrica Alexandrina Adespota',
		'Lys.': 'Lysias', 
		'Lysimachid.': 'Lysimachides',
		'Lysim.': 'Lysimachus', 
		'Lysipp.': 'Lysippus', 
		'Macar.': 'Macarius', 
		'Maced.': 'Macedonius',
		'Macr.': 'Macrobius', 
		'Maec.': 'Maecius', 
		'Magn.': 'Magnes', 
		'Magnus Hist.': 'Magnus', 
		'Maiist.': 'Maiistas', 
		'Malch.': 'Malchus', 
		'Mamerc.': 'Mamercus',
		'Man.': 'Manetho', 
		'Man.Hist.': 'Manetho', 
		'Mantiss.Prov.': 'Mantissa Proverbiorum',
		'Marcellin.': 'Marcellinus',
		'Marc.Sid.': 'Marcellus Sidetes', 
		'Marcian.': 'Marcianus', 
		'M.Ant.': 'Marcus Antoninus', 
		'Marc.Arg.': 'Marcus Argentarius', 
		'Maria Alch.': 'Maria', 
		'Marian.': 'Marianus', 
		'Marin.': 'Marinus', 
		'Mar.Vict.': 'Marius Victorinus', 
		'Mart.': 'Martialis', 
		'Mart.Cap.': 'Martianus Capella', 
		'Max.': 'Maximus', 
		'Max.Tyr.': 'Maximus Tyrius', 
		'Megasth.': 'Megasthenes', 
		'Melamp.': 'Melampus',
		'Melanipp.': 'Melanippides', 
		'Melanth.Hist.': 'Melanthius', 
		'Melanth.Trag.': 'Melanthius',
		'Mel.': 'Meleager', 
		'Meliss.': 'Melissus', 
		'Memn.': 'Memnon', 
		'Menaechm.': 'Menaechmus', 
		'Men.': 'Menander', 
		'Men.Rh.': 'Menander', 
		'Men.Eph.': 'Menander Ephesius',
		'Men.Prot.': 'Menander Protector', 
		'Menecl.': 'Menecles Barcaeus', 
		'Menecr.': 'Menecrates',
		'Menecr.Eph.': 'Menecrates Ephesius', 
		'Menecr.Xanth.': 'Menecrates Xanthius', 
		'Menemach.': 'Menemachus', 
		'Menesth.': 'Menesthenes',
		'Menipp.': 'Menippus', 
		'Menodot.': 'Menodotus Samius', 
		'Mesom.': 'Mesomedes', 
		'Metag.': 'Metagenes', 
		'Metrod.': 'Metrodorus',
		'Metrod.Chius': 'Metrodorus Chius', 
		'Metrod.Sceps.': 'Metrodorus Scepsius', 
		'Mich.': 'Michael Ephesius', 
		'Mimn.': 'Mimnermus', 
		'Mimn.Trag.': 'Mimnermus',
		'Minuc.': 'Minucianus', 
		'Mithr.': 'Mithradates', 
		'Mnasalc.': 'Mnasalcas', 
		'Mnesim.': 'Mnesimachus', 
		'Mnesith.Ath.': 'Mnesitheus Atheniensis', 
		'Mnesith.Cyz.': 'Mnesitheus Cyzicenus',
		'Moer.': 'Moeris', 
		'MoschioTrag.': 'Moschio', 
		'Mosch.': 'Moschus', 
		'Muc.Scaev.': 'Mucius Scaevola',
		'Mund.': 'Mundus Munatius',
		'Musae.': 'Musaeus',
		'Music.': 'Musicius',
		'Muson.': 'Musonius', 
		'Myrin.': 'Myrinus',
		'Myrsil.': 'Myrsilus',
		'Myrtil.': 'Myrtilus', 
		'Naumach.': 'Naumachius', 
		'Nausicr.': 'Nausicrates', 
		'Nausiph.': 'Nausiphanes', 
		'Neanth.': 'Neanthes', 
		'Nearch.': 'Nearchus',
		'Nech.': 'Nechepso', 
		'Neophr.': 'Neophron', 
		'Neoptol.': 'Neoptolemus', 
		'Nicaenet.': 'Nicaenetus', 
		'Nic.': 'Nicander', 
		'Nicarch.': 'Nicarchus',
		'Nicoch.': 'Nicochares', 
		'Nicocl.': 'Nicocles',
		'Nicod.': 'Nicodemus',
		'Nicol.Com.': 'Nicolaus', 
		'Nicol.': 'Nicolaus',
		'Nic.Dam.': 'Nicolaus Damascenus', 
		'Nicom.Com.': 'Nicomachus',
		'Nicom.Trag.': 'Nicomachus',
		'Nicom.': 'Nicomachus Gerasenus', 
		'Nicostr.Com.': 'Nicostratus', 
		'Nicostr.': 'Nicostratus',
		'Nonn.': 'Nonnus', 
		'Noss.': 'Nossis', 
		'Numen.': 'Numenius Apamensis',
		'Nymphod.': 'Nymphodorus',
		'Ocell.': 'Ocellus Lucanus', 
		'Od.': 'Odyssea',
		'Oenom.': 'Oenomaus', 
		'Olymp.Alch.': 'Olympiodorus', 
		'Olymp.Hist.': 'Olympiodorus', 
		'Olymp.': 'Olympiodorus', 
		'Onat.': 'Onatas',
		'Onos.': 'Onosander (Onasander)', 
		'Ophel.': 'Ophelio', 
		'Opp.': 'Oppianus',
		'Orac.Chald.': 'Oracula Chaldaica',
		'Orib.': 'Oribasius', 
		'Orph.': 'Orphica',
		'Pae.Delph.': 'Paean Delphicus', 
		'Pae.Erythr.': 'Paean Erythraeus', 
		'Palaeph.': 'Palaephatus',
		'Palch.': 'Palchus', 
		'Pall.': 'Palladas',
		'Pamphil.': 'Pamphilus',
		'Pancrat.': 'Pancrates',
		'Panyas.': 'Panyasis',
		'Papp.': 'Pappus', 
		'Parm.': 'Parmenides', 
		'Parmen.': 'Parmenio',
		'Parrhas.': 'Parrhasius', 
		'Parth.': 'Parthenius', 
		'Patrocl.': 'Patrocles Thurius',
		'Paul.Aeg.': 'Paulus Aegineta', 
		'Paul.Al.': 'Paulus Alexandrinus', 
		'Paul.Sil.': 'Paulus Silentiarius', 
		'Paus.': 'Pausanias', 
		'Paus.Dam.': 'Pausanias Damascenus', 
		'Paus.Gr.': 'Pausanias Grammaticus',
		'Pediasim.': 'Pediasimus',
		'Pelag.Alch.': 'Pelagius', 
		'Pempel.': 'Pempelus',
		'Perict.': 'Perictione',
		'Peripl.M.Rubr.': 'Periplus Maris Rubri', 
		'Pers.Stoic.': 'Persaeus Citieus', 
		'Pers.': 'Perses',
		'Petos.': 'Petosiris',
		'Petron.': 'Petronius',
		'Petr.Patr.': 'Petrus Patricius', 
		'Phaedim.': 'Phaedimus', 
		'Phaënn.': 'Phaënnus', 
		'Phaest.': 'Phaestus',
		'Phal.': 'Phalaecus', 
		'Phalar.': 'Phalaris',
		'Phan.': 'Phanias',
		'Phan.Hist.': 'Phanias', 
		'Phanocl.': 'Phanocles', 
		'Phanod.': 'Phanodemus', 
		'Pherecr.': 'Pherecrates', 
		'Pherecyd.': 'Pherecydes Lerius', 
		'Pherecyd.Syr.': 'Pherecydes Syrius', 
		'Philagr.': 'Philagrius', 
		'Philem.': 'Philemo', 
		'Philem.Jun.': 'Philemo Junior', 
		'Philetaer.': 'Philetaerus', 
		'Philet.': 'Philetas', 
		'Philippid.': 'Philippides', 
		'Philipp.Com.': 'Philippus', 
		'Phil.': 'Philippus', 
		'Philisc.Com.': 'Philiscus',
		'Philisc.Trag.': 'Philiscus',
		'Philist.': 'Philistus', 
		'Ph.Epic.': 'Philo',
		'Ph.': 'Philo', 
		'Ph.Bybl.': 'Philo Byblius', 
		'Ph.Byz.': 'Philo Byzantius',
		'Ph.Tars.': 'Philo Tarsensis',
		'Philoch.': 'Philochorus', 
		'Philocl.': 'Philocles',
		'Philod.Scarph.': 'Philodamus Scarpheus', 
		'Phld.': 'Philodemus',
		'Philol.': 'Philolaus', 
		'Philomnest.': 'Philomnestus',
		'Philonid.': 'Philonides', 
		'Phlp.': 'Philoponus, Joannes', 
		'Philosteph.Com.': 'Philostephanus',
		'Philosteph.Hist.': 'Philostephanus',
		'Philostr.': 'Philostratus', 
		'Philostr.Jun.': 'Philostratus Junior', 
		'Philox.': 'Philoxenus', 
		'Philox.Gramm.': 'Philoxenus',
		'Philum.': 'Philumenus', 
		'Philyll.': 'Philyllius', 
		'Phint.': 'Phintys',
		'Phleg.': 'Phlegon Trallianus', 
		'Phoc.': 'Phocylides', 
		'Phoeb.': 'Phoebammon', 
		'Phoenicid.': 'Phoenicides', 
		'Phoen.': 'Phoenix', 
		'Phot.': 'Photius', 
		'Phryn.': 'Phrynichus', 
		'Phryn.Com.': 'Phrynichus', 
		'Phryn.Trag.': 'Phrynichus', 
		'Phylarch.': 'Phylarchus', 
		'Phylotim.': 'Phylotimus',
		'Pi.': 'Pindarus', 
		'Pisand.': 'Pisander',
		'Pittac.': 'Pittacus', 
		'Placit.': 'Placita Philosophorum',
		'Pl.Com.': 'Plato', 
		'Pl.': 'Plato', 
		'Pl.Jun.': 'Plato Junior',
		'Platon.': 'Platonius',
		'Plaut.': 'Plautus', 
		'Plin.': 'Plinius', 
		'Plot.': 'Plotinus', 
		'Plu.': 'Plutarchus', 
		'Poet. de herb.': 'Poeta',
		'Polem.Hist.': 'Polemo', 
		'Polem.Phgn.': 'Polemo',
		'Polem.': 'Polemo Sophista', 
		'Polioch.': 'Poliochus',
		'Poll.': 'Pollux', 
		'Polyaen.': 'Polyaenus',
		'Plb.': 'Polybius', 
		'Plb.Rh.': 'Polybius Sardianus',
		'Polycharm.': 'Polycharmus',
		'Polyclit.': 'Polyclitus', 
		'Polycr.': 'Polycrates',
		'Polystr.': 'Polystratus',
		'Polyzel.': 'Polyzelus', 
		'Pomp.': 'Pompeius', 
		'Pomp.Mac.': 'Pompeius Macer',
		'Porph.': 'Porphyrius Tyrius', 
		'Posidipp.': 'Posidippus',
		'Posidon.': 'Posidonius',
		'Pratin.': 'Pratinas', 
		'Praxag.': 'Praxagoras', 
		'Praxill.': 'Praxilla', 
		'Priscian.': 'Priscianus', 
		'Prisc.Lyd.': 'Priscianus Lydus', 
		'Prisc.': 'Priscus', 
		'Procl.': 'Proclus', 
		'Procop.': 'Procopius Caesariensis', 
		'Procop.Gaz.': 'Procopius Gazaeus', 
		'Prodic.': 'Prodicus', 
		'Promathid.': 'Promathidas', 
		'Protag.': 'Protagoras', 
		'Protagorid.': 'Protagoridas', 
		'Proxen.': 'Proxenus', 
		'Psalm.Solom.': 'Psalms of Solomon', 
		'Ps.-Callisth.': 'Pseudo-Callisthenes',
		'Ps.-Phoc.': 'Pseudo-Phocylidea', 
		'Ptol.': 'Ptolemaeus',
		'Ptol.Ascal.': 'Ptolemaeus Ascalonita',
		'Ptol.Chenn.': 'Ptolemaeus Chennos', 
		'Ptol.Euerg.': 'Ptolemaeus Euergetes II', 
		'Ptol.Megalop.': 'Ptolemaeus Megalopolitanus',
		'Pythaen.': 'Pythaenetus',
		'Pythag.': 'Pythagoras', 
		'Pythag. Ep.': 'Pythagorae et Pythagoreorum Epistulae',
		'Pythocl.': 'Pythocles',
		'Quint.': 'Quintilianus', 
		'Q.S.': 'Quintus Smyrnaeus', 
		'Rh.': 'Rhetores Graeci',
		'Rhetor.': 'Rhetorius', 
		'Rhian.': 'Rhianus', 
		'Rhinth.': 'Rhinthon', 
		'Rufin.': 'Rufinus',
		'Ruf.': 'Rufus', 
		'Ruf.Rh.': 'Rufus',
		'Rutil.': 'Rutilius Lupus',
		'Tull.Sab.': 'Sabinus, Tullius', 
		'Sacerd.': 'Sacerdos, Marius Plotius', 
		'Sallust.': 'Sallustius', 
		'Sannyr.': 'Sannyrio', 
		'Sapph.': 'Sappho', 
		'Satyr.': 'Satyrus',
		'Scol.': 'Scolia',
		'Scyl.': 'Scylax', 
		'Scymn.': 'Scymnus', 
		'Scythin.': 'Scythinus',
		'Secund.': 'Secundus', 
		'Seleuc.': 'Seleucus',
		'Seleuc.Lyr.': 'Seleucus',
		'Semon.': 'Semonides', 
		'Seren.': 'Serenus',
		'Serv.': 'Servius', 
		'Sever.': 'Severus',
		'Sext.': 'Sextus',
		'S.E.': 'Sextus Empiricus', 
		'Silen.': 'Silenus', 
		'Simm.': 'Simmias', 
		'Simon.': 'Simonides', 
		'Simp.': 'Simplicius',
		'Simyl.': 'Simylus',
		'Socr.Arg.': 'Socrates Argivus',
		'Socr.Cous': 'Socrates Cous',
		'Socr.Rhod.': 'Socrates Rhodius', 
		'Socr.': 'Socratis et Socraticorum Epistulae', 
		'Sol.': 'Solon', 
		'Sopat.': 'Sopater',
		'Sopat.Rh.': 'Sopater', 
		'Sophil.': 'Sophilus', 
		'S.': 'Sophocles', 
		'Sophon': 'Sophonias', 
		'Sophr.': 'Sophron', 
		'Sor.': 'Soranus', 
		'Sosib.': 'Sosibius', 
		'Sosicr.': 'Sosicrates',
		'Sosicr.Hist.': 'Sosicrates',
		'Sosicr.Rhod.': 'Sosicrates Rhodius',
		'Sosip.': 'Sosipater', 
		'Sosiph.': 'Sosiphanes', 
		'Sosith.': 'Sositheus',
		'Sostrat.': 'Sostratus',
		'Sosyl.': 'Sosylus', 
		'Sotad.Com.': 'Sotades',
		'Sotad.': 'Sotades', 
		'Speus.': 'Speusippus', 
		'Sphaer.Hist.': 'Sphaerus',
		'Sphaer.Stoic.': 'Sphaerus', 
		'Stad.': 'Stadiasmus', 
		'Staphyl.': 'Staphylus',
		'Stat.Flacc.': 'Statyllius Flaccus', 
		'Steph.Com.': 'Stephanus', 
		'Steph.': 'Stephanus',
		'St.Byz.': 'Stephanus Byzantius', 
		'Stesich.': 'Stesichorus', 
		'Stesimbr.': 'Stesimbrotus', 
		'Sthenid.': 'Sthenidas',
		'Stob.': 'Stobaeus, Joannes', 
		'Stoic.': 'Stoicorum Veterum Fragmenta',
		'Str.': 'Strabo', 
		'Strato Com.': 'Strato', 
		'Strat.': 'Strato', 
		'Stratt.': 'Strattis', 
		'Suet.': 'Suetonius', 
		'Suid.': 'Suidas', 
		'Sulp.Max.': 'Sulpicius Maximus', 
		'Sus.': 'Susario', 
		'Sm.': 'Symmachus', 
		'Syn.Alch.': 'Synesius', 
		'Syrian.': 'Syrianus', 
		'Telecl.': 'Teleclides', 
		'Telesill.': 'Telesilla', 
		'Telest.': 'Telestes', 
		'Ter.Maur.': 'Terentianus Maurus', 
		'Ter.Scaur.': 'Terentius Scaurus', 
		'Terp.': 'Terpander', 
		'Thal.': 'Thales', 
		'Theaet.': 'Theaetetus', 
		'Theagen.': 'Theagenes',
		'Theag.': 'Theages',
		'Themiso Hist.': 'Themiso',
		'Them.': 'Themistius', 
		'Themist.': 'Themistocles', 
		'Theocl.': 'Theocles', 
		'Theoc.': 'Theocritus', 
		'Theodect.': 'Theodectes', 
		'Theodorid.': 'Theodoridas', 
		'Theod.': 'Theodorus',
		'Theodos.': 'Theodosius Alexandrinus', 
		'Thd.': 'Theodotion', 
		'Theognet.': 'Theognetus',
		'Thgn.': 'Theognis', 
		'Thgn.Trag.': 'Theognis', 
		'Thgn.Hist.': 'Theognis Rhodius',
		'Theognost.': 'Theognostus', 
		'Theol.Ar.': 'Theologumena Arithmeticae',
		'Theolyt.': 'Theolytus',
		'Theon Gymn.': 'Theon Gymnasiarcha',
		'Theo Sm.': 'Theon Smyrnaeus', 
		'Theoph.': 'Theophanes',
		'Theophil.': 'Theophilus',
		'Thphr.': 'Theophrastus', 
		'Theopomp.Com.': 'Theopompus', 
		'Theopomp.Hist.': 'Theopompus', 
		'Theopomp.Coloph.': 'Theopompus Colophonius',
		'Thom.': 'Thomas', 
		'Thom.Mag.': 'Thomas Magister', 
		'Thrasym.': 'Thrasymachus', 
		'Th.': 'Thucydides', 
		'Thugen.': 'Thugenides',
		'Thyill.': 'Thyillus', 
		'Thymocl.': 'Thymocles',
		'Tib.': 'Tiberius',
		'Tib.Ill.': 'Tiberius Illustrius', 
		'Tim.': 'Timaeus',
		'Timae.': 'Timaeus', 
		'Ti.Locr.': 'Timaeus Locrus',
		'Timag.': 'Timagenes', 
		'Timocl.': 'Timocles', 
		'Timocr.': 'Timocreon', 
		'Timostr.': 'Timostratus', 
		'Tim.Com.': 'Timotheus',
		'Tim.Gaz.': 'Timotheus Gazaeus',
		'Titanomach.': 'Titanomachia',
		'Trag.Adesp.': 'Tragica Adespota',
		'Trophil.': 'Trophilus',
		'Tryph.': 'Tryphiodorus',
		'Tull.Flacc.': 'Tullius Flaccus',
		'Tull.Gem.': 'Tullius Geminus',
		'Tull.Laur.': 'Tullius Laurea', 
		'Tymn.': 'Tymnes',
		'Tyrt.': 'Tyrtaeus', 
		'Tz.': 'Tzetzes, Joannes', 
		'Ulp.': 'Ulpianus', 
		'Uran.': 'Uranius', 
		'Vel.Long.': 'Velius Longus', 
		'Vett.Val.': 'Vettius Valens', 
		'LXX': 'Vetus Testamentum Graece redditum',
		'Vit.Philonid.': 'Vita Philonidis Epicurei',
		'Vit.Hom.': 'Vitae Homeri',
		'Vitr.': 'Vitruvius',
		'Xanth.': 'Xanthus',
		'Xenag.': 'Xenagoras',
		'Xenarch.': 'Xenarchus',
		'Xenocl.': 'Xenocles',
		'Xenocr.': 'Xenocrates',
		'Xenoph.': 'Xenophanes',
		'X.': 'Xenophon',
		'X.Eph.': 'Xenophon Ephesius',
		'Zaleuc.': 'Zaleucus',
		'Zelot.': 'Zelotus',
		'ZenoStoic.': 'Zeno Citieus',
		'Zeno Eleat.': 'Zeno Eleaticus',
		'Zeno Tars.Stoic.': 'Zeno Tarsensis',
		'Zen.': 'Zenobius',
		'Zenod.': 'Zenodotus',
		'Zonae.': 'Zonaeus',
		'Zonar.': 'Zonaras',
		'Zon.': 'Zonas',
		'Zopyr.Hist.': 'Zopyrus',
		'Zopyr.': 'Zopyrus',
		'Zos.Alch.': 'Zosimus',
		'Zos.': 'Zosimus',
	}

	return authordict


def deabrevviatelatinauthors():
	"""

	the latin dictionary xml does not help you to generate this dict

	:return:
	"""

	authordict = {
		'Anthol. Lat.': 'Latin Anthology',
		'Auct. Her.': 'Rhetorica ad Herennium',
		'Caes.': 'Caesar',
		'Cat.': 'Catullus',
		'Cels.': 'Celsus',
		'Cic.': 'Cicero',
		'Col.': 'Columella',
		'Curt.': 'Quntus Curtius Rufus',
		'Dig.': 'Digest of Justinian',
		'Enn.': 'Ennius',
		'Fest.': 'Festus',
		'Flor.': 'Florus',
		'Front.': 'Frontinus',
		'Gell.': 'Gellius',
		'Hor.': 'Horace',
		'Isid.': 'Isidore',
		'Just.': 'Justinian',
		'Juv.': 'Juvenal',
		'Lact.': 'Lactantius',
		'Liv.': 'Livy',
		'Luc.': 'Lucan',
		'Lucr.': 'Lucretius',
		'Macr.': 'Macrobius',
		'Mart.': 'Martial',
		'Nep.': 'Nepos',
		'Non.': 'Nonius',
		'Ov.': 'Ovid',
		'Pall.': 'Palladius',
		'Pers.': 'Persius',
		'Petr.': 'Petronius',
		'Phaedr.': 'Phaedrus',
		'Plaut.': 'Plautus',
		'Plin.': 'Pliny',
		'Prop.': 'Propertius',
		'Quint.': 'Quintilian',
		'Sall.': 'Sallust',
		'Sen.': 'Seneca',
		'Sil.': 'Silius Italicus',
		'Stat.': 'Statius',
		'Suet.': 'Suetonius',
		'Tac.': 'Tacitus',
		'Ter.': 'Terence',
		'Tert.': 'Tertullian',
		'Val. Fl.': 'Valerius Flaccus',
		'Val. Max.': 'Valerius Maxiumus',
		'Varr.': 'Varro',
		'Vell.': 'Velleius',
		'Verg.': 'Vergil',
		'Vitr.': 'Vitruvius'
	}

	return authordict