# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
import redis
import time
from multiprocessing import Array, Value

from server import hipparchia
from server.formatting.bibliographicformatting import bcedating
from server.formatting.wordformatting import avoidsmallvariants
from server.hipparchiaobjects.helperobjects import MPCounter
from server.listsandsession.sessionfunctions import justlatin


class SearchResult(object):
	"""

	really just a more maintainable version of a dict

	"""
	def __init__(self, hitnumber, author, work, citationstring, clickurl, lineobjects):
		self.hitnumber = hitnumber
		self.author = avoidsmallvariants(author)
		self.work = avoidsmallvariants(work)
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

	def getworkid(self):
		"""

		fetch the wkuniversalid value of the focus line

		derive it from the tail of the clickurl, e.g.:

			lt1002w002_LN_24040

		:return:
		"""

		return self.clickurl[0:10]

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
			<span class="foundauthor">{au}</span>,&nbsp;<span class="foundwork">{wk}</span>:
			<browser id="{url}"><span class="foundlocus">{cs}</span></browser>"""

		locushtml = citationtemplate.format(hn=self.hitnumber, au=self.author, wk=self.work, url=self.clickurl,
		                             cs=citestring)

		return locushtml


class SearchObject(object):
	"""

	an object that can be passed around to the various search functions
	it knows about the query, the session, etc.

	"""

	def __init__(self, ts, seeking, proximate, lemmaobject, proximatelemmaobject, frozensession):
		self.ts = ts

		self.originalseeking = seeking
		self.originalproximate = proximate
		self.lemma = lemmaobject
		self.proximatelemma = proximatelemmaobject

		# '>' will mess you up still
		self.originalseeking = re.sub(r'<', '&lt;', self.originalseeking)
		self.originalseeking = re.sub(r'>', '&gt;', self.originalseeking)
		self.originalproximate = re.sub(r'<', '&lt;', self.originalproximate)
		self.originalproximate = re.sub(r'>', '&gt;', self.originalproximate)
		self.vectortype = None
		self.tovectorize = None
		self.vectorquerytype = None
		self.starttime = time.time()
		self.usedcorpora = list()
		self.sentencebundlesize = hipparchia.config['SENTENCESPERDOCUMENT']
		self.poll = None

		# searchtermcharactersubstitutions() logic has moved here

		seeking = re.sub('[σς]', 'ϲ', seeking)
		seeking = re.sub(r'\\ϲ', ' ', seeking)
		seeking = re.sub(r'^\s', r'(^|\s)', seeking)
		seeking = re.sub(r'\s$', r'(\s|$)', seeking)
		seeking = seeking.lower()
		proximate = re.sub('[σς]', 'ϲ', proximate)
		proximate = re.sub(r'\\ϲ', ' ', proximate)
		proximate = re.sub(r'^\s', r'(^|\s)', proximate)
		proximate = re.sub(r'\s$', r'(\s|$)', proximate)
		proximate = proximate.lower()

		# print ('seeking,proximate',seeking,proximate)

		# session['accentsmatter'] logic has been transferred to here

		accented = '[äëïöüâêîôûàèìòùáéíóúᾂᾒᾢᾃᾓᾣᾄᾔᾤᾅᾕᾥᾆᾖᾦᾇᾗᾧἂἒἲὂὒἢὢἃἓἳὃὓἣὣἄἔἴὄὔἤὤἅἕἵὅὕἥὥἆἶὖἦὦἇἷὗἧὧᾲῂῲᾴῄῴᾷῇῷᾀᾐᾠᾁᾑᾡῒῢΐΰῧἀἐἰὀὐἠὠῤἁἑἱὁὑἡὡῥὰὲὶὸὺὴὼάέίόύήώᾶῖῦῆῶϊϋ]'

		if re.search(accented, seeking) or re.search(accented, proximate):
			self.accented = True
			# the following can be counted upon to slow down searches, but relatively few searches will be
			# affected and not grievously
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
		self.searchlist = list()
		self.indexrestrictions = dict()

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

	def getactivecorpora(self):
		allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
		activecorpora = [c for c in allcorpora if self.session[c] == 'yes']
		return activecorpora

	def infervectorquerytype(self):
		exclusive = {'cosdistbysentence', 'cosdistbysentence', 'semanticvectorquery', 'nearestneighborsquery',
		             'tensorflowgraph', 'sentencesimilarity', 'topicmodel'}

		qtype = list()
		for e in exclusive:
			if self.session[e] == 'yes':
				qtype.append(e)

		if len(qtype) > 1:
			# obviously we should never see this unless there is a bug in sessionfunctions.py, vel sim.
			print('error: too many query types have been set:', qtype)
			return None
		else:
			try:
				return qtype[0]
			except IndexError:
				return None

	def getelapsedtime(self):
		return str(round(time.time() - self.starttime, 2))

	def fullcorpussearch(self, corpus):
		# this is a cheat that assumes a static body of texts
		# sql check is: 'SELECT COUNT(universalid) FROM authors WHERE universalid LIKE 'dp%';'
		corpora = {
			'lt': 362,
			'gr': 1823,
			'ch': 291,
			'in': 463,
			'dp': 516
		}

		assert corpus in corpora, 'SearchObject.fullcorpussearch() was sent a corpus not in known corpora'

		test = [x for x in self.searchlist if x[:2] == corpus and len(x) == 6]
		if len(test) == corpora[corpus]:
			return True
		else:
			return False

	def wholecorporasearched(self):
		# note that the searchroute.py searchlist might be empty by the time you check this: searchlist.pop()
		corpora = {
			'lt': 'Latin',
			'gr': 'Greek',
			'ch': 'Christian',
			'in': 'Inscriptional',
			'dp': 'Papyrus'
		}

		whole = list()
		for c in corpora:
			if self.fullcorpussearch(c):
				whole.append(corpora[c])

		return whole

	def numberofauthorssearched(self):
		authors = set([a[:6] for a in self.searchlist])
		return len(authors)


class SearchOutputObject(object):
	"""

	basically a dict to help hold and format the html output of a search

	"""

	def __init__(self, searchobject):
		self.title = str()
		self.found = str()
		self.js = str()
		self.resultcount = str()
		self.scope = '0'
		self.searchtime = '0.00'
		self.proximate = searchobject.proximate
		self.thesearch = str()
		self.htmlsearch = str()
		self.hitmax = 'false'
		self.onehit = searchobject.session['onehit']
		self.usedcorpora = searchobject.usedcorpora

		self.icandodates = 'no'
		if justlatin(searchobject.session) is False:
			self.icandodates = 'yes'

		sortorderdecoder = {
			'universalid': 'ID',
			'shortname': 'name',
			'genres': 'author genre',
			'converted_date': 'date',
			'location': 'location'
		}
		self.sortby = sortorderdecoder[searchobject.session['sortorder']]

		# currently unused
		if searchobject.lemma:
			self.lemma = searchobject.lemma.dictionaryentry
		else:
			self.lemma = ''

		if searchobject.termone:
			self.headword = searchobject.termone
		else:
			self.headword = ''

		dmin, dmax = bcedating(searchobject.session)
		self.dmin = dmin
		self.dmax = dmax

		self.image = str()
		self.reasons = list()

	def generateoutput(self):
		outputdict = dict()
		for item in vars(self):
			outputdict[item] = getattr(self, item)
		return outputdict

	def setresultcount(self, value, string):
		rc = '{:,}'.format(value)
		self.resultcount = '{r} {s}'.format(r=rc, s=string)

	def setscope(self, value):
		self.scope = '{:,}'.format(value)
		if self.usedcorpora:
			w = ' and '.join(self.usedcorpora)
			self.scope = 'all {w} authors in {s}'.format(w=w, s=self.scope)

	def explainemptysearch(self):
		r = ' and '.join(self.reasons)
		self.htmlsearch = '<span class="emph">nothing</span> (search not executed because {r})'.format(r=r)


class SharedMemoryProgressPoll(object):
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

	def setnotes(self, message):
		self.notes = message

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


class RedisProgressPoll(object):
	"""

	a dictionary of Values that can be shared between processes
	the items and their methods build a polling package for progress reporting

	general scheme:
		create the object
		set up some shareable variables
		hand them to the search functions
		report on their fate
		delete when done

	the interface is rather baroque because the underlying simple mechanism was late in arriving

	HSET is tempting instead of SET...

	note that you should not request things like self.poolofwork: it will not be accurate after initialization
		self.worktotal(), etc. are how you get the real values

	"""

	polltcpport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	def __init__(self, timestamp, pollservedfromportnumber=polltcpport):
		self.searchid = str(timestamp)
		self.launchtime = time.time()
		self.portnumber = pollservedfromportnumber
		self.active = False
		self.remaining = -1
		self.poolofwork = -1
		self.statusmessage = str()
		self.hitcount = -1
		self.notes = str()
		self.keytypes = self.setkeytypes()

		dbid = hipparchia.config['REDISDBID']
		if hipparchia.config['REDISPORT'] != 0:
			port = hipparchia.config['REDISPORT']
			self.redisconnection = redis.Redis(host='localhost', port=port, db=dbid)
		else:
			sock = hipparchia.config['REDISCOCKET']
			self.redisconnection = redis.Redis(unix_socket_path=sock, db=dbid)
		self.initializeredispoll()

	def __del__(self):
		self.deleteredispoll()

	def setkeytypes(self):
		keytypes = {'launchtime': float,
		            'portnumber': int,
		            'active': bool,
		            'remaining': int,
		            'poolofwork': int,
		            'statusmessage': bytes,
		            'hitcount': int,
		            'notes': bytes}

		return keytypes

	def initializeredispoll(self):
		for k in self.keytypes:
			rediskey = self.returnrediskey(k)
			redisvalue = getattr(self, k)
			self.redisconnection.set(rediskey, redisvalue)

	def deleteredispoll(self):
		for k in self.keytypes:
			rediskey = self.returnrediskey(k)
			redisvalue = getattr(self, k)
			self.redisconnection.delete(rediskey, redisvalue)

	def returnrediskey(self, keyname):
		return '{id}_{k}'.format(id=self.searchid, k=keyname)

	def setredisvalue(self, key, value):
		k = self.returnrediskey(key)
		self.redisconnection.set(k, value)

	def getredisvalue(self, key):
		self.redisconnection.set_response_callback('GET', self.keytypes[key])
		k = self.returnrediskey(key)
		return self.redisconnection.get(k)

	def getstatus(self):
		m = self.getredisvalue('statusmessage')
		return m.decode('utf-8')

	def getelapsed(self):
		launch = self.getredisvalue('launchtime')
		elapsed = round(time.time() - launch, 0)
		return elapsed

	def getremaining(self):
		return self.getredisvalue('remaining')

	def gethits(self):
		return self.getredisvalue('hitcount')

	def worktotal(self):
		return self.getredisvalue('poolofwork')

	def statusis(self, message):
		self.setredisvalue('statusmessage', message)

	def allworkis(self, amount):
		k = self.returnrediskey('poolofwork')
		self.setredisvalue(k, amount)

	def remain(self, remaining):
		k = self.returnrediskey('remaining')
		self.setredisvalue(k, remaining)

	def sethits(self, found):
		k = self.returnrediskey('hitcount')
		self.setredisvalue(k, found)

	def addhits(self, hits):
		k = self.returnrediskey('hitcount')
		self.redisconnection.incrby(k, hits)

	def activate(self):
		k = self.returnrediskey('active')
		self.setredisvalue(k, True)

	def deactivate(self):
		k = self.returnrediskey('active')
		self.setredisvalue(k, False)

	def getactivity(self):
		return self.getredisvalue('active')

	def getredisnotes(self):
		notes = self.getredisvalue('notes')
		return notes.decode('utf-8')

	def setnotes(self, message):
		self.setredisvalue('notes', message)

	def getnotes(self):
		notes = self.getredisnotes()
		message = '<span class="small">{msg}</span>'
		if 14 < self.getelapsed() < 21:
			m = '(long requests can be aborted by reloading the page)'
		elif re.search('unavailable', notes) and 9 < self.getelapsed() < 15:
			m = notes
		elif re.search('unavailable', notes) is None:
			m = notes
		else:
			m = ''

		return message.format(msg=m)


if hipparchia.config['POLLCONNECTIONTYPE'] != 'redis':
	class ProgressPoll(SharedMemoryProgressPoll):
		pass
else:
	class ProgressPoll(RedisProgressPoll):
		pass
