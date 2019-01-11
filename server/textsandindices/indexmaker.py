# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Pool
from string import punctuation
from typing import List

from flask import session

from server import hipparchia
from server.dbsupport.dblinefunctions import grabbundlesoflines, makeablankline
from server.formatting.wordformatting import elidedextrapunct, extrapunct, minimumgreek, tidyupterm
from server.hipparchiaobjects.dbtextobjects import dbWorkLine
from server.listsandsession.genericlistfunctions import polytonicsort
from server.textsandindices.textandindiceshelperfunctions import dictmerger, getrequiredmorphobjects
from server.threading.mpthreadcount import setthreadcount


def buildindextowork(cdict, activepoll, headwords, cursor):
	"""

	speed notes
		a Manager() implementation was 50% slower than single-threaded: lock/unlock penalty on a shared dictionary
		single thread is quite fast: 52s for Eustathius, Commentarii ad Homeri Iliadem [1,099,422 wds]
		a Pool() is 2x as fast as a single thread, but you cannot get polling data from inside the pool

	cdict = {wo.universalid: (startline, endline)}

	just caesar's bellum gallicum: cdict {'lt0448w001': (1, 6192)}
	all of casear's works: cdict {'lt0448w001': (1, 6192), 'lt0448w002': (6193, 10860), 'lt0448w003': (10861, 10891), 'lt0448w004': (10892, 10927), 'lt0448w005': (10928, 10933), 'lt0448w006': (10934, 10944), 'lt0448w007': (10945, 10997), 'lt0448w008': (10998, 11038)}

	the ultimate output needs to look like
		(word, count, citations)

	each item will hit the browser as something like:
		ἀβίωτον | 4 | w028: 246.d.6; w030: 407.a.5, 407.b.1; w034: 926.b.6

	:param cdict:
	:param activepoll:
	:param headwords:
	:param cursor:
	:return:
	"""

	alphabetical = True

	if session['indexbyfrequency'] == 'yes':
		alphabetical = False

	# print('cdict',cdict)

	onework = False
	if len(cdict) == 1:
		onework = True

	activepoll.allworkis(-1)

	lineobjects = grabbundlesoflines(cdict, cursor)

	pooling = True

	if pooling:
		# index to arisotle: 13.336s
		# 2x as fast to produce the final result; even faster inside the relevant loop
		# the drawback is the problem sending the poll object into the pool
		activepoll.statusis('Compiling the index')
		if activepoll.polltype == 'RedisProgressPoll':
			activepoll.allworkis(len(lineobjects))
			activepoll.remain(len(lineobjects))
		else:
			activepoll.allworkis(-1)
			activepoll.setnotes('(progress information unavailable)')
		completeindexdict = pooledindexmaker(lineobjects)
	else:
		# index to aristotle: 28.587s
		activepoll.statusis('Compiling the index')
		activepoll.allworkis(len(lineobjects))
		activepoll.remain(len(lineobjects))
		completeindexdict = linesintoindex(lineobjects, activepoll)

	# completeindexdict: { wordA: [(workid1, index1, locus1), (workid2, index2, locus2),...], wordB: [(...)]}
	# {'illic': [('lt0472w001', 2048, '68A.35')], 'carpitur': [('lt0472w001', 2048, '68A.35')], ...}

	if not headwords:
		activepoll.statusis('Sifting the index')
		activepoll.setnotes('')
		activepoll.allworkis(-1)
		sortedoutput = generatesortedoutputbyword(completeindexdict, onework, alphabetical)
	else:
		sortedoutput = generatesortedoutputbyheadword(completeindexdict, onework, alphabetical, activepoll)

	return sortedoutput


def generatesortedoutputbyword(completeindexdict: dict, onework: bool, alphabetical: bool) -> List[tuple]:
	"""

	the simple case: just spew the index out alphabetically

	:param completeindexdict:
	:param onework:
	:param alphabetical:
	:return:
	"""

	unsortedoutput = htmlifysimpleindex(completeindexdict, onework)
	if alphabetical:
		sortkeys = [x[0] for x in unsortedoutput]
		outputdict = {x[0]: x for x in unsortedoutput}
		sortkeys = polytonicsort(sortkeys)
		sortedoutput = [outputdict[x] for x in sortkeys]
	else:
		sortedoutput = sorted(unsortedoutput, key=lambda x: int(x[1]), reverse=True)
	# pad position 0 with a fake, unused headword so that these tuples have the same shape as the ones in the other branch of the condition
	sortedoutput = [(s[0], s[0], s[1], s[2], False) for s in sortedoutput]

	return sortedoutput


def generatesortedoutputbyheadword(completeindexdict: dict, onework: bool, alphabetical: bool, activepoll) -> List[tuple]:
	"""

	arrange the index by headword

	:return:
	"""

	# [a] find the morphologyobjects needed
	remaining = len(completeindexdict)
	activepoll.statusis('Finding headwords for entries')
	activepoll.setnotes('({r} entries found)'.format(r=remaining))

	morphobjects = getrequiredmorphobjects(completeindexdict.keys())

	activepoll.statusis('Assigning headwords to entries')
	remaining = len(completeindexdict)
	activepoll.setnotes('({bf} baseforms found)'.format(bf=remaining))
	activepoll.allworkis(remaining)

	# [b] find the baseforms
	augmentedindexdict = findindexbaseforms(completeindexdict, morphobjects, activepoll)

	# sample items in an augmentedindexdict
	# erant {'baseforms': 'sum¹', 'homonyms': None, 'loci': [('lt2300w001', 5, '1.4')]}
	# regis {'baseforms': ['rex', 'rego (to keep straight)'], 'homonyms': 2, 'loci': [('lt2300w001', 7, '1.6')]}
	# qui {'baseforms': ['qui¹', 'quis²', 'quis¹', 'qui²'], 'homonyms': 4, 'loci': [('lt2300w001', 7, '1.6'), ('lt2300w001', 4, '1.3')]}

	# [c] remap under the headwords you found

	activepoll.statusis('Remapping entries')
	activepoll.allworkis(-1)

	if hipparchia.config['DELETEUNACCENTEDGREEKFROMINDEX'] == 'yes':
		hasaccent = re.compile(r'[ἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')
		accenteddict = {k: augmentedindexdict[k] for k in augmentedindexdict.keys() if re.search(hasaccent, k)}
		latindict = {k: augmentedindexdict[k] for k in augmentedindexdict.keys() if re.search(r'[a-z]', k)}
		augmentedindexdict = {**accenteddict, **latindict}
		if hipparchia.config['DROPLATININAGREEKINDEX'] == 'yes':
			if len(latindict.keys()) * 5 < len(accenteddict.keys()):
				augmentedindexdict = accenteddict

	if session['indexskipsknownwords'] == 'yes':
		# 'baseforms' is either False or a list
		augmentedindexdict = {k: augmentedindexdict[k] for k in augmentedindexdict.keys() if not augmentedindexdict[k]['baseforms']}

	headwordindexdict = generateheadwordindexdict(augmentedindexdict)

	# [d] format and arrange the output

	if not alphabetical:
		sorter = list()
		for wd in headwordindexdict:
			forms = headwordindexdict[wd]
			allhits = sum([len(forms[f]) for f in forms])
			sorter.append((allhits, wd))
		sorter = sorted(sorter, reverse=True)
		sortedheadwordindexdictkeys = [s[1] for s in sorter if s[1] != '•••unparsed•••']
		sortedheadwordindexdictkeys.append('•••unparsed•••')
	else:
		sortedheadwordindexdictkeys = polytonicsort(headwordindexdict.keys())

	htmlindexdict = dict()
	sortedoutput = list()
	for headword in sortedheadwordindexdictkeys:
		hw = re.sub('v', 'u', headword)
		hw = re.sub('j', 'i', hw)
		sortedoutput.append(('&nbsp;', '', '', '', False))
		if len(headwordindexdict[headword].keys()) > 1:
			formcount = 0
			homonymncount = 0
			for form in headwordindexdict[headword].keys():
				formcount += len(headwordindexdict[headword][form])
				homonymncount += len([x for x in headwordindexdict[headword][form] if x[3]])
			if formcount > 1 and homonymncount > 0:
				sortedoutput.append((hw, '({fc} / {hc})'.format(fc=formcount, hc=homonymncount), '', '', False))
			elif formcount > 1:
				sortedoutput.append((hw, '({fc})'.format(fc=formcount), '', '', False))

		if alphabetical:
			sortedforms = polytonicsort(headwordindexdict[headword].keys())
		else:
			sortedforms = sorted(headwordindexdict[headword].keys(), key=lambda x: len(headwordindexdict[headword][x]), reverse=True)

		for form in sortedforms:
			# print('headwordindexdict[{h}][{f}] = {x}'.format(h=headword, f=form, x=headwordindexdict[headword][form]))
			hits = sorted(headwordindexdict[headword][form])
			isahomonymn = hits[0][3]
			if onework:
				hits = [h[2] for h in hits]
				loci = ', '.join(hits)
			else:
				previouswork = hits[0][0]
				loci = '<span class="work">{wk}</span>: '.format(wk=previouswork[6:10])
				for hit in hits:
					if hit[0] == previouswork:
						loci += hit[2] + ', '
					else:
						loci = loci[:-2] + '; '
						previouswork = hit[0]
						loci += '<span class="work">{wk}</span>: '.format(wk=previouswork[6:10])
						loci += hit[2] + ', '
				loci = loci[:-2]
			htmlindexdict[headword] = loci
			sortedoutput.append(((hw, form, len(hits), htmlindexdict[headword], isahomonymn)))

	return sortedoutput


def findindexbaseforms(completeindexdict, morphobjects, activepoll) -> dict:
	"""

	step [b] for generatesortedoutputbyheadword()

	:param completeindexdict:
	:param morphobjects:
	:param activepoll:
	:return:
	"""

	remaining = len(completeindexdict)

	augmentedindexdict = dict()
	for k in completeindexdict.keys():
		remaining -= 1
		activepoll.remain(remaining)

		try:
			mo = morphobjects[k]
		except KeyError:
			mo = None

		if mo:
			if mo.countpossible() > 1:
				# parsed = list(set(['{bf} ({tr})'.format(bf=p.getbaseform(), tr=p.gettranslation()) for p in mo.getpossible()]))
				parsed = list(set(['{bf}'.format(bf=p.getbaseform()) for p in mo.getpossible()]))
				# cut the blanks
				parsed = [re.sub(r' \( \)', '', p) for p in parsed]
				if len(parsed) == 1:
					homonyms = None
				else:
					homonyms = len(parsed)
			else:
				parsed = [mo.getpossible()[0].getbaseform()]
				homonyms = None
		else:
			parsed = False
			homonyms = None

		augmentedindexdict[k] = {'baseforms': parsed, 'homonyms': homonyms, 'loci': completeindexdict[k]}

	return augmentedindexdict


def generateheadwordindexdict(augmentedindexdict) -> dict:
	"""

	step [c] for generatesortedoutputbyheadword()

	in:

		sample items in an augmentedindexdict
		erant {'baseforms': 'sum¹', 'homonyms': None, 'loci': [('lt2300w001', 5, '1.4')]}
		regis {'baseforms': ['rex', 'rego (to keep straight)'], 'homonyms': 2, 'loci': [('lt2300w001', 7, '1.6')]}
		qui {'baseforms': ['qui¹', 'quis²', 'quis¹', 'qui²'], 'homonyms': 4, 'loci': [('lt2300w001', 7, '1.6'), ('lt2300w001', 4, '1.3')]}

	out:
		sample items in headwordindexdict
		δέ {'δέ': [('gr2586w002', 2184, '<indexedlocation id="gr2586w002_LN_2184">400.31</indexedlocation>', False), ('gr2586w002', 2180, '<indexedlocation id="gr2586w002_LN_2180">400.27</indexedlocation>', False), ('gr2586w002', 2179, '<indexedlocation id="gr2586w002_LN_2179">400.26</indexedlocation>', False), ('gr2586w002', 2178, '<indexedlocation id="gr2586w002_LN_2178">400.25</indexedlocation>', False), ('gr2586w002', 2177, '<indexedlocation id="gr2586w002_LN_2177">400.24</indexedlocation>', False), ('gr2586w002', 2175, '<indexedlocation id="gr2586w002_LN_2175">400.22</indexedlocation>', False), ('gr2586w002', 2174, '<indexedlocation id="gr2586w002_LN_2174">400.21</indexedlocation>', False), ('gr2586w002', 2173, '<indexedlocation id="gr2586w002_LN_2173">400.20</indexedlocation>', False), ('gr2586w002', 2172, '<indexedlocation id="gr2586w002_LN_2172">400.19</indexedlocation>', False), ('gr2586w002', 2171, '<indexedlocation id="gr2586w002_LN_2171">400.18</indexedlocation>', False), ('gr2586w002', 2169, '<indexedlocation id="gr2586w002_LN_2169">400.16</indexedlocation>', False), ('gr2586w002', 2164, '<indexedlocation id="gr2586w002_LN_2164">400.11</indexedlocation>', False), ('gr2586w002', 2162, '<indexedlocation id="gr2586w002_LN_2162">400.9</indexedlocation>', False), ('gr2586w002', 2161, '<indexedlocation id="gr2586w002_LN_2161">400.8</indexedlocation>', False), ('gr2586w002', 2156, '<indexedlocation id="gr2586w002_LN_2156">400.3</indexedlocation>', False)]}
		οἰκεῖοϲ {'οἰκείαϲ': [('gr2586w002', 2184, '<indexedlocation id="gr2586w002_LN_2184">400.31</indexedlocation>', False)], 'οἰκεῖα': [('gr2586w002', 2158, '<indexedlocation id="gr2586w002_LN_2158">400.5</indexedlocation>', False)]}
		μετά {'μετά': [('gr2586w002', 2184, '<indexedlocation id="gr2586w002_LN_2184">400.31</indexedlocation>', False)]}

	:param augmentedindexdict:
	:return:
	"""

	headwordindexdict = dict()

	for observed in augmentedindexdict.keys():
		if augmentedindexdict[observed]['homonyms']:
			tag = 'isahomonymn'
		else:
			tag = False
		augmentedindexdict[observed]['loci'] = [tuple(list(l) + [tag]) for l in augmentedindexdict[observed]['loci']]

		if augmentedindexdict[observed]['baseforms']:
			baseforms = augmentedindexdict[observed]['baseforms']
		else:
			baseforms = ['•••unparsed•••']

		for bf in baseforms:
			try:
				headwordindexdict[bf]
			except KeyError:
				headwordindexdict[bf] = dict()
			if observed not in headwordindexdict[bf]:
				headwordindexdict[bf][observed] = augmentedindexdict[observed]['loci']
			else:
				for l in augmentedindexdict[observed]['loci']:
					headwordindexdict[bf][observed].append(l)

	return headwordindexdict


def htmlifysimpleindex(completeindexdict, onework) -> List[tuple]:
	"""

	:param completeindexdict:
	:param onework:
	:return:
	"""

	unsortedoutput = list()

	for c in completeindexdict.keys():
		hits = completeindexdict[c]
		count = str(len(hits))
		hits = sorted(hits)
		if onework:
			hits = [h[2] for h in hits]
			loci = ', '.join(hits)
		else:
			previouswork = hits[0][0]
			loci = '<span class="work">{wk}</span>: '.format(wk=previouswork[6:10])
			for hit in hits:
				if hit[0] == previouswork:
					loci += hit[2] + ', '
				else:
					loci = loci[:-2] + '; '
					previouswork = hit[0]
					loci += '<span class="work">{wk}</span>: '.format(wk=previouswork[6:10])
					loci += hit[2] + ', '
			loci = loci[:-2]

		unsortedoutput.append((c, count, loci))

	return unsortedoutput


def linesintoindex(lineobjects: List[dbWorkLine], activepoll) -> dict:
	"""
	generate the condordance dictionary:
		{ wordA: [(workid1, index1, locus1), (workid2, index2, locus2),..., wordB: ...]}
		{'illic': [('lt0472w001', 2048, '68A.35')], 'carpitur': [('lt0472w001', 2048, '68A.35')], ...}

	:return:
	"""

	# kill off titles and salutations: dangerous as there l1='t' has not been 100% ruled out as a valid body citation
	# lineobjects = [ln for ln in lineobjects if ln.l1 not in ['t', 'sa']]

	grave = 'ὰὲὶὸὺὴὼῒῢᾲῂῲἃἓἳὃὓἣὣἂἒἲὂὒἢὢ'
	acute = 'άέίόύήώΐΰᾴῄῴἅἕἵὅὕἥὥἄἔἴὄὔἤὤ'
	gravetoacute = str.maketrans(grave, acute)

	# note the tricky combining marks like " ͡ " which can be hard to spot since they float over another special character
	# τ’ and δ’ and the rest are a problem

	greekpunct = re.compile('[{s}]'.format(s=re.escape(punctuation + elidedextrapunct)))
	latinpunct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

	defaultwork = lineobjects[0].wkuinversalid

	completeindex = dict()

	# clickable entries will break after too many words. Toggle bewteen indexing methods by guessing N words per line and
	# then pick 'locus' when you have too many lineobjects: a nasty hack
	# a RangeError arises from jquery trying to push too many items onto its stack?
	# in which case if you had 32k indexlocationa and then indexlocationb and then ... you could avoid this?
	# pretty hacky, but it might work; then again, jquery might die after N of any kind not just N of a specific kind

	if len(lineobjects) < hipparchia.config['CLICKABLEINDEXEDPASSAGECAP'] or hipparchia.config['CLICKABLEINDEXEDPASSAGECAP'] < 0:
		# [a] '<indexedlocation id="gr0032w008_LN_31011">2.17.6</indexedlocation>' vs [b] just '2.17.6'
		indexingmethod = 'anchoredlocus'
	elif session['indexskipsknownwords'] == 'yes':
		indexingmethod = 'anchoredlocus'
	else:
		indexingmethod = 'locus'

	while lineobjects:
		try:
			line = lineobjects.pop()
			if activepoll:
				activepoll.remain(len(lineobjects))
		except IndexError:
			line = makeablankline(defaultwork, None)

		if line.index:
			# don't use set() - that will yield undercounts
			polytonicwords = line.wordlist('polytonic')
			polytonicgreekwords = [tidyupterm(w, greekpunct).lower() for w in polytonicwords if re.search(minimumgreek, w)]
			polytoniclatinwords = [tidyupterm(w, latinpunct).lower() for w in polytonicwords if not re.search(minimumgreek, w)]
			polytonicwords = polytonicgreekwords + polytoniclatinwords
			# need to figure out how to grab τ’ and δ’ and the rest
			# but you can't decide that me is elided in a line like 'inquam, ‘teque laudo. sed quando?’ ‘nihil ad me’ inquit ‘de'
			unformattedwords = set(line.wordlist('marked_up_line'))
			words = [w for w in polytonicwords if w+'’' not in unformattedwords or not re.search(minimumgreek, w)]
			elisions = [w+"'" for w in polytonicwords if w+'’' in unformattedwords and re.search(minimumgreek, w)]
			words.extend(elisions)
			words = [w.translate(gravetoacute) for w in words]
			for w in words:
				referencestyle = getattr(line, indexingmethod)
				try:
					completeindex[w].append((line.wkuinversalid, line.index, referencestyle()))
				except KeyError:
					completeindex[w] = [(line.wkuinversalid, line.index, referencestyle())]

	return completeindex


def pooledindexmaker(lineobjects: List[dbWorkLine]) -> dict:
	"""

	split up the line objects and dispatch them into an mp pool

	each thread will generate a dict

	then merge the result dicts into a master dict

	return the masterdict

	:param lineobjects:
	:return: masterdict
	"""

	workers = setthreadcount()

	if len(lineobjects) > 100 * workers:
		# if you have only 2 lines of an author and 5 workers how will you divide the author up?
		chunksize = int(len(lineobjects) / workers) + 1
		chunklines = [lineobjects[i:i + chunksize] for i in range(0, len(lineobjects), chunksize)]
	else:
		chunklines = [lineobjects]

	# polling does not really work
	# RuntimeError: Synchronized objects should only be shared between processes through inheritance
	# Manager() can do this but Pool() can't
	thereisapoll = False

	argmap = [(c, thereisapoll) for c in chunklines]

	with Pool(processes=int(workers)) as pool:
		listofcompleteindexdicts = pool.starmap(linesintoindex, argmap)

	masterdict = listofcompleteindexdicts.pop()

	while listofcompleteindexdicts:
		tomerge = listofcompleteindexdicts.pop()
		masterdict = dictmerger(masterdict, tomerge)

	return masterdict
