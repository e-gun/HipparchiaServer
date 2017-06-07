# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time
from collections import deque
from itertools import islice
from multiprocessing import Value, Array

from server import hipparchia


class SearchResult(object):
	"""

	really just a more maintainable version of a dict

	"""
	def __init__(self, hitnumber, author, work, citationstring, clickurl, lineobjects):
		self.hitnumber = hitnumber
		self.author = author
		self.work = work
		self.citationstring = citationstring
		self.clickurl = clickurl
		self.lineobjects = lineobjects

	def getindex(self):
		"""

		fetch the index value of the focus line

		derive it from the tail of the clickurl, e.g.:

			lt1002w002_LN_24040

		:return:
		"""

		return int(self.clickurl.split('_')[-1])


	def getlocusthml(self):
		"""
		generate the wrapped html for the citation; e.g:
			<locus>
				<span class="findnumber">[13]</span>&nbsp;&nbsp;<span class="foundauthor">Quintilianus, Marcus Fabius</span>,&nbsp;<span class="foundwork">Declamationes Minores</span>:
				<browser id="lt1002w002_LN_24040"><span class="foundlocus">oration 289, section pr, line 1</span><br /></browser>
			</locus>
		:return: 
		"""

		locushtml = '<locus>\n{cit}</locus><br />\n'.format(cit=self.citationhtml(self.citationstring))

		return locushtml

	def citationhtml(self, citestring):
		"""

		generate the non-wrapped html for the citation; e.g:

			<span class="findnumber">[13]</span>&nbsp;&nbsp;<span class="foundauthor">Quintilianus, Marcus Fabius</span>,&nbsp;<span class="foundwork">Declamationes Minores</span>:
			<browser id="lt1002w002_LN_24040"><span class="foundlocus">oration 289, section pr, line 1</span><br /></browser>

		:return:
		"""

		citationtemplate = """
			<span class="findnumber">[{hn}]</span>&nbsp;&nbsp;
			<span class="foundauthor">{au}</span>,&nbsp;
			<span class="foundwork">{wk}</span>:
			<browser id="{url}"><span class="foundlocus">{cs}</span></browser>"""

		locushtml = citationtemplate.format(hn=self.hitnumber, au=self.author, wk=self.work, url=self.clickurl,
		                             cs=citestring)

		return locushtml


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


class ProgressPoll(object):
	"""
	
	a dictionary of Values that can be shared between processes
	the items and their methods build a polling package for progress reporting
	
	general scheme:
		create the object
		set up some shareable variables
		hand them to the search functions
		report on their fate
		delete when done
	
	locking checks mostly unimportant: not esp worried about race conditions; most of this is simple fyi
	"""

	polltcpport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	def __init__(self, timestamp, portnumber=polltcpport):
		self.searchid = str(timestamp)
		self.launchtime = time.time()
		self.portnumber = portnumber
		self.active = Value('b', False)
		self.remaining = Value('i', -1)
		self.poolofwork = Value('i', -1)
		self.statusmessage = Array('c', b'')
		self.hitcount = MPCounter()
		self.hitcount.increment(-1)
		self.notes = ''

	def getstatus(self):
		return self.statusmessage.decode('utf-8')

	def getelapsed(self):
		elapsed = round(time.time() - self.launchtime, 0)
		return elapsed

	def getremaining(self):
		return self.remaining.value

	def gethits(self):
		return self.hitcount.value

	def worktotal(self):
		return self.poolofwork.value

	def statusis(self, statusmessage):
		self.statusmessage = bytes(statusmessage, encoding='UTF-8')

	def allworkis(self, amount):
		self.poolofwork.value = amount

	def remain(self, remaining):
		with self.remaining.get_lock():
			self.remaining.value = remaining

	def sethits(self, found):
		self.hitcount.val.value = found

	def addhits(self, hits):
		self.hitcount.increment(hits)

	def activate(self):
		self.active = True

	def deactivate(self):
		self.active = False

	def getactivity(self):
		return self.active

	def getnotes(self):
		message = '<span class="small">{msg}</span>'
		if 14 < self.getelapsed() < 21:
			m = '(long requests can be aborted by reloading the page)'
		elif re.search('unavailable', self.notes) and 9 < self.getelapsed() < 15:
			m = self.notes
		elif re.search('unavailable', self.notes) is None:
			m = self.notes
		else:
			m = ''

		return message.format(msg=m)


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

	def take(self, n, iterable):
		"""Return first n items of the iterable as a list"""
		return list(islice(iterable, n))

	def tail(self, n, iterable):
		"""Return the last n items of the iterable as a list"""
		return list(deque(iterable, maxlen=n))

	def combinationlist(self):
		"""Return all of the possible pairs of list items"""
		combinations = []
		for c in range(1, len(self.words) + 1):
			front = self.take(c, self.words)
			back = self.tail(len(self.words) - c, self.words)
			combinations.append((front, back))
		return combinations

	def combinations(self):
		"""Return the set of search pairs you will need"""
		cl = self.combinationlist()
		combinations = [(' '.join(c[0]), ' '.join(c[1])) for c in cl]
		return combinations


class SearchObject(object):
	"""

	an object that can be passed around to the various search functions
	it knows about the query, the session, etc.

	"""

	def __init__(self, ts, seeking, proximate, frozensession):
		self.ts = ts

		self.originalseeking = seeking
		self.originalproximate = proximate

		# searchtermcharactersubstitutions() logic has moved here

		seeking = re.sub('[σς]', 'ϲ', seeking)
		seeking = re.sub(r'\\ϲ', ' ', seeking)
		seeking = re.sub(r'^\s', '(^|\s)', seeking)
		seeking = re.sub(r'\s$', '(\s|$)', seeking)
		seeking = seeking.lower()
		proximate = re.sub('[σς]', 'ϲ', proximate)
		proximate = re.sub(r'\\ϲ', ' ', proximate)
		proximate = re.sub(r'^\s', '(^|\s)', proximate)
		proximate = re.sub(r'\s$', '(\s|$)', proximate)
		proximate = proximate.lower()

		# print ('seeking,proximate',seeking,proximate)

		# session['accentsmatter'] logic has been transferred to here

		accented = '[äëïöüâêîôûàèìòùáéíóúᾂᾒᾢᾃᾓᾣᾄᾔᾤᾅᾕᾥᾆᾖᾦᾇᾗᾧἂἒἲὂὒἢὢἃἓἳὃὓἣὣἄἔἴὄὔἤὤἅἕἵὅὕἥὥἆἶὖἦὦἇἷὗἧὧᾲῂῲᾴῄῴᾷῇῷᾀᾐᾠᾁᾑᾡῒῢΐΰῧἀἐἰὀὐἠὠῤἁἑἱὁὑἡὡῥὰὲὶὸὺὴὼάέίόύήώᾶῖῦῆῶϊϋ]'

		if re.search(accented, seeking) or re.search(accented, proximate):
			# alternate:
			#   if frozensession['accentsmatter'] == 'yes':
			self.accented = True
			# the following can be counted upon to slow down searches, but not relatively few searches will be affected and not grievously
			seeking = re.sub('v', '[vu]', seeking)
			seeking = re.sub('j', '[ji]', seeking)
			proximate = re.sub('v', '[vu]', proximate)
			proximate = re.sub('j', '[ji]', proximate)
		else:
			self.accented = False
			seeking = re.sub('v', 'u', seeking)
			seeking = re.sub('j', 'i', seeking)
			proximate = re.sub('v', 'u', proximate)
			proximate = re.sub('j', 'i', proximate)

		self.seeking = seeking
		self.proximate = proximate

		self.session = frozensession
		self.proximity = frozensession['proximity']
		self.psgselections = frozensession['psgselections']
		self.psgexclusions = frozensession['psgexclusions']
		self.context = int(frozensession['linesofcontext'])
		if len(seeking) < len(proximate):
			self.longterm = proximate
			self.shorterm = seeking
		else:
			self.longterm = seeking
			self.shorterm = proximate

		# modification or swapping of seeing/proximate mean you want
		# other holders for what you actually search for
		self.termone = seeking
		self.termtwo = proximate
		self.leastcommon = None
		self.searchtype = None
		self.searchlist = []
		self.indexrestrictions = {}

		if self.accented:
			self.usecolumn = 'accented_line'
			self.usewordlist = 'polytonic'
		else:
			self.usecolumn = 'stripped_line'
			self.usewordlist = 'stripped'

		if frozensession['searchscope'] == 'W':
			self.scope = 'words'
		else:
			self.scope = 'lines'

		if frozensession['nearornot'] == 'T':
			self.near = True
			self.nearstr = ''
		else:
			self.near = False
			self.nearstr = ' not'

		self.cap = int(frozensession['maxresults'])

		if frozensession['onehit'] == 'yes':
			self.onehit = True
		else:
			self.onehit = False

		self.distance = int(frozensession['proximity'])