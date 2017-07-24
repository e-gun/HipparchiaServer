# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server import hipparchia
from server.dbsupport.dbfunctions import setconnection
from server.formatting.lexicaformatting import entrysummary, formatdictionarysummary, grabheadmaterial, grabsenses, \
	formatgloss, formatmicroentry, insertbrowserlookups, insertbrowserjs, formateconsolidatedgrammarentry
from server.formatting.wordformatting import cleanaccentsandvj, universalregexequivalent
from server.hipparchiaobjects.lexicalobjects import dbWordCountObject, dbHeadwordObject, dbMorphologyObject, \
	dbGreekWord, dbLatinWord, dbLemmaObject
from server.listsandsession.listmanagement import polytonicsort


def lookformorphologymatches(word, cursor, trialnumber=0):
	"""
	
	:param word: 
	:param cursor: 
	:param trialnumber: 
	:return: 
	"""

	if re.search(r'[a-z]', word):
		usedictionary = 'latin'
	else:
		usedictionary = 'greek'

	if not session['available'][usedictionary+'_morphology']:
		return None

	trialnumber += 1

	# the things that can confuse me
	terminalacute = re.compile(r'[άέίόύήώ]')

	matchingobject = None

	#	syntax = '~' if you have to deal with '[uv]' problems, e.g.
	syntax = '='

	query = 'SELECT * FROM {d}_morphology WHERE observed_form {sy} %s'.format(d=usedictionary, sy=syntax)
	data = (word,)

	cursor.execute(query, data)
	# fetchone() because all possiblities are stored inside the analysis itself
	analysis = cursor.fetchone()

	if analysis:
		matchingobject = dbMorphologyObject(analysis[0], analysis[1], analysis[2], analysis[3])
	else:
		# this code lets you make multiple stabs at an answer if you have already failed once
		# [a] something like πλακουντάριόν τι will fail because of the enclitic (greek_morphology can find πλακουντάριον and πλακουντάριοϲ)
		# [b] something like προχοίδιόν τι will fail twice over because of the enclitic and the diaresis
		# item [b] cannot be fully addressed here; this correction gives you an analysis, but the term can't yet be found in the dictionary
		# greek_morphology has προχοίδιον; the greek_dictionary has προχοΐδιον
		try:
			# have to 'try' because there might not be a word[-2]
			if re.search(terminalacute,word[-1]) and trialnumber < 4:
				sub = cleanaccentsandvj(word[-1])
				newword = word[:-1]+sub
				matchingobject = lookformorphologymatches(newword, cursor, trialnumber)
			elif re.search(terminalacute,word[-2]) and trialnumber < 4:
				sub = cleanaccentsandvj(word[-2])
				newword = word[:-2] + sub + word[-1]
				matchingobject = lookformorphologymatches(newword, cursor, trialnumber)
			elif trialnumber < 4:
				# elided ending? you will ask for ἀλλ, but you need to look for ἀλλ'
				newword = word + chr(39)
				matchingobject = lookformorphologymatches(newword, cursor, trialnumber)
		except:
			matchingobject = None

	return matchingobject


def lexicalmatchesintohtml(observedform, morphologyobject, cursor):
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
	:param matcheslist:
	:param cursor:
	:return:
	"""

	returnarray = []
	entriestocheck = {}
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

		consolidatedentry = {'count': count, 'form': observedform, 'word': p.entry, 'transl': p.gettranslation(),
							 'anal': p.getanalysislist()}
		returnarray.append({'value': formateconsolidatedgrammarentry(consolidatedentry)})

	# the next will trim the items to check by inducing key collisions
	# p.getbaseform(), p.entry, p.xref: judicium jūdiciūm, judicium 42397893
	# p.getbaseform(), p.entry, p.xref: judicium jūdicium, judicium 42397893
	distinct = {}
	for p in possibilities:
		distinct[p.xref] = p.getbaseform()

	count = 0
	for d in distinct:
		count += 1
		entriestocheck[count] = distinct[d]

	# look up and format the dictionary entries
	if len(entriestocheck) == 1:
		# sending 0 as the count to browserdictionarylookup() prevents enumeration
		entryashtml = browserdictionarylookup(0, entriestocheck[1], cursor)
		returnarray.append({'value': entryashtml})
	else:
		count = 0
		for entry in entriestocheck:
			count += 1
			entryashtml = browserdictionarylookup(count, entriestocheck[entry], cursor)
			returnarray.append({'value': entryashtml})

	return returnarray


def browserdictionarylookup(count, seekingentry, cursor):
	"""
	look up a word and return an htlm version of its dictionary entry

	count:
		1
	seekingentry:
		judicium
	entryxref:
		42397893

	:param entry:
	:param dict:
	:param cursor:
	:return:
	"""

	if re.search(r'[a-z]', seekingentry):
		usedictionary = 'latin'
		translationlabel = 'hi'
	else:
		usedictionary = 'greek'
		translationlabel = 'tr'

	# nothingfound = convertdictionaryfindintoobject('nothing', 'nodict')

	# print('browserdictionarylookup(): entry',entry)

	# entry = re.sub(r'#','',entry)
	#
	# if re.search(r'\d$',entry):
	# 	entry = re.sub(r'(.*?)(\d)',r'\1 (\2)',entry)

	wordobjects = searchdictionary(cursor, usedictionary+'_dictionary', 'entry_name', seekingentry, syntax='=')
	outputlist = []
	clickableentry = ''

	if wordobjects != None:
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
			subcount +=1
			# can't have xml in our html
			definition = re.sub(r'<title>(.*?)</title>', r'<worktitle>\1</worktitle>', w.body)

			if type != 'gloss':
				if count == 0:
					outputlist.append('<hr /><p class="dictionaryheading">{ent}'.format(ent=w.entry))
				else:
					if includesubcounts:
						countval = str(count) + chr(subcount+96)
					else:
						countval = str(count)
					outputlist.append('<hr /><p class="dictionaryheading">({cv})&nbsp;{ent}'.format(cv=countval, ent=w.entry))
				if u'\u0304' in w.metricalentry or u'\u0306' in w.metricalentry:
					outputlist.append('&nbsp;<span class="metrics">[{me}]</span>'.format(me=w.metricalentry))
				outputlist.append('</p>')

				if hipparchia.config['SHOWGLOBALWORDCOUNTS'] == 'yes':
					countobject = findtotalcounts(seekingentry, cursor)
					if countobject:
						outputlist.append('<p class="wordcounts">Prevalence (all forms): ')
						outputlist.append(formatprevalencedata(countobject))
						outputlist.append('</p>')

				summarydict = {}
				if session['sensesummary'] == 'yes' or session['authorssummary'] == 'yes' or session['quotesummary'] == 'yes':
					lemmaobject = grablemmataobjectfor(w.entry, usedictionary+'_lemmata', cursor)
					summarydict = entrysummary(definition, usedictionary, translationlabel, lemmaobject)

				if session['sensesummary'] == 'no':
					summarydict['senses'] = ''

				if session['authorssummary'] == 'no':
					summarydict['authors'] = ''

				if session['quotesummary'] == 'no':
					summarydict['quotes'] = ''

				if len(summarydict['authors']) == 0 and len(summarydict['senses']) == 0 and len(summarydict['quotes']) == 0:
					# either you have turned off summary info or this is basically just a gloss entry
					outputlist.append(formatmicroentry(definition))
				else:
					outputlist.append(formatdictionarysummary(summarydict))
					outputlist.append(grabheadmaterial(definition) + '<br />')
					senses = grabsenses(definition)
					if len(senses) > 0:
						for n in senses:
							outputlist.append(n)
					else:
						outputlist.append(formatmicroentry(definition))
			else:
				outputlist.append('<br />\n<p class="dictionaryheading">{ent}<span class="metrics">[gloss]</span></p>'.format(ent=w.entry))
				outputlist.append(formatgloss(definition))

			# add in next / previous links
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

			outputlist.append(navtemplate.format(p=w.preventry, n=w.nextentry))

			cleanedentry = '\n'.join(outputlist)
			clickableentry = insertbrowserlookups(cleanedentry)
			clickableentry = insertbrowserjs(clickableentry)

	else:
		if count == 0:
			cleanedentry = '<br />\n<p class="dictionaryheading">nothing found under <span class="prevalence">{skg}</span></p>\n'.format(skg=seekingentry)
		else:
			cleanedentry = '<br />\n<p class="dictionaryheading">({ct}) nothing found under <span class="prevalence">{skg}</span></p>\n'.format(ct=count, skg=seekingentry)
		clickableentry = cleanedentry

	entry = clickableentry + dictionaryentryjs()

	return entry


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

	still unimplemented:
		τήθη vs τηθή; the parser has the latter, the dictionary expects the former (but knows of the latter)


	:param cursor:
	:param dictionary:
	:param usecolumn:
	:param seeking:
	:return:
	"""
	# print('seeking/trial',seeking,trialnumber)

	maxtrials = 8
	trialnumber += 1
	accenteddiaresis = re.compile(r'αί|εί|οί|υί|ηί|ωί')
	unaccenteddiaresis = re.compile(r'αι|ει|οι|υι|ηι|ωι')

	# nothingfound = convertdictionaryfindintoobject('nothing', 'nodict')

	if dictionary == 'latin_dictionary':
		extracolumn = 'entry_key'
	else:
		extracolumn = 'unaccented_entry'

	qtemplate = """SELECT entry_name, metrical_entry, id_number, entry_type, entry_options, 
					translations, entry_body, {ec}
					FROM {d} WHERE {col} {sy} %s ORDER BY id_number ASC"""
	query = qtemplate.format(ec=extracolumn, d=dictionary, col=usecolumn, sy=syntax)
	data = (seeking,)
	cursor.execute(query, data)
	# print('searchdictionary()',query,'\n\t',data)

	found = cursor.fetchall()

	# we might be at trial 2+ and so we need to strip the supplement we used at trial #1
	if trialnumber > 2:
		seeking = re.sub(r'\[¹²³⁴⁵⁶⁷⁸⁹\]','',seeking)
		seeking = re.sub(r'\^', '', seeking)

	foundobjects = None

	if len(found) > 0:
		foundobjects = [convertdictionaryfindintoobject(f, dictionary, cursor) for f in found]
	elif trialnumber == 1:
		# failure...
		# the word is probably there, we have just been given the wrong search term; try some other solutions
		# [1] first guess: there were multiple possible entries, not just one
		newword = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]','',seeking.lower())
		foundobjects = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber == 2:
		# grab any/all variants: ⁰¹²³⁴⁵⁶⁷⁸⁹
		newword = '^{sk}[¹²³⁴⁵⁶⁷⁸⁹]'.format(sk=seeking)
		foundobjects = searchdictionary(cursor, dictionary, usecolumn, newword, '~', trialnumber)
	# elif trialnumber < maxtrials and '-' in seeking:
	# 	newword = attemptelision(seeking)
	# 	foundobject = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber < maxtrials and seeking[-1] == 'ω':
		# ὑποϲυναλείφομαι is in the dictionary, but greek_lemmata says to look for ὑπό-ϲυναλείφω
		newword = seeking[:-1]+'ομαι'
		foundobjects = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber < maxtrials and re.search(r'ομαι$',seeking):
		# χαρίζω is in the dictionary, but greek_lemmata says to look for χαρίζομαι
		newword = seeking[:-4]+'ω'
		foundobjects = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber < maxtrials and re.search(accenteddiaresis,seeking):
		# false positives very easy here, but we are getting desperate and have nothing to lose
		diaresis = re.search(accenteddiaresis, seeking)
		head = seeking[:diaresis.start()]
		tail = seeking[diaresis.end():]
		vowels = diaresis.group(0)
		vowels = vowels[0] + 'ΐ'
		newword = head + vowels + tail
		foundobjects = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber < maxtrials and re.search(unaccenteddiaresis,seeking):
		diaresis = re.search(unaccenteddiaresis, seeking)
		head = seeking[:diaresis.start()]
		tail = seeking[diaresis.end():]
		vowels = diaresis.group(0)
		vowels = vowels[0] + 'ϊ'
		newword = head + vowels + tail
		foundobjects = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber < maxtrials:
		# τήθη vs τηθή; the parser has the latter, the dictionary expects the former (but knows of the latter)
		trialnumber = maxtrials - 1
		newword = re.sub(r'\[¹²³⁴⁵⁶⁷⁸⁹\]', '', seeking)
		newword = cleanaccentsandvj(newword)
		newword = universalregexequivalent(newword)
		# strip '(' and ')'
		newword = '^{wd}$'.format(wd=newword[1:-1])
		foundobjects = searchdictionary(cursor, dictionary, usecolumn, newword, '~', trialnumber)

	return foundobjects


def convertdictionaryfindintoobject(foundline, dictionary, cursor):
	"""

	dictionary = greek_dictionary or latin_dictionary

	foundline is a db line with the extra parameter last:
		entry_name, metrical_entry, id_number, entry_type, entry_options, , translations, entry_body + extra

	example:
		foundline ('ἑτερόφθαλμοϲ', 'ἑτερόφθαλμοϲ', '43226', 'main', 'n', '[transl]', '<orth extent="suff" lang="greek" opt="n">ἑτερόφθαλμ-οϲ</orth>, <itype lang="greek" opt="n">ον</itype>, <sense id="n43226.0" n="A" level="1" opt="n"><tr opt="n">one-eyed</tr>, <bibl n="Perseus:abo:tlg,0014,024:141" default="NO" valid="yes"><author>D.</author> <biblScope>24.141</biblScope></bibl>, <bibl n="Perseus:abo:tlg,0086,025:1023a:5" default="NO" valid="yes"><author>Arist.</author><title>Metaph.</title><biblScope>1023a5</biblScope></bibl>; <foreign lang="greek">ἑ. γενομένη ἡ Ἑλλάϲ</foreign>, metaph., of the proposed destruction of Athens, Leptines ap. <bibl n="Perseus:abo:tlg,0086,038:1411a:5" default="NO" valid="yes"><author>Arist.</author><title>Rh.</title><biblScope>1411a5</biblScope></bibl>, cf. <bibl default="NO"><author>Demad.</author><biblScope>65</biblScope></bibl> <bibl default="NO"><author>B.</author></bibl>, <bibl default="NO"><author>Plu.</author><biblScope>2.803a</biblScope></bibl>. </sense><sense n="II" id="n43226.1" level="2" opt="n"> <tr opt="n">with different-coloured eyes,</tr> <bibl n="Perseus:abo:tlg,4080,001:16:2:1" default="NO"><author>Gp.</author> <biblScope>16.2.1</biblScope></bibl>.</sense>', 'ετεροφθαλμοϲ')

	:param foundline:
	:param dictionary:
	:return:
	"""
	# print('foundline',foundline)

	if dictionary == 'greek_dictionary':
		wordobject = dbGreekWord(foundline[0], foundline[1], foundline[2], foundline[3], foundline[4], foundline[5], foundline[6], foundline[7])
	elif dictionary == 'latin_dictionary':
		wordobject = dbLatinWord(foundline[0], foundline[1], foundline[2], foundline[3], foundline[4], foundline[5], foundline[6], foundline[7])
	else:
		# you actually want a hollow object
		wordobject = dbGreekWord(None, None, None, None, None, None, None, None)

	ntemplate = 'SELECT entry_name, id_number FROM {d} WHERE id_number > %s ORDER BY id_number ASC LIMIT 1;'

	q = ntemplate.format(d=dictionary)
	d = (wordobject.id,)
	cursor.execute(q, d)
	e = cursor.fetchone()

	try:
		wordobject.nextentry = e[0]
		wordobject.nextentryid = e[1]
	except:
		pass

	ptemplate = 'SELECT entry_name, id_number FROM {d} WHERE id_number < %s ORDER BY id_number DESC LIMIT 1;'

	q = ptemplate.format(d=dictionary)
	d = (wordobject.id,)
	cursor.execute(q, d)
	e = cursor.fetchone()

	try:
		wordobject.preventry = e[0]
		wordobject.preventryid = e[1]
	except:
		pass

	return wordobject


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

	qtemplate = 'SELECT * FROM {d} WHERE {d} ~* %s'
	query = qtemplate.format(d=dictionary, c=usecolumn)
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


def findtotalcounts(word, cursor):
	"""

	use the dictionary_headword_wordcounts table

	[a] take a dictionary entry: ἄκρατοϲ
	[b] look it up

	return a countobject

	:param word:
	:param cursor:
	:return:
	"""

	table = 'dictionary_headword_wordcounts'
	qtemplate = """
		SELECT 
			entry_name , total_count, gr_count, lt_count, dp_count, in_count, ch_count,
			frequency_classification, early_occurrences, middle_occurrences ,late_occurrences, 
			acta, agric, alchem, anthol, apocalyp, apocryph, apol, astrol, astron, biogr, bucol, caten, chronogr, comic, comm, 
			concil, coq, dialog, docu, doxogr, eccl, eleg, encom, epic, epigr, epist, evangel, exeget, fab, geogr, gnom, gramm, 
			hagiogr, hexametr, hist, homilet, hymn, hypoth, iamb, ignotum, invectiv, inscr, jurisprud, lexicogr, liturg, lyr, 
			magica, math, mech, med, metrolog, mim, mus, myth, narrfict, nathist, onir, orac, orat, paradox, parod, paroem, 
			perieg, phil, physiognom, poem, polyhist, prophet, pseudepigr, rhet, satura, satyr, schol, tact, test, theol, trag
		FROM {tbl} WHERE entry_name=%s
	"""

	q = qtemplate.format(tbl=table)
	d = (word,)
	try:
		cursor.execute(q,d)
		l = cursor.fetchone()
	except:
		# psycopg2.ProgrammingError: relation "dictionary_headword_wordcounts" does not exist
		# you have not installed the wordcounts (yet)
		l = None

	try:
		hwcountobject = dbHeadwordObject(l[0], l[1], l[2], l[3], l[4], l[5], l[6], l[7], l[8], l[9], l[10],
		                                 l[11], l[12], l[13], l[14], l[15], l[16], l[17], l[18], l[19], l[20],
		                                 l[21], l[22], l[23], l[24], l[25], l[26], l[27], l[28], l[29], l[30],
		                                 l[31], l[32], l[33], l[34], l[35], l[36], l[37], l[38], l[39], l[40],
		                                 l[41], l[42], l[43], l[44], l[45], l[46], l[47], l[48], l[49], l[50],
		                                 l[51], l[52], l[53], l[54], l[55], l[56], l[57], l[58], l[59], l[60],
		                                 l[61], l[62], l[63], l[64], l[65], l[66], l[67], l[68], l[69], l[70],
		                                 l[71], l[72], l[73], l[74], l[75], l[76], l[77], l[78], l[79], l[80],
		                                 l[81], l[82], l[83], l[84], l[85], l[86], l[87])
	except:
		# print('failed to initialize dbHeadwordObject for',word)
		hwcountobject = None

	return hwcountobject


def findcountsviawordcountstable(wordtocheck):
	"""

	used to look up a list of specific observed forms
	(vs. dictionary headwords)

	:param wordtocheck:
	:return:
	"""
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	initial = cleanaccentsandvj(wordtocheck[0])
	# alternatives = re.sub(r'[uv]','[uv]',c)
	# alternatives = '^'+alternatives+'$'
	if initial in 'abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ':
		# note that we just lost "'φερον", "'φερεν", "'φέρεν", "'φερεϲ", "'φερε",...
		# but the punctuation killer probably zapped them long ago
		# this needs to be addressed in HipparchiaBuilder
		q = 'SELECT * FROM wordcounts_{i} WHERE entry_name = %s'.format(i=initial)
	else:
		q = 'SELECT * FROM wordcounts_0 WHERE entry_name = %s'

	d = (wordtocheck,)
	try:
		curs.execute(q, d)
		result = curs.fetchone()
	except:
		# psycopg2.ProgrammingError: relation "wordcounts_ε" does not exist
		# you did not build the wordcounts at all?
		result = None

	dbconnection.commit()

	return result


def getobservedwordprevalencedata(dictionaryword):
	"""
	
	:param dictionaryword: 
	:return: 
	"""

	if not session['available']['wordcounts_0']:
		return {'value': ''}

	l = findcountsviawordcountstable(dictionaryword)

	try:
		thiswordoccurs = dbWordCountObject(l[0], l[1], l[2], l[3], l[4], l[5], l[6])
	except:
		return None

	if thiswordoccurs:
		# thiswordoccurs: <server.hipparchiaclasses.dbWordCountObject object at 0x10ad63b00>
		prevalence = 'Prevalence (this form): {pd}'.format(pd=formatprevalencedata(thiswordoccurs))
		thehtml = '<p class="wordcounts">{pr}</p>'.format(pr=prevalence)

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
	thehtml = []

	max = 0
	for key in ['gr', 'lt', 'in', 'dp', 'ch']:
		if w.getelement(key) > max:
			max = w.getelement(key)
		if w.getelement(key) > 0:
			thehtml.append('<span class="prevalence">{a}</span> {b:,}'.format(a=w.getlabel(key), b=w.getelement(key)))
	key = 'total'
	if w.getelement(key) != max:
		thehtml.append('<span class="prevalence">{a}</span> {b:,}'.format(a=w.getlabel(key), b=w.getelement(key)))

	thehtml = [' / '.join(thehtml)]

	if type(w) == dbHeadwordObject:
		thehtml.append('\n<p class="wordcounts">Weighted distribution by corpus: ')
		wts = [(w.getweightedcorpora(key), w.getlabel(key)) for key in ['gr', 'lt', 'in', 'dp', 'ch']]
		wts = sorted(wts, reverse=True)
		wts = ['<span class="prevalence">{a}</span> {b:.0f}'.format(a=w[1], b=w[0]) for w in wts]
		thehtml.append(' / '.join(wts))
		thehtml.append('</p>')

		wts = [(w.getweightedtime(key), w.gettimelabel(key)) for key in ['early', 'middle', 'late']]
		wts = sorted(wts, reverse=True)
		if wts[0][0]:
			# None was returned if there is no time data for this (Latin) word
			thehtml.append('<p class="wordcounts">Weighted chronological distribution: ')
			wts = ['<span class="prevalence">{a}</span> {b:.0f}'.format(a=w[1], b=w[0]) for w in wts]
			thehtml.append(' / '.join(wts))
			thehtml.append('</p>')

		if hipparchia.config['COLLAPSEDGENRECOUNTS'] == 'yes':
			genreinfotuples = w.collapsedgenreweights()
		else:
			genreinfotuples = w.sortgenresbyweight()

		if genreinfotuples:
			thehtml.append('<p class="wordcounts">Predominant genres: ')
			genres = []
			for g in range(0,hipparchia.config['NUMBEROFGENRESTOTRACK']):
				git = genreinfotuples[g]
				if git[1] > 0:
					genres.append('<span class="emph">{a}</span>&nbsp;({b:.0f})'.format(a=git[0], b=git[1]))
			thehtml.append(', '.join(genres))

		key = 'frq'
		if w.gettimelabel(key) and re.search(r'core', w.gettimelabel(key)) is None:
			thehtml.append('<p class="wordcounts">Relative frequency: <span class="italic">{lb}</span></p>\n'.format(lb=w.gettimelabel(key)))

	thehtml = '\n'.join(thehtml)

	return thehtml


def grablemmataobjectfor(entryname, db, cursor):
	"""

	:param db:
	:param cursor:
	:return:
	"""

	if not session['available'][db]:
		lo = dbLemmaObject('[parsing is impossible: lemmata data was not installed]', -1, '')
		return lo

	q = 'SELECT * FROM {db} WHERE dictionary_entry=%s'.format(db=db)
	d = (entryname,)
	cursor.execute(q, d)
	l = cursor.fetchone()

	try:
		lemmaobject = dbLemmaObject(l[0], l[1], l[2])
	except TypeError:
		# 'NoneType' object is not subscriptable
		lemmaobject = dbLemmaObject('[entry not found]', -1, '')

	return lemmaobject


def findtermamongsenses(match, seeking, usedict, translationlabel, cur):
	"""
	a reverse lookup match finder
	
	see reverselexiconsearch()
	
	:param match: 
	:param seeking: 
	:param usedict: 
	:param translationlabel: 
	:param cur: 
	:return: 
	"""

	matchingentries = []
	matchingobjectlist = searchdictionary(cur, usedict + '_dictionary', 'entry_name', match, syntax='LIKE')

	for o in matchingobjectlist:
		if o.entry:
			# AttributeError: 'list' object has no attribute 'entry'
			definition = o.body
			lemmaobject = grablemmataobjectfor(o.entry, usedict + '_lemmata', cur)
			summarydict = entrysummary(definition, usedict, translationlabel, lemmaobject)

			for sense in summarydict['senses']:
				if re.search(r'^' + seeking, sense):
					matchingentries.append(match)

	return matchingentries


def dictionaryentryjs():
	"""

	return js to insert

	ensure exact matches, otherwise ἔρδω will pull up ὑπερδώριοϲ too

	and so:
		'/dictsearch/^'+this.id+'$'

	:return:
	"""

	template = """
	<script>
	$('dictionaryentry').click( function(e) {
            e.preventDefault();
            var windowWidth = $(window).width();
            var windowHeight = $(window).height();
            $( '#lexicadialogtext' ).dialog({
                    closeOnEscape: true,
                    autoOpen: false,
                    minWidth: windowWidth*.33,
                    maxHeight: windowHeight*.9,
                    // position: { my: "left top", at: "left top", of: window },
                    title: this.id,
                    draggable: true,
                    icons: { primary: 'ui-icon-close' },
                    click: function() { $( this ).dialog( 'close' ); }
                    });
            $( '#lexicadialogtext' ).dialog( 'open' );
            $( '#lexicadialogtext' ).html('[searching...]');
            $.getJSON('/dictsearch/^'+this.id+'$', function (definitionreturned) {
                $( '#lexicon').val(definitionreturned[0]['trylookingunder']);
                var dLen = definitionreturned.length;
                var linesreturned = []
                for (i = 0; i < dLen; i++) {
                    linesreturned.push(definitionreturned[i]['value']);
                    }
                $( '#lexicadialogtext' ).html(linesreturned);
            });
            return false;
        });
    </script>
	"""

	return template

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
