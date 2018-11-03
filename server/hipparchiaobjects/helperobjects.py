# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from collections import deque
from itertools import islice
from multiprocessing import Value


class LowandHighInfo(object):
	"""

	mainly just a dict to store results from findvalidlevelvalues()

	more maintainable

	"""

	def __init__(self, levelsavailable, currentlevel, levellabel, low, high, valuerange):
		self.levelsavailable = levelsavailable
		self.currentlevel = currentlevel
		self.levellabel = levellabel
		self.low = low
		self.high = high
		self.valuerange = valuerange


class MPCounter(object):
	"""
	a counter that is mp safe
	"""

	def __init__(self):
		self.val = Value('i', 0)

	def increment(self, n=1):
		with self.val.get_lock():
			self.val.value += n

	@property
	def value(self):
		return self.val.value


class QueryCombinator(object):
	"""

	take a phrase and grab all of the possible searches that you need to catch its line-spanning variants

	x = 'one two three four five'
	z = QueryCombinator(x)
	z.combinationlist()
		[(['one'], ['two', 'three', 'four', 'five']), (['one', 'two'], ['three', 'four', 'five']), (['one', 'two', 'three'], ['four', 'five']), (['one', 'two', 'three', 'four'], ['five']), (['one', 'two', 'three', 'four', 'five'], [])]
	z.combinations()
		[('one', 'two three four five'), ('one two', 'three four five'), ('one two three', 'four five'), ('one two three four', 'five'), ('one two three four five', '')]

	"""
	def __init__(self, phrase):
		self.phrase = phrase
		self.words = [w for w in self.phrase.split(' ') if w]

	@staticmethod
	def _grabhead(n, iterable):
		"""Return first n items of the iterable as a list"""
		return list(islice(iterable, n))

	@staticmethod
	def _grabtail(n, iterable):
		"""Return the last n items of the iterable as a list"""
		return list(deque(iterable, maxlen=n))

	def combinationlist(self):
		"""Return all of the possible pairs of list items"""
		combinations = list()
		for c in range(1, len(self.words) + 1):
			front = self._grabhead(c, self.words)
			back = self._grabtail(len(self.words) - c, self.words)
			combinations.append((front, back))
		return combinations

	def combinations(self):
		"""Return the set of search pairs you will need"""
		cl = self.combinationlist()
		combinations = [(' '.join(c[0]), ' '.join(c[1])) for c in cl]
		return combinations


class LSIVectorCorpus(object):
	"""

	something to hold LSI results

	"""

	def __init__(self, semanticindex, corpustfidf, lsidictionary, lsicorpus, bagsofwords, sentences):
		self.semanticindex = semanticindex
		self.tfidf = corpustfidf
		self.lsidictionary = lsidictionary
		self.lsicorpus = lsicorpus
		self.bagsofwords = bagsofwords
		self.sentences = sentences
		self.semantics = semanticindex[lsicorpus]

	def showtopics(self, numberoftopics):
		return self.semanticindex.print_topics(numberoftopics)

	def findquerylsi(self, query):
		vectorquerybag = self.lsidictionary.doc2bow(query.lower().split())
		vectorquerylsi = self.semanticindex[vectorquerybag]
		return vectorquerylsi


class LogEntropyVectorCorpus(object):
	"""

	something to hold LogEntropy results

	"""

	def __init__(self, lsixform, logentropyxform, logentropydictionary, logentropycorpus, bagsofwords, sentences):
		self.lsixform = lsixform
		self.lexform = logentropyxform
		self.dictionary = logentropydictionary
		self.lsicorpus = logentropycorpus
		self.bagsofwords = bagsofwords
		self.sentences = sentences


