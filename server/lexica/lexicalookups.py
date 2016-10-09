import re

from flask import session

from server.lexica.lexicaformatting import entrysummary, formatdictionarysummary, grabheadmaterial, grabsenses, \
	formatgloss, formatmicroentry, insertbrowserlookups, insertbrowserjs
from server.formatting_helper_functions import polytonicsort


def browserdictionarylookup(entry, dict, cursor):
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
		try:
			cleanedentry += '<br />\n<p class="dictionaryheading">'+entry
			if u'\u0304' in metrics or u'\u0306' in metrics:
				cleanedentry += '&nbsp;<span class="metrics">['+metrics+']</span>'
			cleanedentry += '</p>\n'
			a,s,q = entrysummary(definition, dict, translationlabel)
			
			if len(a) == 0 and len(s) == 0 and len(q) == 0:
				# this is basically just a gloss entry
				cleanedentry += formatmicroentry(definition)
			else:
				cleanedentry += formatdictionarysummary(a, s, q)
				cleanedentry += grabheadmaterial(definition) + '<br />\n'
				senses = grabsenses(definition)
				if len(senses) > 0:
					for n in senses:
						cleanedentry += n
				else:
					cleanedentry += formatmicroentry(definition)
		except:
			print('dictionary entry trouble with',entry)
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

