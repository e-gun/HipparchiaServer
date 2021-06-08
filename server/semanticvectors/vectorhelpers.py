# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import json
import re
import time
from string import punctuation
from typing import List

import psycopg2

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork, worklinetemplate
from server.dbsupport.lexicaldbfunctions import findcountsviawordcountstable, querytotalwordcounts
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import acuteorgrav, basiclemmacleanup, elidedextrapunct, removegravity, tidyupterm
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.searchobjects import SearchObject, SearchOutputObject
from server.hipparchiaobjects.wordcountobjects import dbWordCountObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.searching.sqlsearching import precomposedsqlsearch
from server.searching.miscsearchfunctions import buildbetweenwhereextension
from server.startup import lemmatadict

try:
	import numpy as np
	from sklearn.manifold import TSNE
except ImportError as ie:
	np = None
	TSNE = None
	# print('"vectorgraphing.py" is missing a module: {m}'.format(m=ie))
	# this is a benign failure if you are a non-vector user since all you really wanted was vectorranges, etc.
	# which themselves will not really be used


vectorranges = {
	'ldacomponents': range(1, 51),
	'ldaiterations': range(1, 26),
	'ldamaxfeatures': range(1, 5001),
	'ldamaxfreq': range(1, 101),
	'ldaminfreq': range(1, 21),
	'ldamustbelongerthan': range(1, 5),
	'vcutlem': range(1, 101),
	'vcutloc': range(1, 101),
	'vcutneighb': range(1, 101),
	'vdim': range(25, 501),
	'vdsamp': range(1, 21),
	'viterat': range(1, 21),
	'vminpres': range(1, 21),
	'vnncap': range(1, 26),
	'vsentperdoc': range(1, 6),
	'vwindow': range(2, 21)
}

vectordefaults = {
	'ldacomponents': hipparchia.config['LDACOMPONENTS'],
	'ldaiterations': hipparchia.config['LDAITERATIONS'],
	'ldamaxfeatures': hipparchia.config['LDAMAXFEATURES'],
	'ldamaxfreq': hipparchia.config['LDAMAXFREQ'],
	'ldaminfreq': hipparchia.config['LDAMINFREQ'],
	'ldamustbelongerthan': hipparchia.config['LDAMUSTBELONGERTHAN'],
	'vcutlem': hipparchia.config['VECTORDISTANCECUTOFFLEMMAPAIR'],
	'vcutloc': hipparchia.config['VECTORDISTANCECUTOFFLOCAL'],
	'vcutneighb': hipparchia.config['VECTORDISTANCECUTOFFNEARESTNEIGHBOR'],
	'vdim': hipparchia.config['VECTORDIMENSIONS'],
	'vdsamp': hipparchia.config['VECTORDOWNSAMPLE'],
	'viterat': hipparchia.config['VECTORTRAININGITERATIONS'],
	'vminpres': hipparchia.config['VECTORMINIMALPRESENCE'],
	'vnncap': hipparchia.config['NEARESTNEIGHBORSCAP'],
	'vsentperdoc': hipparchia.config['SENTENCESPERDOCUMENT'],
	'vwindow': hipparchia.config['VECTORWINDOW'],
}


vectorlabels = {
	'ldacomponents': 'LDA: no. of topics',
	'ldaiterations': 'LDA: iterations',
	'ldamaxfeatures': 'LDA: features',
	'ldamaxfreq': 'LDA: max frequency',
	'ldaminfreq': 'LDA: min frequency',
	'ldamustbelongerthan': 'LDA: min length',
	'vcutlem': 'Cutoff: Lemma pairs',
	'vcutloc': 'Cutoff: Literal distance',
	'vcutneighb': 'Cutoff: Nearest Neighbors',
	'vdim': 'Vector Dimensions',
	'vdsamp': 'Vector downsampling',
	'viterat': 'Training iterations',
	'vminpres': 'Minimal term presence',
	'vnncap': 'Nearest Neighbors cap',
	'vsentperdoc': 'Sentences per document',
	'vwindow': 'Proximity window size'
}


def cleanvectortext(texttostrip):
	"""

	if we are using the marked up line, then a lot of gunk needs to go

	:param sentence:
	:return:
	"""

	# PROBLEM #1: names
	# you will get bad 'sentences' in the Latin with things like M. Tullius Cicero.
	# could check for 'sentences' that end with a single letter: '(\s\w)\.' --> '\1'
	# but this will still leave you with 'Ti' and similar items
	#
	# PROBLEM #2: dates
	# the following is not 4 sentences: a. d. VIII Id. Nov.
	#
	# USEFUL FOR THE SOLUTION: marked_up_line is case sensitive
	#
	# Note that the case of the substitute is off; but all we really care about is getting the headword right

	praenomina = {
		'A.': 'Aulus',
		'App.': 'Appius',
		'C.': 'Caius',
		'G.': 'Gaius',
		'Cn.': 'Cnaius',
		'Gn.': 'Gnaius',
		'D.': 'Decimus',
		'L.': 'Lucius',
		'M.': 'Marcus',
		'M.’': 'Manius',
		'N.': 'Numerius',
		'P.': 'Publius',
		'Q.': 'Quintus',
		'S.': 'Spurius',
		'Sp.': 'Spurius',
		'Ser.': 'Servius',
		'Sex.': 'Sextus',
		'T.': 'Titus',
		'Ti.': 'Tiberius',
		'V.': 'Vibius'
	}

	datestrings = {
		'a.': 'ante',
		'd.': 'dies',
		'Id.': 'Idibus',
		'Kal.': 'Kalendas',
		'Non.': 'Nonas',
		'prid.': 'pridie',
		'Ian.': 'Ianuarias',
		'Feb.': 'Februarias',
		'Mart.': 'Martias',
		'Apr.': 'Aprilis',
		'Mai.': 'Maias',
		'Iun.': 'Iunias',
		'Quint.': 'Quintilis',
		'Sext.': 'Sextilis',
		'Sept.': 'Septembris',
		'Oct.': 'Octobris',
		'Nov.': 'Novembris',
		'Dec.': 'Decembris'
	}

	searchdict = {**praenomina, **datestrings}

	htmlstrip = re.compile(r'<.*?>')
	wholetext = re.sub(htmlstrip, str(), texttostrip)
	wholetext = re.sub('&nbsp;', str(), wholetext)
	wholetext = re.sub(r'\w+\.', lambda x: replaceabbreviations(x.group(0), searchdict), wholetext)
	# speakers in plays? need to think about catching:  'XY. (says something) AB. (replies)'

	invals = "vjσς"
	outvals = "uiϲϲ"
	text = wholetext.lower()
	wholetext = text.translate(str.maketrans(invals, outvals))

	return wholetext


def replaceabbreviations(foundstring, searchdict):
	"""

	pass lambda results through this: make sure a sentence end is not really a common abbrevation

	:param foundstring:
	:param searchdict:
	:return:
	"""

	if foundstring in searchdict.keys():
		# reduce ...
		# foundstring = re.sub(r'\.', '', foundstring)
		# or expand...
		foundstring = searchdict[foundstring]

	return foundstring


def recursivesplit(tosplit, listofsplitlerms):
	"""

	split and keep splitting

	:param tosplit:
	:param splitterm:
	:return:
	"""

	while listofsplitlerms:
		cutter = listofsplitlerms.pop()
		split = [t.split(cutter) for t in tosplit]
		flattened = [item for sublist in split for item in sublist]
		tosplit = recursivesplit(flattened, listofsplitlerms)

	return tosplit


def findsentences(authortable: str, so: SearchObject, dbcursor: ConnectionObject.cursor) -> List[tuple]:
	"""

	grab a chunk of a database

	turn it into a collection of sentences

	findsentences() results[0] ('line/gr0014w001/1', 'ἀντὶ πολλῶν ἄν ὦ ἄνδρεϲ ἀθηναῖοι χρημάτων ὑμᾶϲ ἑλέϲθαι νομίζω εἰ φανερὸν γένοιτο τὸ μέλλον ϲυνοίϲειν τῇ πόλει περὶ ὧν νυνὶ ϲκοπεῖτε')

	findsentences() results[0] (0, 'ἐπὶ πολλῶν μὲν ἄν τιϲ ἰδεῖν ὦ ἄνδρεϲ ἀθηναῖοι δοκεῖ μοι τὴν παρὰ τῶν θεῶν εὔνοιαν φανερὰν γιγνομένην τῇ πόλει οὐχ ἥκιϲτα δ’ ἐν τοῖϲ παροῦϲι πράγμαϲι')

	candidate for refactoring: note the overlap with searchlistintosqldict()

	:param authortable:
	:param searchobject:
	:param dbcursor:
	:return:
	"""

	r = so.indexrestrictions[authortable]

	if r['type'] == 'temptable':
		# make the table
		q = r['where']['tempquery']
		avoidcollisions = assignuniquename()
		q = re.sub('_includelist', '_includelist_{a}'.format(a=avoidcollisions), q)
		dbcursor.execute(q)
		# now you can work with it
		wtempate = """
		EXISTS
			(SELECT 1 FROM {tbl}_includelist_{a} incl WHERE incl.includeindex = {tbl}.index
		"""
		whereextensions = wtempate.format(a=avoidcollisions, tbl=authortable)
		whr = 'WHERE {xtn} )'.format(xtn=whereextensions)
	elif r['type'] == 'between':
		whereextensions = buildbetweenwhereextension(authortable, so)
		# contains a trailing ' AND'
		whereextensions = whereextensions[:-4]
		whr = 'WHERE {xtn} '.format(xtn=whereextensions)
	elif r['type'] == 'unrestricted':
		whr = str()
	else:
		# should never see this
		consolewarning('error in substringsearch(): unknown whereclause type: {w}'.format(w=r['type']), color='red')
		whr = str()

	# vanilla grab-it-all
	query = 'SELECT {wtmpl} FROM {db} {whr}'.format(wtmpl=worklinetemplate, db=authortable, whr=whr)

	# vs. something that skips titles (but might drop the odd other thing or two...)
	# but this noes not play nicely with 'temptable'
	# if re.search('WHERE', whr):
	# 	whr = whr + ' AND'
	# else:
	# 	whr = 'WHERE'
	# query = 'SELECT {c} FROM {db} {whr} level_00_value != %s'.format(c=so.usecolumn, db=authortable, whr=whr)
	data = ('t',)
	dbcursor.execute(query, data)
	results = resultiterator(dbcursor)
	results = [dblineintolineobject(line) for line in results]

	# kill off titles and salutations: dangerous if there is a body l1 value of 't' out there
	results = [r for r in results if r.l1 not in ['t', 'sa']]

	results = parsevectorsentences(so, results)
	# print('findsentences() results[0]', results[0])

	return results


def parsevectorsentences(so: SearchObject, lineobjects: List[dbWorkLine]) -> List[tuple]:
	"""

	take raw lines, join them together, clean them and then return tuples of lines and ids

	the ids may or may not be needed later

	sentencetuples:
		[('lt0588w001_ln_8', 'sed ii erunt fere qui expertes litterarum graecarum nihil rectum nisi quod ipsorum moribus conueniat putabunt'),
		('lt0588w001_ln_10', 'hi si didicerint non eadem omnibus esse honesta atque turpia sed omnia maiorum institutis iudicari non admirabuntur nos in graiorum uirtutibus exponendis mores eorum secutos'),
		('lt0588w001_ln_13', 'neque enim cimoni fuit turpe atheniensium summo uiro sororem germanam habere in matrimonio quippe cum ciues eius eodem uterentur instituto'),
		(id, text), ...]

	FIXME: [see notes about progress so far...]

	findsentences() results[0] ('line/gr0014w002/233', 'μαϲτότεροϲ παρὰ πᾶϲι νομίζεται')

	this is the WRONG first sentence; but the subsequent sentences seem to be fine...

	this is super-hard to debug: if you use slices of D. Ol 2 you will get the right answer...

	wholetext
	⊏line/gr0014w002/233⊐μαϲτότεροϲ παρὰ πᾶϲι νομίζεται· ὑμεῖϲ δ’ ὅϲῳ χεῖρον ἢ ⊏line/gr0014w002/213⊐Ἐπὶ πολλῶν μὲν ἄν τιϲ ἰδεῖν, ὦ ἄνδρεϲ Ἀθηναῖοι, δοκεῖ ⊏line/gr0014w002/214⊐μοι τὴν παρὰ τῶν θεῶν εὔνοιαν φανερὰν γιγνομένην τῇ πόλει, ⊏line/gr0014w002/215⊐οὐχ ἥκιϲτα δ’ ἐν τοῖϲ παροῦϲι πράγμαϲι· τὸ γὰρ τοὺϲ πολεμή- ⊏line/gr0014w002/216⊐ϲονταϲ Φιλίππῳ γεγενῆϲθαι καὶ χώραν ὅμορον καὶ δύναμίν ⊏line/gr0014w002/217⊐τινα κεκτημένουϲ, καὶ τὸ μέγιϲτον ἁπάντων, τὴν ὑπὲρ τοῦ ⊏line/gr0014w002/218⊐πολέμου γνώμην τοιαύτην ἔχονταϲ ὥϲτε τὰϲ πρὸϲ ἐκεῖνον ⊏line/gr0014w002/219⊐διαλλαγὰϲ πρῶτον μὲν ἀπίϲτουϲ, εἶτα τῆϲ ἑαυτῶν πατρίδοϲ ⊏line/gr0014w002/220⊐νομίζειν ἀνάϲταϲιν, δαιμονίᾳ τινὶ καὶ θείᾳ παντάπαϲιν ἔοικεν ⊏line/gr0014w002/221⊐εὐεργεϲίᾳ. δεῖ τοίνυν, ὦ ἄνδρεϲ Ἀθηναῖοι, τοῦτ’ ἤδη ϲκοπεῖν ⊏line/gr0014w002/222⊐αὐτούϲ, ὅπωϲ μὴ χείρουϲ περὶ ἡμᾶϲ αὐτοὺϲ εἶναι δόξομεν τῶν ⊏line/gr0014w002/223⊐ὑπαρχόντων, ὡϲ ἔϲτι τῶν αἰϲχρῶν, μᾶλλον δὲ τῶν αἰϲχίϲτων, ⊏line/gr0014w002/224⊐μὴ μόνον πόλεων καὶ τόπων ὧν ἦμέν ποτε κύριοι φαίνεϲθαι ⊏line/gr0014w002/225⊐προϊεμένουϲ, ἀλλὰ καὶ τῶν ὑπὸ τῆϲ τύχηϲ παραϲκευαϲθέντων ⊏line/gr0014w002/226⊐ϲυμμάχων καὶ καιρῶν.  ⊏line/gr0014w002/227⊐Τὸ μὲν οὖν, ὦ ἄνδρεϲ Ἀθηναῖοι, τὴν Φιλίππου ῥώμην ⊏line/gr0014w002/228⊐διεξιέναι καὶ διὰ τούτων τῶν λόγων προτρέπειν τὰ δέοντα ⊏line/gr0014w002/229⊐ποιεῖν ὑμᾶϲ, οὐχὶ καλῶϲ ἔχειν ἡγοῦμαι. διὰ τί; ὅτι μοι ⊏line/gr0014w002/230⊐δοκεῖ πάνθ’ ὅϲ’ ἂν εἴποι τιϲ ὑπὲρ τούτων, ἐκείνῳ μὲν ἔχειν ⊏line/gr0014w002/231⊐φιλοτιμίαν, ἡμῖν δ’ οὐχὶ καλῶϲ πεπρᾶχθαι. ὁ μὲν γὰρ ὅϲῳ ⊏line/gr0014w002/232⊐πλείον’ ὑπὲρ τὴν ἀξίαν πεποίηκε τὴν αὑτοῦ, τοϲούτῳ θαυ- ⊏line/gr0014w002/234⊐προϲῆκε κέχρηϲθε τοῖϲ πράγμαϲι, τοϲούτῳ πλείον’ αἰϲχύνην ⊏line/gr0014w002/235⊐ὠφλήκατε. ταῦτα μὲν οὖν παραλείψω. καὶ γὰρ εἰ μετ’ ⊏line/gr0014w002/236⊐ἀληθείαϲ τιϲ, ὦ ἄνδρεϲ Ἀθηναῖοι, ϲκοποῖτο, ἐνθένδ’ ἂν αὐτὸν ⊏line/gr0014w002/237⊐ἴδοι μέγαν γεγενημένον, οὐχὶ παρ’ αὑτοῦ. ὧν οὖν ἐκεῖνοϲ ⊏line/gr0014w002/238⊐μὲν ὀφείλει τοῖϲ ὑπὲρ αὐτοῦ πεπολιτευμένοιϲ χάριν, ὑμῖν ⊏line/gr0014w002/239⊐δὲ δίκην προϲήκει λαβεῖν, τούτων οὐχὶ νῦν ὁρῶ τὸν καιρὸν ⊏line/gr0014w002/240⊐τοῦ λέγειν· ἃ δὲ καὶ χωρὶϲ τούτων ἔνι, καὶ βέλτιόν ἐϲτιν ⊏line/gr0014w002/241⊐ἀκηκοέναι πάνταϲ ὑμᾶϲ, καὶ μεγάλ’, ὦ ἄνδρεϲ Ἀθηναῖοι, κατ’ ⊏line/gr0014w002/242⊐ἐκείνου φαίνοιτ’ ἂν ὀνείδη βουλομένοιϲ ὀρθῶϲ δοκιμάζειν, ⊏line/gr0014w002/243⊐ταῦτ’ εἰπεῖν πειράϲομαι. ⊏line/gr0014w002/244⊐Τὸ μὲν οὖν ἐπίορκον κἄπιϲτον καλεῖν ἄνευ τοῦ τὰ πε- ⊏line/gr0014w002/245⊐πραγμένα δεικνύναι λοιδορίαν εἶναί τιϲ ἂν φήϲειε κενὴν ⊏line/gr0014w002/246⊐δικαίωϲ· τὸ δὲ πάνθ’ ὅϲα πώποτ’ ἔπραξε διεξιόντα ἐφ’ ἅπαϲι ⊏line/gr0014w002/247⊐τούτοιϲ ἐλέγχειν, καὶ βραχέοϲ λόγου ϲυμβαίνει δεῖϲθαι, καὶ ⊏line/gr0014w002/248⊐δυοῖν ἕνεχ’ ἡγοῦμαι ϲυμφέρειν εἰρῆϲθαι, τοῦ τ’ ἐκεῖνον, ὅπερ ...

	results
	[('line/gr0014w002/233', 'μαϲτότεροϲ παρὰ πᾶϲι νομίζεται'), ('line/gr0014w002/213', 'ὑμεῖϲ δ’ ὅϲῳ χεῖρον ἢ ἐπὶ πολλῶν μὲν ἄν τιϲ ἰδεῖν ὦ ἄνδρεϲ ἀθηναῖοι δοκεῖ μοι τὴν παρὰ τῶν θεῶν εὔνοιαν φανερὰν γιγνομένην τῇ πόλει οὐχ ἥκιϲτα δ’ ἐν τοῖϲ παροῦϲι πράγμαϲι'), ('line/gr0014w002/216', 'τὸ γὰρ τοὺϲ πολεμήϲονταϲ φιλίππῳ γεγενῆϲθαι καὶ χώραν ὅμορον καὶ δύναμίν τινα κεκτημένουϲ καὶ τὸ μέγιϲτον ἁπάντων τὴν ὑπὲρ τοῦ πολέμου γνώμην τοιαύτην ἔχονταϲ ὥϲτε τὰϲ πρὸϲ ἐκεῖνον διαλλαγὰϲ πρῶτον μὲν ἀπίϲτουϲ εἶτα τῆϲ ἑαυτῶν πατρίδοϲ νομίζειν ἀνάϲταϲιν δαιμονίᾳ τινὶ καὶ θείᾳ παντάπαϲιν ἔοικεν εὐεργεϲίᾳ'), ('line/gr0014w002/222', 'δεῖ τοίνυν ὦ ἄνδρεϲ ἀθηναῖοι τοῦτ’ ἤδη ϲκοπεῖν αὐτούϲ ὅπωϲ μὴ χείρουϲ περὶ ἡμᾶϲ αὐτοὺϲ εἶναι δόξομεν τῶν ὑπαρχόντων ὡϲ ἔϲτι τῶν αἰϲχρῶν μᾶλλον δὲ τῶν αἰϲχίϲτων μὴ μόνον πόλεων καὶ τόπων ὧν ἦμέν ποτε κύριοι φαίνεϲθαι προϊεμένουϲ ἀλλὰ καὶ τῶν ὑπὸ τῆϲ τύχηϲ παραϲκευαϲθέντων ϲυμμάχων καὶ καιρῶν'), ('line/gr0014w002/227', 'τὸ μὲν οὖν ὦ ἄνδρεϲ ἀθηναῖοι τὴν φιλίππου ῥώμην διεξιέναι καὶ διὰ τούτων τῶν λόγων προτρέπειν τὰ δέοντα ποιεῖν ὑμᾶϲ οὐχὶ καλῶϲ ἔχειν ἡγοῦμαι'), ('line/gr0014w002/229', 'διὰ τί'), ('line/gr0014w002/230', 'ὅτι μοι δοκεῖ πάνθ’ ὅϲ’ ἂν εἴποι τιϲ ὑπὲρ τούτων ἐκείνῳ μὲν ἔχειν φιλοτιμίαν ἡμῖν δ’ οὐχὶ καλῶϲ πεπρᾶχθαι'), ('line/gr0014w002/232', 'ὁ μὲν γὰρ ὅϲῳ πλείον’ ὑπὲρ τὴν ἀξίαν πεποίηκε τὴν αὑτοῦ τοϲούτῳ θαυπροϲῆκε κέχρηϲθε τοῖϲ πράγμαϲι τοϲούτῳ πλείον’ αἰϲχύνην ὠφλήκατε'), ('line/gr0014w002/235', 'ταῦτα μὲν οὖν παραλείψω'), ...]

	Τὸ μὲν οὖν, ὦ ἄνδρεϲ Ἀθηναῖοι, τὴν Φιλίππου ῥώμην 	3.1
	διεξιέναι καὶ διὰ τούτων τῶν λόγων προτρέπειν τὰ δέοντα
	ποιεῖν ὑμᾶϲ, οὐχὶ καλῶϲ ἔχειν ἡγοῦμαι. διὰ τί; ὅτι μοι
	δοκεῖ πάνθ’ ὅϲ’ ἂν εἴποι τιϲ ὑπὲρ τούτων, ἐκείνῳ μὲν ἔχειν
	φιλοτιμίαν, ἡμῖν δ’ οὐχὶ καλῶϲ πεπρᾶχθαι. ὁ μὲν γὰρ ὅϲῳ
	πλείον’ ὑπὲρ τὴν ἀξίαν πεποίηκε τὴν αὑτοῦ, τοϲούτῳ θαυ-
	μαϲτότεροϲ παρὰ πᾶϲι νομίζεται· ὑμεῖϲ δ’ ὅϲῳ χεῖρον ἢ 	3.7
	προϲῆκε κέχρηϲθε τοῖϲ πράγμαϲι, τοϲούτῳ πλείον’ αἰϲχύνην
	ὠφλήκατε.

	THE HUNT....

	but the function is sent the whole text:

	r0 markedup: &nbsp;&nbsp;&nbsp;Ἐπὶ πολλῶν μὲν ἄν τιϲ ἰδεῖν, ὦ ἄνδρεϲ Ἀθηναῖοι, δοκεῖ

	allsentences[0]: Ἐπὶ πολλῶν μὲν ἄν τιϲ ἰδεῖν, ὦ ἄνδρεϲ Ἀθηναῖοι, δοκεῖ μοι τὴν παρὰ τῶν θεῶν εὔνοιαν φανερὰν γιγνομένην τῇ πόλει, οὐχ ἥκιϲτα δ’ ἐν τοῖϲ παροῦϲι πράγμαϲι
	matches[0] is fine @ matches = [' '.join(m.split()) for m in matches]

	end: (0, 'ἐπὶ πολλῶν μὲν ἄν τιϲ ἰδεῖν ὦ ἄνδρεϲ ἀθηναῖοι δοκεῖ μοι τὴν παρὰ τῶν θεῶν εὔνοιαν φανερὰν γιγνομένην τῇ πόλει οὐχ ἥκιϲτα δ’ ἐν τοῖϲ παροῦϲι πράγμαϲι')

	:param searchobject:
	:param lineobjects:
	:return:
	"""

	requiresids = ['semanticvectorquery', 'nearestneighborsquery', 'sentencesimilarity']

	columnmap = {'marked_up_line': 'markedup', 'accented_line': 'polytonic', 'stripped_line': 'stripped'}
	col = columnmap[so.usecolumn]

	if so.vectorquerytype in requiresids:
		wholetext = ' '.join(['⊏{i}⊐{t}'.format(i=l.getlineurl(), t=getattr(l, col)) for l in lineobjects])
	else:
		wholetext = ' '.join([getattr(l, col) for l in lineobjects])

	if so.usecolumn == 'marked_up_line':
		wholetext = cleanvectortext(wholetext)

	# need to split at all possible sentence ends
	# need to turn off semicolon in latin...
	# latin: ['.', '?', '!']
	# greek: ['.', ';', '!', '·']

	terminations = ['.', '?', '!', '·', ';']
	allsentences = recursivesplit([wholetext], terminations)

	# print('type(so.lemma)', type(so.lemma))
	if so.vectorquerytype == 'cosdistbysentence':
		terms = [acuteorgrav(t) for t in so.lemma.formlist]
		lookingfor = "|".join(terms)
		lookingfor = '({lf})'.format(lf=lookingfor)
	else:
		lookingfor = so.seeking

	if lookingfor != '.':
		# uv problem...
		allsentences = [basiclemmacleanup(s) for s in allsentences]
		matches = [s for s in allsentences if re.search(lookingfor, s)]
	else:
		matches = allsentences

	# hyphenated line-ends are a problem: oriun- tur --> oriuntur
	matches = [re.sub(r'-\s{1,2}', str(), m) for m in matches]
	# matches = [re.sub(r'-\s{0,2}', str(), m) for m in matches]

	# more cleanup
	matches = [m.lower() for m in matches]
	matches = [' '.join(m.split()) for m in matches]

	# how many sentences per document?
	# do values >1 make sense? Perhaps in dramatists...
	bundlesize = so.sentencebundlesize

	if bundlesize > 1:
		# https://stackoverflow.com/questions/44104729/grouping-every-three-items-together-in-list-python
		matches = [' '.join(bundle) for bundle in zip(*[iter(matches)] * bundlesize)]

	# FIXME: there is a problem with  τ’ and δ’ and the rest (refactor via indexmaker.py)
	# nevertheless, most of these words are going to be stopwords anyway
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + elidedextrapunct)))
	if so.vectorquerytype in requiresids:
		# now we mark the source of every sentence by turning it into a tuple: (location, text)
		previousid = lineobjects[0].getlineurl()
		idfinder = re.compile(r'⊏(.*?)⊐')
		taggedmatches = list()
		for m in matches:
			ids = re.findall(idfinder, m)
			if ids:
				taggedmatches.append((ids[0], re.sub(idfinder, str(), m)))
				previousid = ids[-1]
			else:
				taggedmatches.append((previousid, m))

		cleanedmatches = [(lineid, tidyupterm(m, punct)) for lineid, m in taggedmatches]
	else:
		cleanedmatches = [(n, tidyupterm(m, punct)) for n, m in enumerate(matches)]

	return cleanedmatches


def convertmophdicttodict(morphdict: dict) -> dict:
	"""

	return a dict of dicts of possibilities for all of the words we will be using

	key = word-in-use
	value = { maybeA, maybeB, maybeC}

	{'θεῶν': {'θεόϲ', 'θέα', 'θεάω', 'θεά'}, 'πώ': {'πω'}, 'πολλά': {'πολύϲ'}, 'πατήρ': {'πατήρ'}, ... }

	relies heavily on dbMorphologyObject.getpossible()
	and this itself is going to rely on MorphPossibilityObject.getbaseform()

	:return:
	"""

	dontskipunknowns = True

	parseables = {k: v for k, v in morphdict.items() if v is not None}
	parseables = {k: set([p.getbaseform() for p in parseables[k].getpossible()]) for k in parseables.keys()}

	if dontskipunknowns:
		# if the base for was not found, associate a word with itself
		unparseables = {k: {k} for k, v in morphdict.items() if v is None}
		newmorphdict = {**unparseables, **parseables}
	else:
		newmorphdict = parseables

	# over-aggressive? more thought/care might be required here
	# the definitely changes the shape of the bags of words...
	delenda = mostcommonheadwords()
	newmorphdict = {k: v for k, v in newmorphdict.items() if v - delenda == v}

	return newmorphdict


def bruteforcefinddblinefromsentence(thissentence, modifiedsearchobject):
	"""

	get a locus from a random sentence coughed up by the vector corpus

	:param thissentence:
	:param searchobject:
	:return:
	"""

	nullpoll = ProgressPoll(time.time())
	mso = modifiedsearchobject
	mso.lemma = None
	mso.proximatelemma = None
	mso.searchtype = 'phrase'
	mso.usecolumn = 'accented_line'
	mso.usewordlist = 'polytonic'
	mso.accented = True
	mso.seeking = ' '.join(thissentence[:6])
	mso.termone = mso.seeking
	mso.termtwo = ' '.join(thissentence[-5:])
	mso.poll = nullpoll
	hits = precomposedsqlsearch(mso)

	# if len(hits) > 1:
	# 	print('findlocusfromsentence() found {h} hits when looking for {s}'.format(h=len(hits), s=mso.seeking))

	return hits


def finddblinesfromsentences(thissentence, sentencestuples, cursor):
	"""

	given a sentencelist ['word1', 'word2', word3', ...] , look for a match in a sentence tuple collection:
		[(universalid1, text1), (universalid2, text2), ...]

	returns a list of dblines

	:param thissentence:
	:param sentencestuples:
	:return:
	"""

	thissentence = ' '.join(thissentence)

	matches = list()
	for s in sentencestuples:
		cleans = s[1].strip()
		if cleans == thissentence:
			matches.append(s[0])

	fetchedlines = convertlineuidstolineobject(matches, cursor)

	return fetchedlines


def convertlineuidstolineobject(listoflines, cursor):
	"""

	given a list of universalids, fetch the relevant lines

	would be more efficient if you grabbed all of them at once
	for any given table.

	but note that these lists are usually just one item long

	:return:
	"""

	fetchedlines = list()
	for uid in listoflines:
		fetchedlines.append(convertsingleuidtodblineobject(uid, cursor))

	return fetchedlines


def convertsingleuidtodblineobject(lineuid, cursor):
	"""

	:param lineuid:
	:param cursor:
	:return:
	"""

	# print('convertsingleuidtodblineobject() lineuid', lineuid)

	db = lineuid.split('_')[0][:6]
	ln = lineuid.split('_')[-1]

	try:
		myline = grabonelinefromwork(db, ln, cursor)
		fetchedline = dblineintolineobject(myline)
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "l" does not exist
		fetchedline = None

	return fetchedline


def mostcommoninflectedforms(cheat=True) -> set:
	"""

	figure out what gets used the most

	can use this to drop items from sentences before we get to
	headwords and their homonym problems

	hipparchiaDB=# SELECT entry_name,total_count FROM wordcounts_a ORDER BY total_count DESC LIMIT 10;
	entry_name | total_count
	------------+-------------
	ad         |       68000
	a          |       65487
	aut        |       32020
	ab         |       26047
	atque      |       21686
	autem      |       20164
	ac         |       19066
	an         |       12405
	ante       |        9535
	apud       |        7399
	(10 rows)

	hipparchiaDB=# SELECT entry_name,total_count FROM wordcounts_α ORDER BY total_count DESC LIMIT 10;
	entry_name | total_count
	------------+-------------
	ἀπό        |      256257
	αὐτοῦ      |      242718
	ἄν         |      225966
	ἀλλά       |      219506
	ἀλλ        |      202609
	αὐτόν      |      163403
	αὐτῶν      |      145216
	αὐτῷ       |      134328
	αἱ         |      102667
	αὐτόϲ      |       89056

	mostcommoninflectedforms()
	('καί', 4507887)
	('δέ', 1674979)
	('τό', 1496102)
	('τοῦ', 1286914)
	('τῶν', 1127343)
	('τήν', 1053085)
	('τῆϲ', 935988)
	('ὁ', 874987)
	...
	('οἷϲ', 40448)
	('πολλά', 40255)
	('δραχμαί', 40212)
	('εἶπεν', 40154)
	('ἄλλων', 40104)
	...

	('c', 253099)
	('et', 227463)
	('in', 183970)
	('est', 105956)
	('non', 96510)
	('ut', 75705)
	('ad', 68000)
	('cum', 66544)
	('a', 65487)
	('si', 62655)
	('quod', 56694)
	...

	('ipsa', 5372)
	('inquit', 5342)
	('nomine', 5342)
	('sint', 5342)
	('nobis', 5317)
	('primum', 5297)
	('itaque', 5271)
	('unde', 5256)
	('illi', 5227)
	('siue', 5208)
	('illud', 5206)
	('eos', 5186)
	('pace', 5114)
	('parte', 5049)
	('n', 5032)
	('tempore', 5018)
	('satis', 5007)
	('rerum', 4999)
	...

	:param cheat:
	:return:
	"""

	if not cheat:
		dbconnection = ConnectionObject()
		dbcursor = dbconnection.cursor()

		latinletters = 'abcdefghijklmnopqrstuvwxyz'
		greekletters = '0αβψδεφγηιξκλμνοπρϲτυωχθζ'

		# needed for initial probe
		# limit = 50
		# qtemplate = """
		# SELECT entry_name,total_count FROM wordcounts_{letter} ORDER BY total_count DESC LIMIT {lim}
		# """

		qtemplate = """
		SELECT entry_name FROM wordcounts_{letter} WHERE total_count > %s ORDER BY total_count DESC 
		"""

		greekmorethan = 40000
		latinmorethan = 5031
		countlist = list()

		for letters, cap in [(latinletters, latinmorethan), (greekletters, greekmorethan)]:
			langlist = list()
			for l in letters:
				data = (cap,)
				dbcursor.execute(qtemplate.format(letter=l), data)
				tophits = resultiterator(dbcursor)
				langlist.extend([t[0] for t in tophits])
			# langlist = sorted(langlist, key=lambda x: x[1], reverse=True)
			countlist.extend(langlist)

		print('mostcommoninflectedforms()')
		mcif = set(countlist)
		print(mcif)
	else:
		mcif = {'ita', 'a', 'inquit', 'ego', 'die', 'nunc', 'nos', 'quid', 'πάντων', 'ἤ', 'με', 'θεόν', 'δεῖ', 'for',
		        'igitur', 'ϲύν', 'b', 'uers', 'p', 'ϲου', 'τῷ', 'εἰϲ', 'ergo', 'ἐπ', 'ὥϲτε', 'sua', 'me', 'πρό', 'sic',
		        'aut', 'nisi', 'rem', 'πάλιν', 'ἡμῶν', 'φηϲί', 'παρά', 'ἔϲτι', 'αὐτῆϲ', 'τότε', 'eos', 'αὐτούϲ',
		        'λέγει', 'cum', 'τόν', 'quidem', 'ἐϲτιν', 'posse', 'αὐτόϲ', 'post', 'αὐτῶν', 'libro', 'm', 'hanc',
		        'οὐδέ', 'fr', 'πρῶτον', 'μέν', 'res', 'ἐϲτι', 'αὐτῷ', 'οὐχ', 'non', 'ἐϲτί', 'modo', 'αὐτοῦ', 'sine',
		        'ad', 'uero', 'fuit', 'τοῦ', 'ἀπό', 'ea', 'ὅτι', 'parte', 'ἔχει', 'οὔτε', 'ὅταν', 'αὐτήν', 'esse',
		        'sub', 'τοῦτο', 'i', 'omnes', 'break', 'μή', 'ἤδη', 'ϲοι', 'sibi', 'at', 'mihi', 'τήν', 'in', 'de',
		        'τούτου', 'ab', 'omnia', 'ὃ', 'ἦν', 'γάρ', 'οὐδέν', 'quam', 'per', 'α', 'autem', 'eius', 'item', 'ὡϲ',
		        'sint', 'length', 'οὗ', 'λόγον', 'eum', 'ἀντί', 'ex', 'uel', 'ἐπειδή', 're', 'ei', 'quo', 'ἐξ',
		        'δραχμαί', 'αὐτό', 'ἄρα', 'ἔτουϲ', 'ἀλλ', 'οὐκ', 'τά', 'ὑπέρ', 'τάϲ', 'μάλιϲτα', 'etiam', 'haec',
		        'nihil', 'οὕτω', 'siue', 'nobis', 'si', 'itaque', 'uac', 'erat', 'uestig', 'εἶπεν', 'ἔϲτιν', 'tantum',
		        'tam', 'nec', 'unde', 'qua', 'hoc', 'quis', 'iii', 'ὥϲπερ', 'semper', 'εἶναι', 'e', '½', 'is', 'quem',
		        'τῆϲ', 'ἐγώ', 'καθ', 'his', 'θεοῦ', 'tibi', 'ubi', 'pro', 'ἄν', 'πολλά', 'τῇ', 'πρόϲ', 'l', 'ἔϲται',
		        'οὕτωϲ', 'τό', 'ἐφ', 'ἡμῖν', 'οἷϲ', 'inter', 'idem', 'illa', 'n', 'se', 'εἰ', 'μόνον', 'ac', 'ἵνα',
		        'ipse', 'erit', 'μετά', 'μοι', 'δι', 'γε', 'enim', 'ille', 'an', 'sunt', 'esset', 'γίνεται', 'omnibus',
		        'ne', 'ἐπί', 'τούτοιϲ', 'ὁμοίωϲ', 'παρ', 'causa', 'neque', 'cr', 'ἐάν', 'quos', 'ταῦτα', 'h', 'ante',
		        'ἐϲτίν', 'ἣν', 'αὐτόν', 'eo', 'ὧν', 'ἐπεί', 'οἷον', 'sed', 'ἀλλά', 'ii', 'ἡ', 't', 'te', 'ταῖϲ', 'est',
		        'sit', 'cuius', 'καί', 'quasi', 'ἀεί', 'o', 'τούτων', 'ἐϲ', 'quae', 'τούϲ', 'minus', 'quia', 'tamen',
		        'iam', 'd', 'διά', 'primum', 'r', 'τιϲ', 'νῦν', 'illud', 'u', 'apud', 'c', 'ἐκ', 'δ', 'quod', 'f',
		        'quoque', 'tr', 'τί', 'ipsa', 'rei', 'hic', 'οἱ', 'illi', 'et', 'πῶϲ', 'φηϲίν', 'τοίνυν', 's', 'magis',
		        'unknown', 'οὖν', 'dum', 'text', 'μᾶλλον', 'λόγοϲ', 'habet', 'τοῖϲ', 'qui', 'αὐτοῖϲ', 'suo', 'πάντα',
		        'uacat', 'τίϲ', 'pace', 'ἔχειν', 'οὐ', 'κατά', 'contra', 'δύο', 'ἔτι', 'αἱ', 'uet', 'οὗτοϲ', 'deinde',
		        'id', 'ut', 'ὑπό', 'τι', 'lin', 'ἄλλων', 'τε', 'tu', 'ὁ', 'cf', 'δή', 'potest', 'ἐν', 'eam', 'tum',
		        'μου', 'nam', 'θεόϲ', 'κατ', 'ὦ', 'cui', 'nomine', 'περί', 'atque', 'δέ', 'quibus', 'ἡμᾶϲ', 'τῶν',
		        'eorum'}

	return mcif


def uselessforeignwords() -> set:
	"""

	stuff that clogs up the data, esp in the papyri, etc

	quite incomplete at the moment; a little thought could derive a decent amount of it algorithmically

	:return:
	"""

	useless = {'text', 'length', 'unknown', 'break', 'uestig', 'uac'}

	return useless


def mostcommonheadwords(cheat=True) -> set:
	"""

	fetch N most common Greek and Latin

	build an exclusion list from this and return it: wordstoskip

	but first prune the common word list of words you nevertheless are interested in

	:return: wordstoskip
	"""

	if cheat:
		# this is what you will get if you calculate
		# since it tends not to change, you can cheat unless/until you modify
		# either the dictionaries or wordswecareabout or the cutoff...
		l = set(hwlat100) - keeplatin
		g = set(hwgrk150) - keepgreek
		wordstoskip = l.union(g)
	else:
		wordswecareabout = {
			'facio', 'possum', 'video', 'dico²', 'vaco', 'volo¹', 'habeo', 'do', 'vis',
			'ἔδω', 'δέω¹', 'δεῖ', 'δέομαι', 'ἔχω', 'λέγω¹', 'φημί', 'θεόϲ', 'ποιέω', 'πολύϲ',
			'ἄναξ', 'λόγοϲ'
		}

		dbconnection = ConnectionObject()
		dbcursor = dbconnection.cursor()

		qtemplate = """
		SELECT entry_name,total_count FROM dictionary_headword_wordcounts 
			WHERE entry_name ~ '[{yesorno}a-zA-Z]' ORDER BY total_count DESC LIMIT {lim}
		"""

		counts = dict()

		# grab the raw data: a greek query and a latin query
		# note that different limits have been set for each language
		for gl in {('', 75), ('^', 100)}:
			yesorno = gl[0]
			lim = gl[1]
			dbcursor.execute(qtemplate.format(yesorno=yesorno, lim=lim))
			tophits = resultiterator(dbcursor)
			tophits = {t[0]: t[1] for t in tophits}
			counts.update(tophits)

		# results = ['{wd} - {ct}'.format(wd=c, ct=counts[c]) for c in counts]
		#
		# for r in results:
		# 	print(r)

		wordstoskip = list(counts.keys() - wordswecareabout)

		qtemplate = """
		SELECT entry_name FROM {d} WHERE pos=ANY(%s)
		"""

		exclude = ['interj.', 'prep.', 'conj.', 'partic.']
		x = (exclude,)

		uninteresting = list()
		for d in ['greek_dictionary', 'latin_dictionary']:
			dbcursor.execute(qtemplate.format(d=d), x)
			finds = resultiterator(dbcursor)
			uninteresting += [f[0] for f in finds]

		wordstoskip = set(wordstoskip + uninteresting)

		dbconnection.connectioncleanup()

		# print('wordstoskip =', wordstoskip)

	wordstoskip.union(uselessforeignwords())

	return wordstoskip


def mostcommonwordsviaheadwords() -> set:
	"""

	use mostcommonheadwords to return the most common declined forms

		... 'ὁ', 'χἤ', 'χὤ', 'τάν', 'τοῦ', 'τώϲ', ...

	:return:
	"""

	headwords = mostcommonheadwords()

	wordstoskip = list()
	for h in headwords:
		try:
			wordstoskip.extend(lemmatadict[h].formlist)
		except KeyError:
			pass

	mostcommonwords = set(wordstoskip)

	mostcommonwords.union(uselessforeignwords())

	return mostcommonwords


def removestopwords(sentencestring: str, stopwords: list) -> str:
	"""

	take a sentence and throw out the stopwords in it

	:param sentencestring:
	:param stopwords:
	:return:
	"""

	wordlist = sentencestring.split(' ')
	wordlist = [removegravity(w) for w in wordlist if removegravity(w) not in stopwords]
	newsentence = ' '.join(wordlist)
	return newsentence


def relativehomonymnweight(worda, wordb, morphdict) -> float:
	"""

	NOT YET CALLED BY ANY VECTOR CODE

	accepto and acceptum share many forms, what is the liklihood that accepta comes from the verb and not the noun?

	est: is it from esse or edere?

	This is a huge problem. One way to approcimate an answer would be to take the sum of the non-overlapping forms
	and then use this as a ratio that yields a pseudo-probability

	Issues that arise: [a] perfectly convergent forms; [b] non-overlap in only one quarter; [c] corporal-sensitive
	variations (i.e., some forms more likely in an inscriptional context)

	hipparchiaDB=# select total_count from dictionary_headword_wordcounts where entry_name='sum¹';
	 total_count
	-------------
	      118369
	(1 row)

	hipparchiaDB=# select total_count from dictionary_headword_wordcounts where entry_name='edo¹';
	 total_count
	-------------
	      159481
	(1 row)

	:param worda:
	:param wordb:
	:param morphdict:
	:return:
	"""

	aheadwordobject = querytotalwordcounts(worda)
	bheadwordobject = querytotalwordcounts(wordb)
	atotal = aheadwordobject.t
	btotal = bheadwordobject.t
	try:
		totalratio = atotal/btotal
	except ZeroDivisionError:
		# how you managed to pick a zero headword would be interesting to know
		totalratio = -1

	auniqueforms = morphdict[worda] - morphdict[wordb]
	buniqueforms = morphdict[wordb] - morphdict[worda]

	auniquecounts = [dbWordCountObject(*findcountsviawordcountstable(wd)) for wd in auniqueforms]
	buniquecounts = [dbWordCountObject(*findcountsviawordcountstable(wd)) for wd in buniqueforms]

	aunique = sum([x.t for x in auniquecounts])
	bunique = sum([x.t for x in buniquecounts])
	try:
		uniqueratio = aunique/bunique
	except ZeroDivisionError:
		uniqueratio = -1

	if uniqueratio <= 0:
		return totalratio
	else:
		return uniqueratio


def reducetotwodimensions(model) -> dict:
	"""
	copied from
	https://radimrehurek.com/gensim/auto_examples/tutorials/run_word2vec.html#sphx-glr-auto-examples-tutorials-run-word2vec-py

	:param model:
	:return:
	"""

	dimensions = 2  # final num dimensions (2D, 3D, etc)

	vectors = list()  # positions in vector space
	labels = list()  # keep track of words to label our data again later
	for word in model.wv.vocab:
		vectors.append(model.wv[word])
		labels.append(word)

	# convert both lists into numpy vectors for reduction
	vectors = np.asarray(vectors)
	labels = np.asarray(labels)

	# reduce using t-SNE
	vectors = np.asarray(vectors)
	tsne = TSNE(n_components=dimensions, random_state=0)
	vectors = tsne.fit_transform(vectors)

	xvalues = [v[0] for v in vectors]
	yvalues = [v[1] for v in vectors]

	returndict = dict()
	returndict['xvalues'] = xvalues
	returndict['yvalues'] = yvalues
	returndict['labels'] = labels

	return returndict


def emptyvectoroutput(searchobject, reasons=None):
	"""

	no results; say as much

	:return:
	"""

	if not reasons:
		reasons = list()

	so = searchobject

	so.poll.allworkis(-1)
	so.poll.deactivate()

	output = SearchOutputObject(so)
	output.success = '<!-- FAILED -->'
	output.reasons = reasons

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c]]

	if not activecorpora:
		output.reasons.append('there are no active databases')
	if not (so.lemma or so.seeking):
		output.reasons.append('no search term was provided')

	output.explainemptysearch()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


"""

CHEAT SKIPWORD BLOCKS

"""

hwlat100 = ['qui¹', 'et', 'in', 'edo¹', 'is', 'sum¹', 'hic', 'non', 'ab', 'ut', 'Cos²', 'si', 'ad', 'cum', 'ex', 'a', 'eo¹',
	  'ego', 'quis¹', 'tu', 'Eos', 'dico²', 'ille', 'sed', 'de', 'neque', 'facio', 'possum', 'atque', 'sui', 'res',
	  'quam', 'aut', 'ipse', 'huc', 'habeo', 'do', 'omne', 'video', 'ito', 'magnus', 'b', 'alius²', 'for', 'idem',
	  'suum', 'etiam', 'per', 'enim', 'omnes', 'ita', 'suus', 'omnis', 'autem', 'vel', 'vel', 'Alius¹', 'qui²', 'quo',
	  'nam', 'bonus', 'neo¹', 'meus', 'volo¹', 'ne³', 'ne¹', 'suo', 'verus', 'pars', 'reor', 'sua', 'vaco', 'verum',
	  'primus', 'unus', 'multus', 'causa', 'jam', 'tamen', 'Sue', 'nos', 'dies', 'Ios', 'modus', 'tuus', 'venio',
	  'pro¹', 'pro²', 'ago', 'deus', 'annus', 'locus', 'homo', 'pater', 'eo²', 'tantus', 'fero', 'quidem', 'noster',
	  'an', 'locum']

hwgrk150 = ['ὁ', 'καί', 'τίϲ', 'ἔδω', 'δέ', 'εἰμί', 'δέω¹', 'δεῖ', 'δέομαι', 'εἰϲ', 'αὐτόϲ', 'τιϲ', 'οὗτοϲ', 'ἐν',
			'γάροϲ', 'γάρον', 'γάρ', 'οὐ', 'μένω', 'μέν', 'τῷ', 'ἐγώ', 'ἡμόϲ', 'κατά', 'Ζεύϲ', 'ἐπί', 'ὡϲ', 'διά',
			'πρόϲ', 'προϲάμβ', 'τε', 'πᾶϲ', 'ἐκ', 'ἕ', 'ϲύ', 'Ἀλλά', 'γίγνομαι', 'ἁμόϲ', 'ὅϲτιϲ', 'ἤ¹', 'ἤ²', 'ἔχω',
			'ὅϲ', 'μή', 'ὅτι¹', 'λέγω¹', 'ὅτι²', 'τῇ', 'Τήιοϲ', 'ἀπό', 'εἰ', 'περί', 'ἐάν', 'θεόϲ', 'φημί', 'ἐκάϲ',
			'ἄν¹', 'ἄνω¹', 'ἄλλοϲ', 'qui¹', 'πηρόϲ', 'παρά', 'ἀνά', 'αὐτοῦ', 'ποιέω', 'ἄναξ', 'ἄνα', 'ἄν²', 'πολύϲ',
			'οὖν', 'λόγοϲ', 'οὕτωϲ', 'μετά', 'ἔτι', 'ὑπό', 'ἑαυτοῦ', 'ἐκεῖνοϲ', 'εἶπον', 'πρότεροϲ', 'edo¹', 'μέγαϲ',
			'ἵημι', 'εἷϲ', 'οὐδόϲ', 'οὐδέ', 'ἄνθρωποϲ', 'ἠμί', 'μόνοϲ', 'κύριοϲ', 'διό', 'οὐδείϲ', 'ἐπεί', 'πόλιϲ',
			'τοιοῦτοϲ', 'χάω', 'καθά', 'θεάομαι', 'γε', 'ἕτεροϲ', 'δοκέω', 'λαμβάνω', 'δή', 'δίδωμι', 'ἵνα',
			'βαϲιλεύϲ', 'φύϲιϲ', 'ἔτοϲ', 'πατήρ', 'ϲῶμα', 'καλέω', 'ἐρῶ', 'υἱόϲ', 'ὅϲοϲ', 'γαῖα', 'οὔτε', 'οἷοϲ',
			'ἀνήρ', 'ὁράω', 'ψυχή', 'Ἔχιϲ', 'ὥϲπερ', 'αὐτόϲε', 'χέω', 'ὑπέρ', 'ϲόϲ', 'θεάω', 'νῦν', 'ἐμόϲ', 'δύναμαι',
			'φύω', 'πάλιν', 'ὅλοξ', 'ἀρχή', 'καλόϲ', 'δύναμιϲ', 'πωϲ', 'δύο', 'ἀγαθόϲ', 'οἶδα', 'δείκνυμι', 'χρόνοϲ',
			'ὅμοιοϲ', 'ἕκαϲτοϲ', 'ὁμοῖοϲ', 'ὥϲτε', 'ἡμέρα', 'γράφω', 'δραχμή', 'μέροϲ']

keeplatin = {'facio', 'possum', 'habeo', 'video', 'magnus', 'bonus', 'volo¹', 'primus', 'venio', 'ago', 'deus', 'annus',
			 'locus', 'pater', 'fero'}

keepgreek = {'ἔχω', 'λέγω¹', 'θεόϲ', 'φημί', 'ποιέω', 'ἵημι', 'μόνοϲ', 'κύριοϲ', 'πόλιϲ', 'θεάομαι', 'δοκέω', 'λαμβάνω',
			 'δίδωμι', 'βαϲιλεύϲ', 'φύϲιϲ', 'ἔτοϲ', 'πατήρ', 'ϲῶμα', 'καλέω', 'ἐρῶ', 'υἱόϲ', 'γαῖα', 'ἀνήρ', 'ὁράω',
			 'ψυχή', 'δύναμαι', 'ἀρχή', 'καλόϲ', 'δύναμιϲ', 'ἀγαθόϲ', 'οἶδα', 'δείκνυμι', 'χρόνοϲ', 'γράφω', 'δραχμή',
			 'μέροϲ'}

# golang might want to know this...

# l = set(hwlat100) - keeplatin
# g = set(hwgrk150) - keepgreek
# wordstoskip = l.union(g)
# ws = ' '.join([w for w in wordstoskip])