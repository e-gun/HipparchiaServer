# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import pickle
import re
import time
from hashlib import md5

from server import hipparchia
from server.formatting.bibliographicformatting import bcedating
from server.formatting.miscformatting import debugmessage, htmlcommentdecorator
from server.formatting.wordformatting import avoidsmallvariants
from server.hipparchiaobjects.dbtextobjects import dbLemmaObject
from server.hipparchiaobjects.vectorobjects import VectorValues
from server.listsandsession.checksession import justlatin


class SearchObject(object):
	"""

	an object that can be passed around to the various search functions
	it knows about the query, the session, etc.

	"""

	def __init__(self, searchid: str, seeking: str, proximate: str, lemmaobject: dbLemmaObject, proximatelemmaobject: dbLemmaObject, frozensession: dict):
		self.searchid = searchid
		self.originalseeking = seeking
		self.originalproximate = proximate
		self.lemma = lemmaobject  # should start moving away from self.lemma and towards self.lemmaone
		self.proximatelemma = proximatelemmaobject  # should start moving away from self.proximatelemma and towards self.lemmatwo
		self.lemmaone = self.lemma
		self.lemmatwo = self.proximatelemma
		self.lemmathree = None
		self.termthree = None
		self.phrase = str()
		self.session = frozensession
		self.iamarobot = False  # but the vectorbot is...

		# the next store the "where" part of the search and get filled out and assigned elsewhere
		self.searchsqldict = dict()
		self.searchlist = list()
		self.indexrestrictions = dict()

		# '>' will mess you up still
		self.originalseeking = re.sub(r'<', '&lt;', self.originalseeking)
		self.originalseeking = re.sub(r'>', '&gt;', self.originalseeking)
		self.originalproximate = re.sub(r'<', '&lt;', self.originalproximate)
		self.originalproximate = re.sub(r'>', '&gt;', self.originalproximate)
		self.vectortype = None
		self.tovectorize = None
		self.vectorquerytype = None
		self.vectorvalues = VectorValues(frozensession)
		self.starttime = time.time()
		self.usedcorpora = list()
		self.sentencebundlesize = hipparchia.config['SENTENCESPERDOCUMENT']
		self.poll = None
		self.searchlistthumbprint = None
		if hipparchia.config['SEARCHLISTCONNECTIONTYPE'] == 'queue':
			self.usequeue = True
		else:
			self.usequeue = False
		if hipparchia.config['SEARCHLISTCONNECTIONTYPE'] == 'redis':
			self.redissearchlist = True
		else:
			self.redissearchlist = False
		if hipparchia.config['SEARCHRESULCONNECTIONTYPE'] == 'redis':
			self.redisresultlist = True
		else:
			self.redisresultlist = False

		self.accented = False
		if self._isaccented(seeking) or self._isaccented(proximate):
			self.accented = True

		# tidy up the input with some basic regex-friendly swaps
		seeking = self.searchtermcleanup(seeking)
		proximate = self.searchtermcleanup(proximate)
		seeking = self._vjsubstitutes(seeking)
		proximate = self._vjsubstitutes(proximate)

		self.seeking = seeking
		self.proximate = proximate

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

		if self.accented:
			self.usecolumn = 'accented_line'
			self.usewordlist = 'polytonic'
		else:
			self.usecolumn = 'stripped_line'
			self.usewordlist = 'stripped'

		if frozensession['searchinsidemarkup']:
			self.usecolumn = 'marked_up_line'
			self.usewordlist = 'polytonic'

		if frozensession['searchscope'] == 'words':
			self.scope = 'words'
		else:
			self.scope = 'lines'

		if frozensession['nearornot'] == 'near':
			self.near = True
			self.nearstr = str()
		else:
			self.near = False
			self.nearstr = ' not'

		self.cap = int(frozensession['maxresults'])
		self.tempcap = None

		if frozensession['onehit']:
			self.onehit = True
		else:
			self.onehit = False

		self.distance = int(frozensession['proximity'])

	def setsearchlistthumbprint(self):
		#  { 'in0d0f': {'type': 'unrestricted', 'where': False}, ... }
		# as this is a dict you can't count on the same order of items and so the same tp
		# need access to sort to make it deterministic
		tp = [(k, self.indexrestrictions[k]['type'], self.indexrestrictions[k]['where']) for k in self.indexrestrictions]
		tp.sort()
		self.searchlistthumbprint = md5(pickle.dumps(tp)).hexdigest()

	@staticmethod
	def searchtermcleanup(searchterm: str) -> str:
		searchterm = re.sub('[σς]', 'ϲ', searchterm)
		searchterm = re.sub(r'\\ϲ', r'\\s', searchterm)
		searchterm = re.sub(r'^ ', r'(^|\\s)', searchterm)
		searchterm = re.sub(r' $', r'(\\s|$)', searchterm)
		searchterm = searchterm.lower()
		return searchterm

	def _vjsubstitutes(self, searchterm: str) -> str:
		if self.accented:
			searchterm = self._accentsdomatter(searchterm)
		else:
			searchterm = self._accentsdonotmatter(searchterm)
		return searchterm

	@staticmethod
	def _isaccented(searchterm: str) -> bool:
		accented = '[äëïöüâêîôûàèìòùáéíóúᾂᾒᾢᾃᾓᾣᾄᾔᾤᾅᾕᾥᾆᾖᾦᾇᾗᾧἂἒἲὂὒἢὢἃἓἳὃὓἣὣἄἔἴὄὔἤὤἅἕἵὅὕἥὥἆἶὖἦὦἇἷὗἧὧᾲῂῲᾴῄῴᾷῇῷᾀᾐᾠᾁᾑᾡῒῢΐΰῧἀἐἰὀὐἠὠῤἁἑἱὁὑἡὡῥὰὲὶὸὺὴὼάέίόύήώᾶῖῦῆῶϊϋ]'
		# note how rare it is going to be that you want to search for "apúd" and not "apud"...
		# the inconsistent Latin data could easily lead you to make false inferences: apúd is meaningful only
		# inside of specific editions of specific authors
		if re.search(accented, searchterm):
			accented = True
		else:
			accented = False
		return accented

	@staticmethod
	def _accentsdonotmatter(searchterm: str) -> str:
		searchterm = re.sub('v', 'u', searchterm)
		searchterm = re.sub('j', 'i', searchterm)
		return searchterm

	@staticmethod
	def _accentsdomatter(searchterm: str) -> str:
		searchterm = re.sub('v', '[vu]', searchterm)
		searchterm = re.sub('j', '[ji]', searchterm)
		return searchterm

	def getactivecorpora(self) -> list:
		allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
		activecorpora = [c for c in allcorpora if self.session[c]]
		return activecorpora

	def infervectorquerytype(self):

		if not hipparchia.config['SEMANTICVECTORSENABLED']:
			return None

		exclusive = {'cosdistbysentence', 'cosdistbylineorword', 'semanticvectorquery', 'nearestneighborsquery',
		             'tensorflowgraph', 'sentencesimilarity', 'topicmodel', 'analogyfinder'}

		qtype = list()
		for e in exclusive:
			if self.session[e]:
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

	def _doingafullcorpussearch(self, corpus) -> bool:
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

	def setsearchtype(self):
		phrasefinder = re.compile(r'[^\s]\s[^\s]')

		if re.search(phrasefinder, self.seeking) or re.search(phrasefinder, self.proximate):
			containsaphrase = True
		else:
			containsaphrase = False

		if self.lemmaone or self.lemmatwo:
			containsalemma = True
		else:
			containsalemma = False

		if self.proximate or self.lemmatwo:
			iscomplex = True
		else:
			iscomplex = False

		if containsaphrase and not iscomplex:
			self.searchtype = 'phrase'
		elif containsaphrase and iscomplex:
			self.searchtype = 'phraseandproximity'
		elif containsalemma and not iscomplex:
			self.searchtype = 'simplelemma'
			self.usewordlist = 'polytonic'
		elif iscomplex:
			self.searchtype = 'proximity'
		else:
			self.searchtype = 'simple'
		# debugmessage('SearchObject().setsearchtype(): {t}'.format(t=self.searchtype))

	def generatesearchdescription(self) -> str:
		# used to set the page title; called by executesearch()
		assert self.searchtype in ['simple', 'simplelemma', 'proximity', 'phrase', 'phraseandproximity'], 'unknown searchtype sent to generatesearchdescription()'

		if self.searchtype == 'simplelemma':
			return 'all forms of »{skg}«'.format(skg=self.lemmaone.dictionaryentry)
		elif self.lemmaone and self.lemmatwo:
			# proximity of lemma to lemma
			s = '{skg}{ns} within {sp} {sc} of {pr}'
			return s.format(skg=self.lemmaone.dictionaryentry, ns=self.nearstr, sp=self.proximity, sc=self.scope, pr=self.lemmatwo.dictionaryentry)
		elif (self.lemmaone or self.lemmatwo) and (self.seeking or self.proximate):
			# proximity of lemma to word or word to word
			if self.lemmaone:
				lm = self.lemmaone
				t = self.originalproximate
			else:
				lm = self.lemmatwo
				t = self.seeking
			s = '{skg}{ns} within {sp} {sc} of {pr}'
			return s.format(skg=lm.dictionaryentry, ns=self.nearstr, sp=self.proximity, sc=self.scope, pr=t)
		elif self.searchtype == 'simple':
			return self.originalseeking
		elif self.searchtype == 'phrase':
			return self.originalseeking
		elif self.searchtype == 'phraseandproximity':
			return self.originalseeking
		else:
			# proximity of two terms
			s = '{skg}{ns} within {sp} {sc} of {pr}'
			return s.format(skg=self.originalseeking, ns=self.nearstr, sp=self.proximity, sc=self.scope, pr=self.originalproximate)

	def swapseekingandproxmate(self):
		s = self.seeking
		p = self.proximate
		self.seeking = p
		self.proximate = s

	def swaplemmaoneandtwo(self):
		o = self.lemmaone
		t = self.lemmatwo
		self.lemmaone = t
		self.lemmatwo = o

	def generatehtmlsearchdescription(self) -> str:
		# used to set the page title; called by executesearch()
		assert self.searchtype in ['simple', 'simplelemma', 'proximity', 'phrase', 'phraseandproximity'], 'unknown searchtype sent to generatehtmlsearchdescription()'

		if self.searchtype == 'simplelemma':
			s = 'all {n} known forms of <span class="sought">»{skg}«</span>'
			return s.format(n=len(self.lemmaone.formlist), skg=self.lemmaone.dictionaryentry)
		elif self.lemmaone and self.lemmatwo:
			# proximity of lemma to lemma
			s = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of all {pn} known forms of <span class="sought">»{pskg}«</span>'
			return s.format(n=len(self.lemmaone.formlist), skg=self.lemmaone.dictionaryentry, ns=self.nearstr, sp=self.proximity, sc=self.scope, pn=len(self.lemmatwo.formlist), pskg=self.lemmatwo.dictionaryentry)
		elif (self.lemmaone or self.lemmatwo) and (self.seeking or self.proximate):
			# proximity of lemma to word
			if self.lemmaone:
				lm = self.lemmaone
				t = self.originalproximate
			else:
				lm = self.lemmatwo
				t = self.seeking
			s = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pskg}«</span>'
			return s.format(n=len(lm.formlist), skg=lm.dictionaryentry, ns=self.nearstr, sp=self.proximity, sc=self.scope, pskg=t)
		elif self.searchtype == 'simple':
			return '<span class="sought">»{skg}«</span>'.format(skg=self.originalseeking)
		elif self.searchtype == 'phrase':
			return '<span class="sought">»{skg}«</span>'.format(skg=self.originalseeking)
		elif self.searchtype == 'phraseandproximity':
			s = '<span class="sought">»{skg}«</span> within {sp} {sc} of <span class="sought">»{x}«</span>'
			return s.format(skg=self.originalseeking, x=self.termtwo, sc=self.scope, sp=self.proximity)
		else:
			# proximity of two terms
			s = '<span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pr}«</span>'
			return s.format(skg=self.originalseeking, ns=self.nearstr, sp=self.proximity, sc=self.scope, pr=self.originalproximate)

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
			if self._doingafullcorpussearch(c):
				whole.append(corpora[c])

		return whole

	def numberofauthorssearched(self) -> int:
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
		self.hitmax = False
		self.onehit = searchobject.session['onehit']
		self.usedcorpora = searchobject.usedcorpora
		self.searchsummary = str()
		self.success = str()

		self.icandodates = False
		if justlatin(searchobject.session) is False:
			self.icandodates = True

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
			try:
				self.lemma = searchobject.lemma.dictionaryentry
			except AttributeError:
				self.lemma = str()
		else:
			self.lemma = str()

		if searchobject.termone:
			self.headword = searchobject.termone
		else:
			self.headword = str()

		dmin, dmax = bcedating(searchobject.session)
		self.dmin = dmin
		self.dmax = dmax

		self.image = str()
		self.reasons = list()

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

	@htmlcommentdecorator
	def generatesummary(self) -> str:
		"""

		generate the summary info.

		example of what the browser will see:

			<div id="searchsummary">
			Sought <span class="sought">»εναντ«</span>
			<br>
			Searched 3,844 texts and found 50 passages (0.21s)
			<br>
			Searched between 850 B.C.E. and 1 C.E.
			<br>
			Only allowing one match per item searched (either a whole author or a specified work)
			<br>
			Sorted by date
			<br>
			[Search suspended: result cap reached.]
			</div>

		:return:
		"""

		stemplate = """
		Sought {hs}
		<br>
		{tx} and found {fd} ({tm}s)
		<br>
		{betw}
		{onehit}
		Sorted by {sb}
		<br>
		{hitmax}
		{success}
		"""

		# pluralization check
		tx = 'Searched 1 work'
		if self.scope != 1:
			tx = 'Searched {t} works'.format(t=self.scope)

		# pluralization check
		fd = '1 passage'
		if self.resultcount != '1 passages':
			fd = self.resultcount

		betw = '<!-- dates did not matter -->\n'

		if self.icandodates:
			if self.dmin != '850 B.C.E.' or self.dmax != '1500 C.E.':
				betw = 'Searched between {a} and {b}\n\t<br>'.format(a=self.dmin, b=self.dmax)

		onehit = '<!-- unlimited hits per author -->\n'
		if self.onehit:
			onehit = 'Only allowing one match per item searched (either a whole author or a specified work)\n\t<br>'

		hitmax = '<!-- did not hit the results cap -->\n'
		if self.hitmax:
			hitmax = '[Search suspended: result cap reached.]'

		summary = stemplate.format(hs=self.htmlsearch, tx=tx, fd=fd, tm=self.searchtime, betw=betw,
		                           onehit=onehit, sb=self.sortby, hitmax=hitmax, success=self.success)

		return summary

	def generateoutput(self) -> dict:
		"""

		this is the one we really care about:

		generate everything that we send to the JS so that it can update the browser display via the contents of outputdict

		note that these attributes start out empty and need to be updated before you can get what you want here

		for example, self.generatesummary() needs to set self.searchsummary before we will have a summary

		:return:
		"""

		self.searchsummary = self.generatesummary()

		outputdict = dict()
		itemsweuse = ['title', 'searchsummary', 'found', 'image', 'js']
		for item in itemsweuse:
			outputdict[item] = getattr(self, item)
		return outputdict

	def generatenulloutput(self, itemname=None, itemval=str()):
		"""

		build null output that you can feed with an error message

		useful for catching illegitimate searches / configurations

		'searchsummary' is almost certainly the 'itemmname' you will pick

		:param itemname:
		:param itemval:
		:return:
		"""

		outputdict = dict()
		itemsweuse = ['title', 'searchsummary', 'found', 'image', 'js']
		for item in itemsweuse:
			if item != itemname:
				outputdict[item] = str()
			else:
				outputdict[item] = itemval
		return outputdict


class SearchResult(object):
	"""

	really just a more maintainable version of a dict

	"""
	def __init__(self, hitnumber, author, work, citationstring, worknumber, clickurl, lineobjects):
		self.hitnumber = hitnumber
		self.author = avoidsmallvariants(author)
		self.work = avoidsmallvariants(work)
		self.citationstring = citationstring
		self.clickurl = clickurl
		self.lineobjects = lineobjects
		self.worknumber = worknumber

	def getindex(self) -> int:
		"""

		fetch the index value of the focus line

		derive it from the tail of the clickurl, e.g.:

			'linenumber/lt1212/002/5284'

		:return:
		"""

		return int(self.clickurl.split('/')[-1])

	def getlocusthml(self) -> str:
		"""
		generate the wrapped html for the citation; e.g:
			<locus>
				<span class="findnumber">[20]</span>&nbsp;&nbsp;
				<span class="foundauthor">Valerius Maximus</span>,&nbsp;<span class="foundwork">Facta et Dicta Memorabilia</span>:
				<browser id="linenumber/lt1038w001/199"><span class="foundlocus">book 1, chapter 1, section 15, line 6</span></browser>
			</locus>
			<br />
		:return:
		"""

		locushtml = '<locus>\n{cit}\n</locus><br />\n'.format(cit=self.citationhtml(self.citationstring))

		return locushtml

	def citationhtml(self, citestring) -> str:
		"""

		generate the non-wrapped html for the citation; e.g:

			<span class="findnumber">[13]</span>&nbsp;&nbsp;<span class="foundauthor">Quintilianus, Marcus Fabius</span>,&nbsp;<span class="foundwork">Declamationes Minores</span>:
			<browser id="linenumber/lt1002w002/24040"><span class="foundlocus">oration 289, section pr, line 1</span><br /></browser>

		:return:
		"""

		citationtemplate = """
			<span class="findnumber">[{hn}]</span>&nbsp;&nbsp;
			<span class="foundauthor">{au}</span>,&nbsp;<span class="foundwork">{wk}</span>:
			<browser id="{url}"><span class="foundlocus">{cs}</span></browser>"""

		locushtml = citationtemplate.format(hn=self.hitnumber, au=self.author, wk=self.work, url=self.clickurl, cs=citestring)

		return locushtml
