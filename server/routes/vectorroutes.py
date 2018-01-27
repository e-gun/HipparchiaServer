# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import re
import time

from flask import session

from server import hipparchia
from server.formatting.bibliographicformatting import bcedating
from server.formatting.wordformatting import buildhipparchiatranstable, removegravity, stripaccents
from server.hipparchiaobjects.helperobjects import ProgressPoll, SearchObject
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.sessionfunctions import sessionvariables
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.vectordispatcher import findheadwords, vectordispatching
from server.semanticvectors.vectorhelpers import buildvectorspace, caclulatecosinevalues, mostcommonwords
from server.startup import authordict, lemmatadict, listmapper, poll, workdict

"""
	THE MATH

	http://www.puttypeg.net/papers/vector-chapter.pdf

	see esp pp. 155-58 on cosine similarity:
	
		cos(α,β) = α · β / ||α|| ||β||
	
	||α|| = sqrt(α · α)
	
	and α = sum([a1, a2, ... ai])

	1 = most related
	0 = unrelated

"""

"""	
	OVERVIEW OF THE IDEAL PROCESS
	
	[a] find all forms of X
	[b] find all words in the same sentence as X
	[c] calculate values for the most common neighbors of X where these values describe the degree of relatedness
	[d] calculate similar values that relate those same neighbors to one another
	[e] graph the results.
	
"""


@hipparchia.route('/findvectors', methods=['GET'])
def findvectors(searchitem=None, vtype='lemma'):
	"""

	use the searchlist to grab a collection of passages

	[or is it better to do this via the text boxes...? you will never be able to do "all of medicine" that way, though]

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""

	starttime = time.time()

	ts = str(int(time.time()))

	# we are not really a route at the moment, but instead being called by execute search
	# when the Δ option is checked; hence the commenting out of the following
	# lemma = cleaninitialquery(request.args.get('lem', ''))

	lemma = None
	seeking = ''

	if vtype == 'string':
		seeking = searchitem
	else:
		try:
			lemma = lemmatadict[searchitem]
		except KeyError:
			pass

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	searchlist = list()
	reasons = list()
	output = ''
	nosearch = True

	proximate = ''
	proximatelemma = ''
	sessionvariables()
	frozensession = session.copy()

	dmin, dmax = bcedating(frozensession)

	so = SearchObject(ts, seeking, proximate, lemma, proximatelemma, frozensession)
	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if frozensession[c] == 'yes']

	if (lemma or seeking) and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, frozensession)

	# make sure you don't go nuts
	maxwords = hipparchia.config['MAXVECTORSPACE']
	wordstotal = 0
	for work in searchlist:
		work = work[:10]
		try:
			wordstotal += workdict[work].wordcount
		except TypeError:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass

	if wordstotal > maxwords:
		searchlist = list()
		reasons.append('the vector scope max exceeded: {a} > {b} '.format(a=locale.format('%d', wordstotal, grouping=True), b=locale.format('%d', maxwords, grouping=True)))

	# DEBUGGING
	# Frogs and mice
	# so.lemma = lemmatadict['βάτραχοϲ']
	# searchlist = ['gr1220']
	#
	# # Hippocrates
	# """
	# Sought all 6 known forms of »εὕρηϲιϲ«
	# Searched 57 texts and found 35 passages (0.25s)
	# Sorted by name
	# """
	# so.lemma = lemmatadict['εὕρηϲιϲ']
	# searchlist = ['gr0627']
	#
	# # Galen
	# """
	# Sought all 6 known forms of »εὕρηϲιϲ«
	# Searched 110 texts and found 296 passages (0.93s)
	# Sorted by name
	#
	# Sought all 9 known forms of »εὕρεϲιϲ«
	# Searched 110 texts and found 288 passages (0.59s)
	# Sorted by name
	#
	# """
	#
	# so.lemma = lemmatadict['εὕρεϲιϲ']
	# so.lemma.formlist = list(set(lemmatadict['εὕρεϲιϲ'].formlist + lemmatadict['εὕρηϲιϲ'].formlist))
	# searchlist = ['gr0057']
	#
	# so.lemma = lemmatadict['παραλείπω']

	# Euripides
	# so.lemma = lemmatadict['ἄτη']
	# print(so.lemma.formlist)
	# so.lemma.formlist = ['ἄτῃ', 'ἄταν', 'ἄτηϲ', 'ἄτηι']
	# searchlist = ['gr0006']

	# Vergil
	# so.lemma = lemmatadict['flos']
	# searchlist = ['lt0690']

	if len(searchlist) > 0:
		nosearch = False
		searchlist = flagexclusions(searchlist, frozensession)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# find all sentences
		activepoll.statusis('Finding all sentences')
		sentences = vectordispatching(so, activepoll)

		# find all words in use
		allwords = [s.split(' ') for s in sentences]
		# flatten
		allwords = [item for sublist in allwords for item in sublist]

		minimumgreek = re.compile('[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')
		greekwords = [w for w in allwords if re.search(minimumgreek, w)]

		trans = buildhipparchiatranstable()
		latinwords = [w for w in allwords if not re.search(minimumgreek, w)]

		allwords = [removegravity(w) for w in greekwords] + [stripaccents(w, trans) for w in latinwords]
		allwords = set(allwords) - {''}

		# find all possible forms of all the words we used
		# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
		activepoll.statusis('Finding headwords')
		morphdict = findheadwords(allwords, activepoll)
		morphdict = {k: v for k, v in morphdict.items() if v is not None}
		morphdict = {k: set([p.getbaseform() for p in morphdict[k].getpossible()]) for k in morphdict.keys()}

		# {'θεῶν': {'θεόϲ', 'θέα', 'θεάω', 'θεά'}, 'πώ': {'πω'}, 'πολλά': {'πολύϲ'}, 'πατήρ': {'πατήρ'}, ... }

		# over-aggressive? more thought/care might be required here
		delenda = mostcommonwords()
		morphdict = {k: v for k, v in morphdict.items() if v - delenda == v}

		# find all possible headwords of all of the forms in use
		# note that we will not know what we did not know: count unparsed words too and deliver that as info at the end?
		allheadwords = dict()
		for m in morphdict.keys():
			for h in morphdict[m]:
				allheadwords[h] = m

		activepoll.statusis('Building vectors')
		vectorspace = buildvectorspace(allheadwords, morphdict, sentences, focusterm=seeking)

		# for k in vectorspace.keys():
		# 	print(k, vectorspace[k])

		activepoll.statusis('Calculating cosine distances')
		if lemma:
			focus = so.lemma.dictionaryentry
		else:
			focus = seeking

		cosinevalues = caclulatecosinevalues(focus, vectorspace, allheadwords.keys())

		# apply the threshold and drop the 'None' items
		threshold = 1.0 - hipparchia.config['VECTORDISTANCECUTOFF']
		cosinevalues = {c: cosinevalues[c] for c in cosinevalues if cosinevalues[c] and cosinevalues[c] < threshold}

		# now we have the relationship of everybody to our lemmatized word

		# print('CORE COSINE VALUES')
		# for v in polytonicsort(cosinevalues):
		# 	print(v, cosinevalues[v])
		ccv = [(cosinevalues[v], v) for v in cosinevalues]
		ccv = sorted(ccv, key=lambda t: t[0])
		ccv = ['\t{a}\t{b}'.format(a=round(c[0],3), b=c[1]) for c in ccv]
		ccv = '\n'.join(ccv)

		# next we look for the interrelationships of the words that are above the threshold
		metacosinevals = dict()
		metacosinevals[focus] = cosinevalues
		for v in cosinevalues:
			metac = caclulatecosinevalues(v, vectorspace, cosinevalues.keys())
			metac = {c: metac[c] for c in metac if metac[c] and metac[c] < threshold}
			metacosinevals[v] = metac

		# for headword in polytonicsort(metacosinevals.keys()):
		# 	print(headword)
		# 	for word in metacosinevals[headword]:
		# 		print('\t', word, metacosinevals[headword][word])

		findshtml = '<pre>{ccv}</pre>'.format(ccv=ccv)
		nosearch = False

	if not nosearch:
		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)
		workssearched = locale.format('%d', workssearched, grouping=True)

		output = dict()
		output['title'] = 'Cosine distances to »{skg}«'.format(skg=focus)
		output['found'] = findshtml
		# ultimately the js should let you clock on any top word to find its associations...
		output['js'] = ''
		output['resultcount'] = '{c} related terms in {s} sentences'.format(c=len(cosinevalues), s=len(sentences))
		output['scope'] = workssearched
		output['searchtime'] = str(searchtime)
		output['proximate'] = ''
		if lemma:
			xtra = 'all forms of '
		else:
			xtra = ''
		output['thesearch'] = '{x}»{skg}«'.format(x=xtra, skg=focus)
		output['htmlsearch'] = '{x}<span class="sought">»{skg}«</span>'.format(x=xtra, skg=focus)
		output['hitmax'] = ''
		output['onehit'] = ''
		output['sortby'] = 'distance with a cutoff of {c}'.format(c=1-hipparchia.config['VECTORDISTANCECUTOFF'])
		output['dmin'] = dmin
		output['dmax'] = dmax
		activepoll.deactivate()

	if nosearch:
		if not activecorpora:
			reasons.append('there are no active databases')
		if not (lemma or seeking):
			reasons.append('no search term was provided')
		if len(searchlist) == 0:
			reasons.append('no works in the searchlist')
		output = dict()
		output['title'] = '(empty query)'
		output['found'] = ''
		output['resultcount'] = 0
		output['scope'] = 0
		output['searchtime'] = '0.00'
		output['proximate'] = proximate
		output['thesearch'] = ''
		output['htmlsearch'] = '<span class="emph">nothing</span> (search not executed because {r})'.format(r=' and '.join(reasons))
		output['hitmax'] = 0
		output['dmin'] = dmin
		output['dmax'] = dmax
		output['sortby'] = frozensession['sortorder']
		output['onehit'] = frozensession['onehit']

	output = json.dumps(output)

	del poll[ts]

	return output