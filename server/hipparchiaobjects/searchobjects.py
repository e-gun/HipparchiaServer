# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time

from server import hipparchia
from server.formatting.bibliographicformatting import bcedating
from server.formatting.miscformatting import htmlcommentdecorator
from server.formatting.wordformatting import avoidsmallvariants
from server.hipparchiaobjects.vectorobjects import VectorValues
from server.listsandsession.checksession import justlatin


class SearchObject(object):
	"""

	an object that can be passed around to the various search functions
	it knows about the query, the session, etc.

	"""

	def __init__(self, searchid, seeking, proximate, lemmaobject, proximatelemmaobject, frozensession):
		self.searchid = searchid
		self.originalseeking = seeking
		self.originalproximate = proximate
		self.lemma = lemmaobject
		self.proximatelemma = proximatelemmaobject
		self.lemmaone = self.lemma
		self.lemmatwo = self.proximatelemma
		self.lemmathree = None
		self.termthree = None
		self.session = frozensession
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

		# searchtermcharactersubstitutions() logic has moved here

		seeking = self.searchtermcleanup(seeking)
		proximate = self.searchtermcleanup(proximate)

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

		if frozensession['onehit']:
			self.onehit = True
		else:
			self.onehit = False

		self.distance = int(frozensession['proximity'])

	@staticmethod
	def searchtermcleanup(searchterm):
		searchterm = re.sub('[σς]', 'ϲ', searchterm)
		searchterm = re.sub(r'\\ϲ', r'\\s', searchterm)
		searchterm = re.sub(r'^ ', r'(^|\\s)', searchterm)
		searchterm = re.sub(r' $', r'(\\s|$)', searchterm)
		searchterm = searchterm.lower()
		return searchterm

	def getactivecorpora(self):
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
		"""

		# pluralization check
		tx = 'Searched 1 text'
		if self.scope != 1:
			tx = 'Searched {t} texts'.format(t=self.scope)

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
		                           onehit=onehit, sb=self.sortby, hitmax=hitmax)

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
