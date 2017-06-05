# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Manager, Process
from multiprocessing import Pool
from string import punctuation

from server import hipparchia
from server.dbsupport.dbfunctions import dblineintolineobject, makeablankline, setconnection
from server.formatting.wordformatting import tidyupterm
from server.helperfunctions import setthreadcount
from server.hipparchiaobjects.helperobjects import MPCounter
from server.lexica.lexicalookups import lookformorphologymatches
from server.listsandsession.listmanagement import polytonicsort
from server.textsandindices.textandindiceshelperfunctions import dictmerger


def compilewordlists(worksandboundaries, cursor):
	"""
	grab and return lots of lines
	this is very generic
	typical uses are
		one work + a line range (which may or may not be the whole work: {'work1: (start,stop)}
		multiple (whole) works: {'work1': (start,stop), 'work2': (start,stop), ...}
	but you could one day use this to mix-and-match:
		a completeindex of Thuc + Hdt 3 + all Epic...
	this is, you could use compileauthorandworklist() to feed this function
	the resulting concorances would be massive

	:param worksandboundaries:
	:param cursor:
	:return:
	"""

	lineobjects = []

	for w in worksandboundaries:
		db = w[0:6]
		query = 'SELECT * FROM ' + db + ' WHERE (index >= %s AND index <= %s)'
		data = (worksandboundaries[w][0], worksandboundaries[w][1])
		cursor.execute(query, data)
		lines = cursor.fetchall()

		thiswork = [dblineintolineobject(l) for l in lines]
		lineobjects += thiswork

	return lineobjects


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

	:param work:
	:param startline:
	:param endline:
	:param cursor:
	:return:
	"""

	# print('cdict',cdict)

	onework = False
	if len(cdict) == 1:
		onework = True

	activepoll.allworkis(-1)

	lineobjects = compilewordlists(cdict, cursor)

	pooling = True
	if pooling:
		activepoll.statusis('Compiling the index')
		# 2x as fast to produce the final result; even faster inside the relevant loop
		# the drawback is the problem sending the poll object into the pool
		activepoll.allworkis(-1)
		activepoll.notes = '(progress information unavailable)'
		completeindexdict = pooledindexmaker(lineobjects)
	else:
		activepoll.statusis('Compiling the index')
		activepoll.allworkis(len(lineobjects))
		activepoll.remain(len(lineobjects))
		completeindexdict = linesintoindex(lineobjects, activepoll)

	# completeindexdict: { wordA: [(workid1, index1, locus1), (workid2, index2, locus2),...], wordB: [(...)]}
	# {'illic': [('lt0472w001', 2048, '68A.35')], 'carpitur': [('lt0472w001', 2048, '68A.35')], ...}

	if not headwords:
		activepoll.statusis('Sifting the index')
		activepoll.notes = ''
		activepoll.allworkis(-1)
		unsortedoutput = htmlifysimpleindex(completeindexdict, onework)
		sortkeys = [x[0] for x in unsortedoutput]
		outputdict = {x[0]: x for x in unsortedoutput}
		sortkeys = polytonicsort(sortkeys)
		sortedoutput = [outputdict[x] for x in sortkeys]
		# pad position 0 with a fake, unused headword so that these tuples have the same shape as the ones in the other branch of the condition
		sortedoutput = [(s[0], s[0], s[1], s[2], False) for s in sortedoutput]
	else:

		# [a] find the morphologyobjects needed
		remaining = len(completeindexdict)
		activepoll.statusis('Finding headwords for entries')
		activepoll.notes = '({r} entries found)'.format(r=remaining)

		manager = Manager()
		commitcount = MPCounter()
		terms = manager.list(completeindexdict.keys())
		morphobjects = manager.dict()
		workers = setthreadcount()

		jobs = [Process(target=mpmorphology, args=(terms, morphobjects, commitcount))
		        for i in range(workers)]
		for j in jobs: j.start()
		for j in jobs: j.join()

		activepoll.statusis('Assigning headwords to entries')
		remaining = len(completeindexdict)
		activepoll.notes = '({bf} baseforms found)'.format(bf=remaining)
		activepoll.allworkis(remaining)

		# [b] find the baseforms
		augmentedindexdict = {}
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

		# sample items in an augmentedindexdict
		# erant {'baseforms': 'sum¹', 'homonyms': None, 'loci': [('lt2300w001', 5, '1.4')]}
		# regis {'baseforms': ['rex', 'rego (to keep straight)'], 'homonyms': 2, 'loci': [('lt2300w001', 7, '1.6')]}
		# qui {'baseforms': ['qui¹', 'quis²', 'quis¹', 'qui²'], 'homonyms': 4, 'loci': [('lt2300w001', 7, '1.6'), ('lt2300w001', 4, '1.3')]}

		# [c] remap under the headwords you found

		activepoll.statusis('Remapping entries')
		activepoll.allworkis(-1)
		headwordindexdict = {}

		for observed in augmentedindexdict.keys():
			if augmentedindexdict[observed]['homonyms']:
				tag = 'isahomonymn'
			else:
				tag = False
			augmentedindexdict[observed]['loci'] = [tuple(list(l) + [tag]) for l in
			                                        augmentedindexdict[observed]['loci']]

			if augmentedindexdict[observed]['baseforms']:
				baseforms = augmentedindexdict[observed]['baseforms']
			else:
				baseforms = ['•••unparsed•••']

			for bf in baseforms:
				try:
					headwordindexdict[bf]
				except KeyError:
					headwordindexdict[bf] = {}
				if observed not in headwordindexdict[bf]:
					headwordindexdict[bf][observed] = augmentedindexdict[observed]['loci']
				else:
					for l in augmentedindexdict[observed]['loci']:
						headwordindexdict[bf][observed].append(l)

		# sample items in headwordindexdict
		# 'intersum': {'intersunt': [('lt2300w001', 8, '1.7', False)]}
		# 'populus² (a poplar)': {'populum': [('lt2300w001', 6, '1.5', 'isahomonymn')], 'populi': [('lt2300w001', 1, 't.1', 'isahomonymn')]}
		# 'sum¹': {'est': [('lt2300w001', 7, '1.6', 'isahomonymn')], 'erant': [('lt2300w001', 5, '1.4', False)], 'sunt': [('lt2300w001', 2, '1.1', False)]}

		htmlindexdict = {}
		sortedoutput = []
		for headword in polytonicsort(headwordindexdict.keys()):
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

			for form in polytonicsort(headwordindexdict[headword].keys()):
				hits = sorted(headwordindexdict[headword][form])
				isahomonymn = hits[0][3]
				if onework == True:
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


def mpmorphology(terms, morphobjects, commitcount):
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	while terms:
		try:
			t = terms.pop()
		except IndexError:
			t = None

		if t:

			mo = lookformorphologymatches(t, curs)

			if mo:
				morphobjects[t] = mo
			else:
				morphobjects[t] = None

		commitcount.increment()
		if commitcount.value % hipparchia.config['MPCOMMITCOUNT'] == 0:
			dbconnection.commit()

	dbconnection.commit()

	return morphobjects


def htmlifysimpleindex(completeindexdict, onework):
	"""

	:param completeindexdict:
	:param onework:
	:return:
	"""

	unsortedoutput = []

	for c in completeindexdict.keys():
		hits = completeindexdict[c]
		count = str(len(hits))
		hits = sorted(hits)
		if onework == True:
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


def linesintoindex(lineobjects, activepoll):
	"""
	generate the condordance dictionary:
		{ wordA: [(workid1, index1, locus1), (workid2, index2, locus2),..., wordB: ...]}
		{'illic': [('lt0472w001', 2048, '68A.35')], 'carpitur': [('lt0472w001', 2048, '68A.35')], ...}

	:return:
	"""

	grave = 'ὰὲὶὸὺὴὼῒῢᾲῂῲἃἓἳὃὓἣὣἂἒἲὂὒἢὢ'
	acute = 'άέίόύήώΐΰᾴῄῴἅἕἵὅὕἥὥἄἔἴὄὔἤὤ'
	gravetoacute = str.maketrans(grave, acute)

	extrapunct = '\′‵’‘·̆́“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

	defaultwork = lineobjects[0].wkuinversalid

	completeindex = {}

	while len(lineobjects) > 0:
		try:
			line = lineobjects.pop()
			if activepoll:
				activepoll.remain(len(lineobjects))
		except:
			line = makeablankline(defaultwork, -1)

		if line.index != -1:
			words = line.wordlist('polytonic')
			words = [tidyupterm(w, punct).lower() for w in words]
			words = list(set(words))
			words = [w.translate(gravetoacute) for w in words]
			for w in words:
				try:
					completeindex[w].append((line.wkuinversalid, line.index, line.locus()))
				except:
					completeindex[w] = [(line.wkuinversalid, line.index, line.locus())]

	return completeindex


def pooledindexmaker(lineobjects):
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