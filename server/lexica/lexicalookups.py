# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from flask import session
from server.dbsupport.dbfunctions import setconnection
from server.lexica.lexicaformatting import entrysummary, formatdictionarysummary, grabheadmaterial, grabsenses, \
	formatgloss, formatmicroentry, insertbrowserlookups, insertbrowserjs, formateconsolidatedgrammarentry
from server.listsandsession.listmanagement import polytonicsort
from server.searching.betacodetounicode import stripaccents
from server.hipparchiaclasses import dbWordCountObject, dbHeadwordObject
from server import hipparchia

def lookformorphologymatches(word, usedictionary, cursor, trialnumber=0):
	"""

	:param word:
	:param usedictionary:
	:return:
	"""

	trialnumber += 1

	possible = re.compile(r'(<possibility_(\d{1,2})>)(.*?)<xref_value>(.*?)</xref_value>(.*?)</possibility_\d{1,2}>')
	# the things that can confuse me
	terminalacute = re.compile(r'[άέίόύήώ]')

	matches = None

	if usedictionary == 'latin':
		word = re.sub(r'[uv]', '[uv]', word)
		word = '^'+word+'$'
		syntax = '~'
	else:
		syntax = '='

	query = 'SELECT possible_dictionary_forms FROM ' + usedictionary + '_morphology WHERE observed_form '+syntax+' %s'
	data = (word,)

	cursor.execute(query, data)

	analysis = cursor.fetchone()

	if analysis:
		matches = re.findall(possible, analysis[0])
		# 1 = #, 2 = word, 4 = body, 3 = xref
	else:
		# this code lets you make multiple stabs at an answer if you have already failed once
		# [a] something like πλακουντάριόν τι will fail because of the enclitic (greek_morphology can find πλακουντάριον and πλακουντάριοϲ)
		# [b] something like προχοίδιόν τι will fail twice over because of the enclitic and the diaresis
		# item [b] cannot be fully addressed here; this correction gives you an analysis, but the term can't yet be found in the dictionary
		# greek_morphology has προχοίδιον; the greek_dictionary has προχοΐδιον
		try:
			# have to 'try' because there might not be a word[-2]
			if re.search(terminalacute,word[-1]) is not None and trialnumber < 3:
				sub = stripaccents(word[-1])
				newword = word[:-1]+sub
				matches = lookformorphologymatches(newword, usedictionary, cursor, trialnumber)
			elif re.search(terminalacute,word[-2]) is not None and trialnumber < 3:
				sub = stripaccents(word[-2])
				newword = word[:-2] + sub + word[-1]
				matches = lookformorphologymatches(newword, usedictionary, cursor, trialnumber)
		except:
			matches = None

	return matches


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

	transfinder = re.compile(r'<transl>(.*?)</transl>')
	analysisfinder = re.compile(r'<analysis>(.*?)</analysis>')

	# the top part of the HTML: just the analyses
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


def browserdictionarylookup(count, entry, usedictionary, cursor, suppressprevalence=False):
	"""
	look up a word and return an htlm version of its dictionary entry
	:param entry:
	:param dict:
	:param cursor:
	:return:
	"""

	if usedictionary == 'greek':
		translationlabel = 'tr'
	else:
		translationlabel = 'hi'

	nothingfound = { 'metrics': '', 'definition': '', 'type': '' }

	# mismatch between homonymns as per the lemmas and the dictionary: "λέγω1" vs "λέγω (1)"
	# a potential moving target if things change with the builder

	entry = re.sub(r'#','',entry)

	if re.search(r'\d$',entry) is not None:
		entry = re.sub(r'(.*?)(\d)',r'\1 (\2)',entry)

	founddict = searchdictionary(cursor, usedictionary+'_dictionary', 'entry_name', entry, syntax='=')

	metrics = founddict['metrics']
	definition = founddict['definition']
	type = founddict['type']
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

		if hipparchia.config['SHOWGLOBALWORDCOUNTS'] == 'yes' and suppressprevalence==False:
			countobject = findtotalcounts(entry, cursor)
			if countobject:
				cleanedentry += '<p class="wordcounts">Prevalence (all forms): '
				cleanedentry += formatprevalencedata(countobject)
				cleanedentry += '</p>\n'

		if hipparchia.config['SHOWLEXICALSUMMARYINFO'] == 'yes':
			summarydict = entrysummary(definition, usedictionary, translationlabel)
		else:
			summarydict = {'authors': '', 'senses': '', 'quotes': ''}

		if len(summarydict['authors']) == 0 and len(summarydict['senses']) == 0 and len(summarydict['quotes']) == 0:
			# either you have turned off summary info or this is basically just a gloss entry
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
		if '-' in entry:
			parts = entry.split('-')
			partone = parts[0]
			parttwo = parts[1]
			# ά --> α, etc.
			tail = stripaccents(partone[-1])
			head = stripaccents(parttwo[0])
			guessone = partone[:-1] + tail + parttwo[1:]
			guesstwo = partone[:-1] + head + parttwo[1:]
			if guessone != guesstwo:
				searched = entry + ' (both '+guessone+' and '+guesstwo+' were searched)'
			else:
				searched = entry + ' ('+guessone+' was searched)'
		else:
			searched = entry
		cleanedentry += '<br />\n<p class="dictionaryheading">nothing found under '+searched+'</p>\n'
		cleanedentry += 'But the parser can get fooled by enclitics (which will alter the accent), spelling variations, and disagreement about the number of entries for a word.<br />'
		cleanedentry += '<br />Try looking for this word yourself by using the proper search box: something is likely to turn up. Remember that partial word searching is acceptable and that accents do not matter.'

	clickableentry = insertbrowserlookups(cleanedentry)
	clickableentry = insertbrowserjs(clickableentry)
	
	return clickableentry


def searchdictionary(cursor, dictionary, usecolumn, seeking, syntax, trialnumber=0):
	"""

	this will make several stabs at finding a word in the dictionary

	we need to do this because sometimes a find in the morphology dictionary does not point to something
	you can find in the dictionary of meanings

	sample values:
		dictionary:	'greek_dictionary'
		usecolumn: 'entry_name'
		seeking: 'προχοΐδιον'
		syntax: '=' or 'LIKE'

	:param cursor:
	:param dictionary:
	:param usecolumn:
	:param seeking:
	:return:
	"""

	trialnumber += 1
	accenteddiaresis = re.compile(r'αί|εί|οί|υί|ηί|ωί')
	unaccenteddiaresis = re.compile(r'αι|ει|οι|υι|ηι|ωι')

	nothingfound = {'metrics': '', 'definition': '', 'type': ''}

	query = 'SELECT metrical_entry, entry_body, entry_type FROM ' + dictionary + ' WHERE '+usecolumn+' '+syntax+' %s'
	data = (seeking,)
	cursor.execute(query, data)
	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	found = cursor.fetchone()

	# we might be at trial 2+ and so we need to strip the supplement we used at trial #1
	seeking = re.sub(r'\s%$','',seeking)

	founddict = nothingfound

	if found is not None:
		# success!
		founddict['metrics'] = found[0]
		founddict['definition'] = found[1]
		founddict['type'] = found[2]
	elif trialnumber == 1:
		# failure...
		# the word is probably there, we have just been given the wrong search term; try some other solutions
		# [1] first guess: there were multiple possible entries, not just one; change your syntax
		# this lets you find 'WORD (1)' and 'WORD (2)' if you failed to find WORD
		founddict = searchdictionary(cursor, dictionary, usecolumn, seeking+ ' %', 'LIKE', trialnumber)
	elif trialnumber < 4 and '-' in seeking:
		# [2] next guess: sometimes you get sent things like κατά-ἀράζω & κατά-ἐρέω
		# these will fail; hence the retry structure
		parts = seeking.split('-')
		partone = parts[0]
		parttwo = parts[1]
		# ά --> α, etc.
		tail = stripaccents(partone[-1])
		head = stripaccents(parttwo[0])
		guessone = partone[:-1] + tail + parttwo[1:]
		guesstwo = partone[:-1] + head + parttwo[1:]
		founddict = searchdictionary(cursor, dictionary, usecolumn, guessone, '=',trialnumber)
		if founddict == nothingfound:
			founddict = searchdictionary(cursor, dictionary, usecolumn, guesstwo, '=',trialnumber)
	elif trialnumber < 4 and re.search(accenteddiaresis,seeking) is not None:
		# false positives very easy here, but we are getting desperate and have nothing to lose
		diaresis = re.search(accenteddiaresis, seeking)
		head = seeking[:diaresis.start()]
		tail = seeking[diaresis.end():]
		vowels = diaresis.group(0)
		vowels = vowels[0] + 'ΐ'
		newword = head + vowels + tail
		founddict = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber < 4 and re.search(unaccenteddiaresis,seeking) is not None:
		diaresis = re.search(unaccenteddiaresis, seeking)
		head = seeking[:diaresis.start()]
		tail = seeking[diaresis.end():]
		vowels = diaresis.group(0)
		vowels = vowels[0] + 'ϊ'
		newword = head + vowels + tail
		founddict = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)

	return founddict


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


def findtotalcounts(word, cursor):
	"""

	use the dictionary_headword_wordcounts table

	[a] take a dictionary entry: ἄκρατοϲ
	[b] look it up

	:param word:
	:param cursor:
	:return:
	"""

	word = re.sub(r'v','u',word)

	table = 'dictionary_headword_wordcounts'
	q = 'SELECT entry_name , total_count, gr_count, lt_count, dp_count, in_count, ch_count, ' \
	    'frequency_classification, early_occurrences, middle_occurrences ,late_occurrences FROM ' + table + ' WHERE entry_name=%s'
	d = (word,)
	cursor.execute(q,d)
	l = cursor.fetchone()

	try:
		hwcountobject = dbHeadwordObject(l[0], l[1], l[2], l[3], l[4], l[5], l[6], l[7], l[8], l[9], l[10])
	except:
		hwcountobject = None


	return hwcountobject


def findcountsviawordcountstable(wordtocheck):
	"""

	used to look up a list of specific observed forms
	(vs. dictionary headwords)

	:param checklist:
	:param finds:
	:return:
	"""
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	initial = stripaccents(wordtocheck[0])
	# alternatives = re.sub(r'[uv]','[uv]',c)
	# alternatives = '^'+alternatives+'$'
	if initial in 'abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ':
		# note that we just lost "'φερον", "'φερεν", "'φέρεν", "'φερεϲ", "'φερε",...
		# but the punctuation killer probably zapped them long ago
		# this needs to be addressed in HipparchiaBuilder
		q = 'SELECT * FROM wordcounts_'+initial+' WHERE entry_name = %s'
	else:
		q = 'SELECT * FROM wordcounts_0 WHERE entry_name = %s'

	d = (wordtocheck,)
	curs.execute(q, d)
	result = curs.fetchone()

	dbconnection.commit()

	return result


def getobservedwordprevalencedata(dictionaryword):
	"""

	:return:
	"""
	l = findcountsviawordcountstable(dictionaryword)

	try:
		thiswordoccurs = dbWordCountObject(l[0], l[1], l[2], l[3], l[4], l[5], l[6])
	except:
		return None

	if thiswordoccurs:
		# thiswordoccurs: <server.hipparchiaclasses.dbWordCountObject object at 0x10ad63b00>
		prevalence = 'Prevalence (this form): '
		prevalence += formatprevalencedata(thiswordoccurs)
		thehtml = '<p class="wordcounts">' + prevalence + '</p>'

		return {'value': thehtml}
	else:
		return None

def formatprevalencedata(wordcountobject):
	"""

	html for the results

	:param wordcountobject:
	:return:
	"""

	w = wordcountobject
	thehtml = ''

	max = 0
	for key in ['gr', 'lt', 'in', 'dp', 'ch']:
		if w.getelement(key) > max:
			max = w.getelement(key)
		if w.getelement(key) > 0:
			thehtml += '<span class="emph">' + w.getlabel(key) + '</span>' + ' {:,}'.format(w.getelement(key)) + ' / '
	key = 'total'
	if w.getelement(key) != max:
		thehtml += '<span class="emph">'+w.getlabel(key)+'</span>' + ' {:,}'.format(w.getelement(key))
	else:
		# there was just one hit; so you should drop the ' / '
		thehtml = thehtml[:-3]

	if type(w) == dbHeadwordObject:

		wts = [(w.getweightedtime(key), w.gettimelabel(key)) for key in ['early', 'middle', 'late']]
		wts = sorted(wts, reverse=True)

		if wts[0][0]:
			# None was returned if there is no time data for this (Latin) word
			thehtml += '\n<p class="wordcounts">Weighted chronological distribution: '
			for wt in wts:
				thehtml += '<span class="emph">' + wt[1] + '</span>' + ' {0:.0f}'.format(wt[0]) + ' / '
			thehtml = thehtml[:-3]
			thehtml += '</p>\n'

		thehtml += '\n<p class="wordcounts">Weighted distribution by corpus: '
		wts = [(w.getweightedcorpora(key), w.getlabel(key)) for key in ['gr', 'lt', 'in', 'dp', 'ch']]
		wts = sorted(wts, reverse=True)
		for wt in wts:
			thehtml += '<span class="emph">' + wt[1] + '</span>' + ' {0:.0f}'.format(wt[0]) + ' / '
		thehtml = thehtml[:-3]
		thehtml += '</p>\n'
		key = 'frq'
		if w.gettimelabel(key) is not None and w.gettimelabel(key) != 'core vocabulary (more than 50)':
			thehtml += '<p class="wordcounts">Relative frequency: <span class="italic">' + w.gettimelabel(key) + '</span></p>\n'

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

