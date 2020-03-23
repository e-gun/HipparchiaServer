# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from flask import session

from server.dbsupport.bulkdboperations import bulklexicalgrab
from server.dbsupport.lexicaldbfunctions import lookformorphologymatches
from server.formatting.vectorformatting import formatnnmatches, formatnnsimilarity, nearestneighborgenerateoutput
from server.hipparchiaobjects.lexicalobjects import dbColumnorderGreekword, dbColumnorderLatinword
from server.hipparchiaobjects.morphanalysisobjects import BaseFormMorphology
from server.hipparchiaobjects.vectorobjects import VectorValues
from server.semanticvectors.gensimmodels import buildgensimmodel
from server.semanticvectors.vectorgraphing import graphnnmatches
from server.semanticvectors.vectorhelpers import convertmophdicttodict, findwordvectorset
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput
from server.startup import lemmatadict
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects
from server.hipparchiaobjects.connectionobject import ConnectionObject


def generatenearestneighbordata(sentencetuples, workssearched, searchobject, vectorspace):
	"""

	this is where we go after executegensimsearch() makes its function pick

	[a] buildnnvectorspace (if needed)
	[b] do the right sort of search
		findword2vecsimilarities
		findapproximatenearestneighbors
	[c] generate the output

	:param searchobject:
	:param activepoll:
	:param sentencetuples:
	:param workssearched:
	:param starttime:
	:param vectorspace:
	:return:
	"""

	posrestriction = 'testing'

	so = searchobject
	vv = so.vectorvalues
	activepoll = so.poll
	imagename = str()
	try:
		termone = so.lemma.dictionaryentry
	except AttributeError:
		# AttributeError: 'str' object has no attribute 'dictionaryentry'
		# session['baggingmethod'] == 'unlemmatized' (I hope...)
		termone = so.seeking

	try:
		termtwo = so.proximatelemma.dictionaryentry
	except AttributeError:
		termtwo = None

	if not vectorspace:
		vectorspace = buildnnvectorspace(sentencetuples, so)
		if vectorspace == 'failed to build model':
			reasons = [vectorspace]
			return emptyvectoroutput(so, reasons)

	if termone and termtwo:
		similarity = findword2vecsimilarities(termone, termtwo, vectorspace)
		similarity = formatnnsimilarity(termone, termtwo, similarity)
		mostsimilar = ['placeholder']
		html = similarity
	else:
		activepoll.statusis('Calculating the nearest neighbors')
		mostsimilar = findapproximatenearestneighbors(termone, vectorspace, vv)
		# [('εὕρηϲιϲ', 1.0), ('εὑρίϲκω', 0.6673248708248138), ('φυϲιάω', 0.5833806097507477), ('νόμοϲ', 0.5505017340183258), ...]
		if not mostsimilar:
			# proper noun? Ϲωκράτηϲ --> ϲωκράτηϲ
			termone = termone[0].lower() + termone[1:]
			mostsimilar = findapproximatenearestneighbors(termone, vectorspace, vv)
		if mostsimilar:
			# you can get back >1000 items
			if posrestriction:
				activepoll.statusis('Trimming by part of speech')
				validset = trimbypartofspeech([m[0] for m in mostsimilar], posrestriction)
				mostsimilar = [m for m in mostsimilar if m[0] in validset]
			html = formatnnmatches(mostsimilar, vv)
			activepoll.statusis('Building the graph')
			mostsimilar = mostsimilar[:vv.neighborscap]
			imagename = graphnnmatches(termone, mostsimilar, vectorspace, so)
		else:
			html = '<pre>["{t}" was not found in the vector space]</pre>'.format(t=termone)

	findshtml = '{h}'.format(h=html)

	output = nearestneighborgenerateoutput(findshtml, mostsimilar, imagename, workssearched, searchobject)

	return output


def buildnnvectorspace(sentencetuples, searchobject):
	"""

	find the words
	find the morphology objects you need for those words
	build vectors

	:return:
	"""

	wordbundler = False

	activepoll = searchobject.poll

	# find all words in use
	listsofwords = [s[1] for s in sentencetuples]
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	wl = '{:,}'.format(len(listsofwords))
	activepoll.statusis(
		'No stored model for this search. Generating a new one.<br />Finding headwords for {n} sentences'.format(n=wl))

	morphdict = getrequiredmorphobjects(allwords, furtherdeabbreviate=True)

	# associate each word with its possible headwords
	morphdict = convertmophdicttodict(morphdict)

	# import re
	# teststring = r'aesa'
	# kvpairs = [(k,morphdict[k]) for k in morphdict.keys() if re.search(teststring, k)]
	# print('convertmophdicttodict', kvpairs)
	# sample selection:
	# convertmophdicttodict [('caesare', {'caesar'}), ('caesarisque', {'caesar'}), ('caesari', {'caesar'}), ('caesar', {'caesar'}), ('caesa', {'caesum', 'caesa', 'caesus¹', 'caedo'}), ('caesaremque', {'caesar'}), ('caesaris', {'caesar'}), ('caesarem', {'caesar'})]

	if wordbundler:
		morphdict = {t: '·'.join(morphdict[t]) for t in morphdict}

	activepoll.statusis('No stored model for this search. Generating a new one.<br />Building vectors for the headwords in the {n} sentences'.format(n=wl))
	vectorspace = buildgensimmodel(searchobject, morphdict, listsofwords)

	return vectorspace


def findapproximatenearestneighbors(query, mymodel, vectorvalues: VectorValues):
	"""

	search for points in space that are close to a given query point

	the query should be a dictionary headword

	this returns a list of tuples: (word, distance)

	:param query:
	:param mymodel:
	:param vectorvalues:
	:return:
	"""

	explore = max(2500, vectorvalues.neighborscap)

	try:
		mostsimilar = mymodel.wv.most_similar(query, topn=explore)
		mostsimilar = [s for s in mostsimilar if s[1] > vectorvalues.nearestneighborcutoffdistance]
	except KeyError:
		# keyedvectors.py: raise KeyError("word '%s' not in vocabulary" % word)
		mostsimilar = None
	except AttributeError:
		# 'NoneType' object has no attribute 'most_similar'
		mostsimilar = None

	#print('mostsimilar', mostsimilar)

	return mostsimilar


def findword2vecsimilarities(termone, termtwo, mymodel):
	"""

	WordEmbeddingsKeyedVectors in keyedvectors.py gives the methods

		similarity(w1, w2)
			[similarity('woman', 'man')]

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	similarity = mymodel.wv.similarity(termone, termtwo)

	return similarity


def trimbypartofspeech(listofwords: List[str], partofspeech: str) -> set:
	"""

	return only the adjectives, e.g., in a list of headwords

	note these are words and not HeadwordObjects

	need a collection of BaseFormMorphology objects

	but to do that you need: (headword, xrefid, language, lexicalid, session)

	hipparchiaDB=# select * from greek_dictionary limit 0;
	 entry_name | metrical_entry | unaccented_entry | id_number | pos | translations | entry_body
	------------+----------------+------------------+-----------+-----+--------------+------------
	(0 rows)

	p {'prep.', '', 'partic.', 'num. adj.', 'adv. num.', 'v. n.', 'subst.', 'v. dep.', 'adv.', 'pron. adj.', 'p. a.', 'v. freq. a.', 'v. a.', 'adj.'}

	:param listofwords:
	:param partofspeech:
	:return:
	"""

	# cap = 250
	# listofwords = listofwords[:cap]

	mappostodbcategories = {
		'adjective': 'adj.',
		'verb': 'v.',
		'adverb': 'adv.'
	}

	isgreek = re.compile('[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')

	if re.search(isgreek, listofwords[0]):
		language = 'greek'
		objecttemplate = dbColumnorderGreekword
	else:
		language = 'latin'
		objecttemplate = dbColumnorderLatinword

	# print('finding lex')
	# lexicalresults = bulklexicalgrab(listofwords, 'dictionary', 'entry_name', language)
	# lexicalresults = [objecttemplate(*r) for r in lexicalresults]
	# lexicalresults = {r.entry: r for r in lexicalresults}

	# morphobjects = bulkfindmorphologyobjects(listofwords, language)
	# print('finding possibilities')
	# # {religiosus: [<server.hipparchiaobjects.morphologyobjects.MorphPossibilityObject object at 0x14dcf6240>], ...}
	# morphobjects = {m.observed: m.getpossible() for m in morphobjects}
	# declined = [m for m in morphobjects if set([o.isdeclined() for o in morphobjects[m]])]
	# print('declined', declined)

	# lexicalresults = bulklexicalgrab(listofwords, 'dictionary', 'entry_name', language)
	# basewords = [objecttemplate(*r) for r in lexicalresults]
	# xrefsdixt = dict()
	# for b in basewords:
	# 	try:
	# 		xrefsdixt[b.entry] = lemmatadict[b.entry]
	# 	except KeyError:
	# 		print('keyerror on', b.entry)
	# 		pass
	#
	# bmodict = {b.entry: BaseFormMorphology(b.entry, xrefsdixt[b.entry].xref, language, b.id, session, passedlemmataobject=xrefsdixt[b.entry]) for b in basewords}
	#
	# reducedlistofwords = list()
	# for w in listofwords:
	# 	print('analyses', w, bmodict[w].analyses)
	# 	try:
	# 		if bmodict[w].iammostlyconjugated():
	# 			reducedlistofwords.append(w)
	# 	except KeyError:
	# 		print('keyerror on', w)
	#
	# print('reducedlistofwords', reducedlistofwords)

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	morphologyobjecdict = {w: lookformorphologymatches(w, dbcursor) for w in listofwords}
	# {'serius¹': None, 'solacium': <server.hipparchiaobjects.dbtextobjects.dbMorphologyObject object at 0x155362780>, ... }
	possibilitieslistdict = {m: morphologyobjecdict[m].getpossible() for m in morphologyobjecdict if morphologyobjecdict[m]}
	verbpossib = {m for m in possibilitieslistdict if True in [p.isconjugated() for p in possibilitieslistdict[m]]}
	# print('verbpossib', verbpossib)
	nounandadjpossib = {m for m in possibilitieslistdict if True in [p.isdeclined() for p in possibilitieslistdict[m]]}

	dbconnection.connectioncleanup()

	# trimmedlist = set([w for w in listofwords if w in verbpossib])
	trimmedlist = set([w for w in listofwords if w in nounandadjpossib])

	return trimmedlist