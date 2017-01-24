# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.lexica.lexicaformatting import entrysummary, formatdictionarysummary, grabheadmaterial, grabsenses, \
	formatgloss, formatmicroentry, insertbrowserlookups, insertbrowserjs, formateconsolidatedgrammarentry
from server.listsandsession.listmanagement import polytonicsort


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
		"ὁ κύριοϲ θεὸϲ καταβή-"


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

def lexicalmatchesintohtml(observedform, matcheslist, usedictionary, cursor):
	"""

	you have found the word(s), now generate a collection of HTML lines to hand to the JS
	this is a sort of pseudo-page

	first do the parsing results; then do the dictionary results

	observedform:
		nubibus

	matcheslist:
		[('<possibility_1>', '1', 'nūbibus,nubes', '50817064', '<transl>a cloud</transl><analysis>fem abl pl</analysis>'), ('<possibility_2>', '2', 'nūbibus,nubes', '50817064', '<transl>a cloud</transl><analysis>fem dat pl</analysis>'), ('<possibility_3>', '3', 'nūbibus,nubis', '50839960', '<transl>a cloud</transl><analysis>masc abl pl</analysis>'), ('<possibility_4>', '4', 'nūbibus,nubis', '50839960', '<transl>a cloud</transl><analysis>masc dat pl</analysis>')]

	usedictionary:
		latin

	:param observedform:
	:param matcheslist:
	:param usedictionary:
	:param cursor:
	:return:
	"""

	returnarray = []
	differentwordsfound = {}
	entriestocheck = {}
	for m in matcheslist:
		if m[3] not in differentwordsfound:
			differentwordsfound[m[3]] = [(m[2], m[4])]
		else:
			differentwordsfound[m[3]].append((m[2], m[4]))
	# the top part: just the analyses
	transfinder = re.compile(r'<transl>(.*?)</transl>')
	analysisfinder = re.compile(r'<analysis>(.*?)</analysis>')
	count = 0
	for w in differentwordsfound:
		count += 1
		# {'50817064': [('nūbibus,nubes', '<transl>a cloud</transl><analysis>fem abl pl</analysis>'), ('nūbibus,nubes', '<transl>a cloud</transl><analysis>fem dat pl</analysis>')], '50839960': [('nūbibus,nubis', '<transl>a cloud</transl><analysis>masc abl pl</analysis>'), ('nūbibus,nubis', '<transl>a cloud</transl><analysis>masc dat pl</analysis>')]}
		theentry = differentwordsfound[w]
		wordandform = theentry[0][0]
		wordandform = wordandform.split(',')
		form = wordandform[0]
		try:
			theword = wordandform[1]
		except:
			theword = form
		thetransl = re.search(transfinder, theentry[0][1])
		thetransl = thetransl.group(1)
		analyses = [re.search(analysisfinder, x[1]) for x in theentry]
		analysislist = [x.group(1) for x in analyses]
		consolidatedentry = {'count': count, 'form': observedform, 'word': theword, 'transl': thetransl,
							 'anal': analysislist}
		returnarray.append({'value': formateconsolidatedgrammarentry(consolidatedentry)})
		entriestocheck[w] = theword

	# look up and format the dictionary entries

	if len(entriestocheck) == 1:
		entry = entriestocheck.popitem()
		entryashtml = browserdictionarylookup(0, entry[1], usedictionary, cursor)
		returnarray.append({'value': entryashtml})
	else:
		count = 0
		for entry in entriestocheck:
			count += 1
			entryashtml = browserdictionarylookup(count, entriestocheck[entry], usedictionary, cursor)
			returnarray.append({'value': entryashtml})

	return returnarray


def browserdictionarylookup(count, entry, dict, cursor):
	"""
	look up a word and return an htlm version of its dictionary entry
	:param entry:
	:param dict:
	:param cursor:
	:return:
	"""

	if dict == 'greek':
		translationlabel = 'tr'
	else:
		translationlabel = 'hi'

	# mismatch between homonymns as per the lemmas and the dictionary: "λέγω1" vs "λέγω (1)"
	# a potential moving target if things change with the builder
	
	if re.search(r'\d$',entry) is not None:
		entry = re.sub(r'(.*?)(\d)',r'\1 (\2)',entry)

	try:
		found = searchdictionary(cursor, dict+'_dictionary', 'entry_name', entry, syntax='=')
	except:
		found = ('', '', '')
		
	if found == ('', '', ''):
		try:
			found = searchdictionary(cursor, dict + '_dictionary', 'entry_name', entry+' %', syntax='LIKE')
		except:
			found = ('','', '')

	metrics = found[0]
	definition = found[1]
	type = found[2]
	metrics = re.sub(r'\(\d{1,}\)',r'',metrics)
	
	# can't have xml in our html
	definition = re.sub(r'<title>(.*?)</title>', r'<worktitle>\1</worktitle>', definition)
	
	cleanedentry = ''
	
	if definition != '' and type != 'gloss':
		if count == 0:
			cleanedentry += '<hr /><p class="dictionaryheading">'+entry
		else:
			cleanedentry += '<hr /><p class="dictionaryheading">(' + str(count) + ')&nbsp;' + entry
		if u'\u0304' in metrics or u'\u0306' in metrics:
			cleanedentry += '&nbsp;<span class="metrics">['+metrics+']</span>'
		cleanedentry += '</p>\n'
		summarydict = entrysummary(definition, dict, translationlabel)

		if len(summarydict['authors']) == 0 and len(summarydict['senses']) == 0 and len(summarydict['quotes']) == 0:
			# this is basically just a gloss entry
			cleanedentry += formatmicroentry(definition)
		else:
			cleanedentry += formatdictionarysummary(summarydict)
			cleanedentry += grabheadmaterial(definition) + '<br />\n'
			senses = grabsenses(definition)
			if len(senses) > 0:
				for n in senses:
					cleanedentry += n
			else:
				cleanedentry += formatmicroentry(definition)
	elif definition != '' and type == 'gloss':
		cleanedentry += '<br />\n<p class="dictionaryheading">' + entry + '<span class="metrics">[gloss]</span></p>\n'
		cleanedentry += formatgloss(definition)
	else:
		cleanedentry += '<br />\n<p class="dictionaryheading">nothing found under '+entry+'</p>\n'
		cleanedentry += 'But the parser can get fooled by enclitics, spelling variations, and disagreement about the number of entries for a word.<br />'
		cleanedentry += 'Try looking this word yourself by using the proper search box: something is likely to turn up.'
	
	clickableentry = cleanedentry
	# in progress
	clickableentry = insertbrowserlookups(cleanedentry)
	clickableentry = insertbrowserjs(clickableentry)
	
	return clickableentry


def searchdictionary(cursor, dictionary, usecolumn, seeking, syntax):
	"""
	duplicates dbfunctions fnc, but that one was hurling exceptions if you tried to call it
	could not even get to the first line of the fnc
	:param cursor:
	:param dictionary:
	:param usecolumn:
	:param seeking:
	:return:
	"""
		
	query = 'SELECT metrical_entry, entry_body, entry_type FROM ' + dictionary + ' WHERE '+usecolumn+' '+syntax+' %s'
	data = (seeking,)
	cursor.execute(query, data)
	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	found = cursor.fetchone()
	
	if found is not None:
		return found
	else:
		return ('','','')


def bulkddictsearch(cursor, dictionary, usecolumn, seeking):
	"""
	fetchall vs fetchone
	only called by the lemma lookups; don't confuse this with the dictionary search up in views.py
	:param cursor:
	:param dictionary:
	:param usecolumn:
	:param seeking:
	:return:
	"""
	
	query = 'SELECT * FROM ' + dictionary + ' WHERE '+usecolumn+' ~* %s'
	data = (seeking,)
	cursor.execute(query, data)

	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	found = cursor.fetchall()

	# the results should be given the polytonicsort() treatment
	sortedfinds = []
	finddict = {}
	for f in found:
		finddict[f[0]] = f
	keys = finddict.keys()
	keys = polytonicsort(keys)
	
	for k in keys:
		sortedfinds.append(finddict[k])

	return sortedfinds


def findlemma(word, cursor):
	# note that lemma entries are internally separated by tabs and SQL does not escape special chars
	# fortunately even the first item has a lieading tab
	# SELECT * from greek_lemmata WHERE derivative_forms LIKE '%'||chr(9)||'θρηνεῖν %'
	finder = re.compile(r'^'+word+' ')

	query = 'SELECT * FROM '+session['usewhichdictionary']+'_lemmata WHERE derivative_forms LIKE %s||chr(9)||%s'
	data = ('%',word+' %')
	cursor.execute(query, data)
	lemmata = cursor.fetchall()
	dictonary = {}
	for lem in lemmata:
		variants = lem[2].split('\t')
		morphology = ''
		for var in variants:
			if re.search(finder,var) is not None:
				morphology += var+', '
		dictonary[lem[0]] = morphology[:-2]
	return dictonary


def findotherforms(xref_number, cursor):
	query = 'SELECT derivative_forms FROM ' + session['usewhichdictionary'] + '_lemmata where xref_number = %s'
	data = (xref_number,)
	cursor.execute(query, data)
	analysis = cursor.fetchone()
	analysis = list(analysis)

	anaylsys = analysis[0].split('\t')
	analysis[:] = ['<parsed>'+x+'</parsed>' for x in anaylsys if x != '']
	oneliner = '\n'.join(analysis)
	return oneliner


def definebylemma(lemmadict,corporatable,cursor):
	# the diogenes implementation: <basefont><a onClick="parse_lat('Arma')">Arma</a> <a onClick="parse_lat('uirumque')"><font color="red"><b><u>uirum</u></b></font>que</a>
	# <a onClick="parse_lat('cano')">cano,</a> <a onClick="parse_lat('Troiae')">Troiae</a> <a onClick="parse_lat('qui')">qui</a> <a onClick="parse_lat('primus')">primus</a>
	# <a onClick="parse_lat('ab')">ab</a> <a onClick="parse_lat('oris')">oris</a> <br> ...

	# stackoverflow:
	# Putting the onclick within the href would offend those who believe strongly in separation of content from behavior/action. The argument is that your html content should remain focused solely on content, not on presentation or behavior.
	# The typical path these days is to use a javascript library (eg. jquery) and create an event handler using that library. It would look something like:
	# $('a').click( function(e) {e.preventDefault(); /*your_code_here;*/ return false; } );
	# also consider using 'title' here

	# feed me findlemma stuff
	# {'δείδω': 'δεῖϲαι (aor imperat mid 2nd sg) (aor inf act)', 'δεῖϲα': 'δεῖϲαι (fem nom/voc pl)'}
	dictionaryentries = []
	for key,value in lemmadict.items():
		entry = bulkddictsearch(cursor, corporatable + '_dictionary', 'entry_name', key)
		dictionaryentries.append('<p class="lemma">'+value+'</p>\n<p class="dictionaryentry">'+entry+'</p>\n')
	return dictionaryentries

