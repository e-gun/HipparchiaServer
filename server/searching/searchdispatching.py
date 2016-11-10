from multiprocessing import Manager, Process

from server import hipparchia
from server.dbsupport.dbfunctions import dblineintolineobject
from server.hipparchiaclasses import MPCounter
from server.searching.searchformatting import sortandunpackresults
from server.searching.phrasesearching import shortphrasesearch
from server.searching.workonsearch import workonsimplesearch, workonphrasesearch, workonproximitysearch

def searchdispatcher(searchtype, seeking, proximate, indexedauthorandworklist, authordict, activepoll):
	"""
	assign the search to multiprocessing workers
	:param seeking:
	:param indexedauthorandworklist:
	:return:
	"""
	
	activepoll.allworkis(len(indexedauthorandworklist))
	activepoll.remain(len(indexedauthorandworklist))
	activepoll.sethits(0)
	
	count = MPCounter()
	manager = Manager()
	hits = manager.dict()
	authors = manager.dict(authordict)
	searching = manager.list(indexedauthorandworklist)
	
	# if you don't autocommit you will soon see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	
	# a class and/or decorator would be nice, but you have a lot of trouble getting the (mp aware) args into the function
	# the must be a way, but this also works
	if searchtype == 'simple':
		activepoll.statusis('Executing a simple word search...')
		jobs = [Process(target=workonsimplesearch, args=(count, hits, seeking, searching, commitcount, authors, activepoll)) for i in range(workers)]
	elif searchtype == 'phrase':
		activepoll.statusis('Executing a phrase search. Checking longest term first...')
		jobs = [Process(target=workonphrasesearch, args=(hits, seeking, searching, commitcount, authors, activepoll)) for i in range(workers)]
	elif searchtype == 'proximity':
		activepoll.statusis('Executing a proximity search...')
		jobs = [Process(target=workonproximitysearch, args=(count, hits, seeking, proximate, searching, commitcount, authors, activepoll)) for i in range(workers)]
	else:
		# impossible, but...
		jobs = []
		
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	# what comes back is a dict: {sortedawindex: (wkid, [(result1), (result2), ...])}
	# you need to sort by index and then unpack the results into a list
	# this will restore the old order from sortauthorandworklists()
	hits = sortandunpackresults(hits)
	lineobjects = []
	for h in hits:
		# hit= ('gr0199w012', (842, '-1', '-1', '-1', '-1', '5', '41', 'Πυθῶνί τ’ ἐν ἀγαθέᾳ· ', 'πυθωνι τ εν αγαθεα ', '', ''))
		lineobjects.append(dblineintolineobject(h[0],h[1]))
	
	return lineobjects


def dispatchshortphrasesearch(searchphrase, indexedauthorandworklist, authors, activepoll):
	"""
	brute force a search for something horrid like και δη και
	a set of short words should send you here, otherwise you will look up all the words that look like και and then...
	:param searchphrase:
	:param cursor:
	:param wkid:
	:return:
	"""
	
	activepoll.allworkis(len(indexedauthorandworklist))
	activepoll.remain(len(indexedauthorandworklist))
	activepoll.sethits(0)
	activepoll.statusis('Executing a short-phrase search...')
		
	count = MPCounter()
	manager = Manager()
	hits = manager.dict()
	workstosearch = manager.list(indexedauthorandworklist)
	# if you don't autocommit you will see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	
	jobs = [Process(target=shortphrasesearch, args=(count, hits, searchphrase, workstosearch, authors, activepoll)) for i in range(workers)]
	
	for j in jobs: j.start()
	for j in jobs: j.join()
			
	hits = sortandunpackresults(hits)
	# hits = [('gr0059w002', <server.hipparchiaclasses.dbWorkLine object at 0x10b0bb358>), ...]

	lineobjects = []
	for h in hits:
		lineobjects.append(h[1])
	
	return lineobjects