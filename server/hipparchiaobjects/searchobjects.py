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
		seeking = re.sub(r'\\ϲ', r'\\s', seeking)
		seeking = re.sub(r'^ ', r'(^|\\s)', seeking)
		seeking = re.sub(r' $', r'(\\s|$)', seeking)
		seeking = seeking.lower()
		proximate = re.sub('[σς]', 'ϲ', proximate)
		proximate = re.sub(r'\\ϲ', ' ', proximate)
		proximate = re.sub(r'^ ', r'(^|\\s)', proximate)
		proximate = re.sub(r' $', r'(\\s|$)', proximate)
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
