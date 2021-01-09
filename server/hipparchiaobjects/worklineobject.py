# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from string import punctuation
from typing import List

from flask import session

from server import hipparchia
from server.dbsupport.dbbuildinfo import buildoptionchecking
from server.formatting.betacodeescapes import andsubstitutes
from server.formatting.wordformatting import attemptsigmadifferentiation, avoidsmallvariants, forcelunates, tidyupterm, uforvoutsideofmarkup

buildoptions = buildoptionchecking()


class dbWorkLine(object):
	"""
	an object that corresponds to a db line (+ a fair number of methods...)

	CREATE TABLE public.in0207 (
		index integer NOT NULL UNIQUE DEFAULT nextval('in0207'::regclass),
		wkuniversalid character varying(10) COLLATE pg_catalog."default",
		level_05_value character varying(64) COLLATE pg_catalog."default",
		level_04_value character varying(64) COLLATE pg_catalog."default",
		level_03_value character varying(64) COLLATE pg_catalog."default",
		level_02_value character varying(64) COLLATE pg_catalog."default",
		level_01_value character varying(64) COLLATE pg_catalog."default",
		level_00_value character varying(64) COLLATE pg_catalog."default",
		marked_up_line text COLLATE pg_catalog."default",
		accented_line text COLLATE pg_catalog."default",
		stripped_line text COLLATE pg_catalog."default",
		hyphenated_words character varying(128) COLLATE pg_catalog."default",
		annotations character varying(256) COLLATE pg_catalog."default"
	)

	worth noting anywhere you think you will be grabbing 100k+ lines:

	def f(n):
		for _ in range(n):
			re.sub(r'e', str(), 'abcdef')
		return

	def g(n):
		for _ in range(n):
			'abcdef'.replace('e', str())
		return

	timeit(lambda: f(100), number=10000)
		1.2959101439998904
	timeit(lambda: g(100), number=10000)
		0.3025400220001302

	"""

	__slots__ = ('wkuinversalid', 'db', 'authorid', 'workid', 'universalid', 'index', 'l0', 'l1', 'l2', 'l3', 'l4', 'l5',
	             'markedup', 'polytonic', 'stripped', 'annotations', 'hyphenated', 'paragraphformatting', 'hasbeencleaned',
	             'mylevels', 'mynonbaselevels')

	nonliterarycorpora = ['in', 'dp', 'ch']
	# re.compile pulled out of the inset functions so that you do not compile 100k times when generating a long text
	insetvaluefinder = re.compile(r'value=".*?" ')
	metadatafinder = re.compile(r'<hmu_metadata_notes value="(.*?)" />')
	andsfinder = re.compile(r'&(\d{1,2})(.*?)(&\d?)')
	hmuopenfinder = re.compile(r'<(hmu_.*?)>')
	hmuclosefinder = re.compile(r'</(hmu_.*?)>')
	hmuspanopenfinder = re.compile(r'<hmu_span_(.*?)>')
	hmuspanclosefinder = re.compile(r'</hmu_span_(.*?)>')
	hmushiftfinder = re.compile(r'<hmu_fontshift_(.*?)_(.*?)>')
	hmushiftcleaner = re.compile(r'</hmu_fontshift_.*?>')
	hmuformattingopener = re.compile(r'<hmu_(span|fontshift)_(.*?)>')
	hmuformattingcloser = re.compile(r'</hmu_(span|fontshift)_(.*?)>')
	bracketclosedfinder = {'square': {'c': re.compile(r'\]')}, 'round': {'c': re.compile(r'\)')}, 'angled': {'c': re.compile(r'⟩')}, 'curly': {'c': re.compile(r'\}')}}
	bracketfinder = {
		'square': {'regex': re.compile(r'\[[^\]]{0,}$'),
		           'exceptions': [re.compile(r'\[(ϲτρ|ἀντ)\. .\.'), re.compile(r'\[ἐπῳδόϲ')]},
		'round': {'regex': re.compile(r'\([^\)]{0,}$')},
		'angled': {'regex': re.compile(r'⟨[^⟩]{0,}$')},
		'curly': {'regex': re.compile(r'\{[^\}]{0,}$')},
		}
	editorialbrackets = {
				'square': {
					'ocreg': re.compile(r'\[(.*?)(\]|$)'),
					'coreg': re.compile(r'(^|\[)(.*?)\]'),
					'class': 'editorialmarker_squarebrackets',
					'o': '[',
					'c': ']'
				},
				'round': {
					'ocreg': re.compile(r'\((.*?)(\)|$)'),
					'coreg': re.compile(r'(^|\()(.*?)\)'),
					'class': 'editorialmarker_roundbrackets',
					'o': '(',
					'c': ')'
				},
				'angled': {
					'ocreg': re.compile(r'⟨(.*?)(⟩|$)'),
					'coreg': re.compile(r'(^|⟨)(.*?)⟩'),
					'class': 'editorialmarker_angledbrackets',
					'o': '⟨',
					'c': '⟩'
				},
				'curly': {
					'ocreg': re.compile(r'\{(.*?)(\}|$)'),
					'coreg': re.compile(r'(^|\{)(.*?)\}'),
					'class': 'editorialmarker_curlybrackets',
					'o': '{',
					'c': '}'
				}
			}

	grave = 'ὰὲὶὸὺὴὼῒῢᾲῂῲἃἓἳὃὓἣὣἂἒἲὂὒἢὢ'
	acute = 'άέίόύήώΐΰᾴῄῴἅἕἵὅὕἥὥἄἔἴὄὔἤὤ'
	gravetoacute = str.maketrans(grave, acute)
	minimumgreek = re.compile(
		'[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')
	# note the tricky combining marks like " ͡ " which can be hard to spot since they float over another special character
	elidedextrapunct = '\′‵‘·“”„—†⌈⌋⌊∣⎜͙ˈͻ✳※¶§⸨⸩｟｠⟫⟪❵❴⟧⟦→◦⊚𐄂𝕔☩(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚̄⁝͜‖͡⸓͝'
	extrapunct = elidedextrapunct + '’'
	greekpunct = re.compile('[{s}]'.format(s=re.escape(punctuation + elidedextrapunct)))
	latinpunct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))
	smallcaps = re.compile(r'(<span class="smallcapitals">)(.*?)(</span>)')

	def __init__(self, wkuinversalid, index, level_05_value, level_04_value, level_03_value, level_02_value,
	             level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words,
	             annotations):

		self.wkuinversalid = wkuinversalid[:10]
		self.db = wkuinversalid[0:2]
		self.authorid = wkuinversalid[:6]
		self.workid = wkuinversalid[7:]
		self.universalid = wkuinversalid
		self.index = index
		self.l5 = level_05_value
		self.l4 = level_04_value
		self.l3 = level_03_value
		self.l2 = level_02_value
		self.l1 = level_01_value
		self.l0 = level_00_value
		self.markedup = marked_up_line
		self.polytonic = accented_line
		self.stripped = stripped_line
		self.annotations = annotations
		self.hyphenated = hyphenated_words
		self.paragraphformatting = None
		self.hasbeencleaned = False
		self.mylevels = [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]
		self.mynonbaselevels = [self.l1, self.l2, self.l3, self.l4, self.l5]
		if self.markedup is None:
			self.markedup = str()
			self.polytonic = str()
			self.stripped = str()

	def getlineurl(self):
		# .getlineur() is used by the vectors
		return 'line/{w}/{i}'.format(w=self.wkuinversalid, i=self.index)

	def getbrowserurl(self):
		return 'linenumber/{a}/{w}/{i}'.format(a=self.authorid, w=self.workid, i=self.index)

	def _tagsalreadyrational(self):
		try:
			rational = buildoptions[self.db]['rationalizetags']
		except KeyError:
			rational = 'n'

		try:
			alreadyhtml = buildoptions[self.db]['htmlifydatabase']
		except KeyError:
			alreadyhtml = 'y'

		if rational == 'y' and alreadyhtml == 'n':
			return True
		else:
			return False

	def generatehtmlversion(self):
		try:
			zaplunates = session['zaplunates']
		except RuntimeError:
			# accursed Windows10 non-fork() issue
			zaplunates = hipparchia.config['RESTOREMEDIALANDFINALSIGMA']
		except KeyError:
			# you don't have a session at all...
			# you can provoke this by using something like curl on the server
			zaplunates = False

		try:
			zapvees = session['zapvees']
		except RuntimeError:
			# accursed Windows10 non-fork() issue
			zapvees = hipparchia.config['FORCEUFORV']
		except KeyError:
			# you don't have a session at all...
			# you can provoke this by using something like curl on the server
			zapvees = False

		if zaplunates:
			self.markedup = attemptsigmadifferentiation(self.markedup)
		if hipparchia.config['FORCELUNATESIGMANOMATTERWHAT']:
			self.markedup = forcelunates(self.markedup)
		if hipparchia.config['DISTINCTGREEKANDLATINFONTS']:
			self.markedup = self.separategreekandlatinfonts()

		if zapvees:
			self.markedup = uforvoutsideofmarkup(self.markedup)

		# needs to happen after zapvees
		# smallcaps means: "Civitatem peregrinvs vsvrpans veneat" and not "Ciuitatem peregrinus usurpans ueneat"
		if re.search(self.smallcaps, self.markedup):
			vlswaplambda = lambda x: x.group(1) + x.group(2).replace('u', 'v') + x.group(3)
			self.markedup = re.sub(self.smallcaps, vlswaplambda, self.markedup)

		self.fixhmuirrationaloragnization()
		self.hmuspanrewrite()
		self.hmufontshiftsintospans()

	def decompose(self) -> tuple:
		"""

		return the tuple that generated the object

		but see dblineintolineobject():
			all columns pushed straight into the object with *one* twist: 1, 0, 2, 3, ...

		:return:
		"""

		items = ['wkuinversalid', 'index', 'l5', 'l4', 'l3', 'l2', 'l1', 'l0', 'markedup', 'polytonic', 'stripped',
		         'hyphenated', 'annotations']
		tvals = [getattr(self, i) for i in items]
		return tuple(tvals)

	def uncleanlocus(self) -> str:
		"""
		call me to get a formatted citation: "3.2.1"

		but funky chars might be in here...

		:param self:
		:return:
		"""

		if self.db not in dbWorkLine.nonliterarycorpora:
			loc = [lvl for lvl in self.mylevels if str(lvl) != '-1']
			loc.reverse()
			citation = '.'.join(loc)
		else:
			# papyrus and inscriptions are wonky: usually they have just a recto, but sometimes they have something else
			# only mark the 'something else' version
			if self.l1 != 'recto':
				citation = '{a} {b}'.format(a=self.l1, b=self.l0)
			else:
				citation = self.l0

		return citation

	def locus(self) -> str:
		"""

		turn the funky substitutes into standard characters:

		in:     B❨1❩, line 2
		out:    B(1), line 2

		NB: these might not be in the data...

		:return:
		"""

		return avoidsmallvariants(self.uncleanlocus())

	def avoidminimallocus(self):
		"""

		it is possible for locus() to return '1', vel sim when nocontexthtmlifysearchfinds() calls it

		this is not very clickable

		:return:
		"""

		lc = self.locus()

		try:
			lc = 'line ' + str(int(lc))
		except ValueError:
			# 'try' will only succeed if l is a simple digit (and so needs expansion)
			pass

		return lc

	def anchoredlocus(self) -> str:
		"""

		build a clickable url for the locus and wrap the locus in it:

		   <indexedlocation id="linenumber/gr0032/008/30784">1.4.4</indexedlocation>

		:return:
		"""

		template = '<indexedlocation id="linenumber/{au}/{wk}/{idx}">{loc}</indexedlocation>'
		locus = template.format(au=self.authorid, wk=self.workid, idx=self.index, loc=self.locus())
		return locus

	def _generatelocus(self, levellist) -> str:
		"""

		common code for prolixlocus() and shortlocus()

		:param levellist:
		:return:
		"""

		loc = list()
		for lvl in levellist:
			if str(lvl) != '-1' and (self.db not in dbWorkLine.nonliterarycorpora and lvl != 'recto'):
				loc.append(lvl)
		loc.reverse()

		if not loc:
			citation = self.locus()
		else:
			citation = '.'.join(loc)

		return citation


	def prolixlocus(self) -> str:
		"""
		try to get a citation that DOES NOT drop the lvl0 info: "3.2"
		:return:
		"""

		return self._generatelocus(self.mylevels)


	def shortlocus(self) -> str:
		"""
		try to get a short citation that drops the lvl0 info: "3.2"
		useful for tagging level shifts without constantly seeing 'line 1'
		:return:
		"""

		return self._generatelocus(self.mylevels)

	def uncleanlocustuple(self):
		"""
		call me to get a citation tuple in 0-to-5 order
		:return:
		"""
		cit = list()
		for lvl in self.mylevels:
			if str(lvl) != '-1':
				cit.append(lvl)
		citationtuple = tuple(cit)

		return citationtuple

	def locustuple(self):
		"""

		turn the funky substitutes into standard characters:

		in:     B❨1❩, line 2
		out:    B(1), line 2

		NB: these might not be in the data...

		:return:
		"""

		ltuple = self.uncleanlocustuple()

		newtuple = (avoidsmallvariants(t) for t in ltuple)

		return newtuple

	def samelevelas(self, other) -> bool:
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci have to be from the same work
		:param self:
		:param other:
		:return:
		"""

		if self.wkuinversalid == other.wkuinversalid and self.mynonbaselevels == other.mynonbaselevels:
			return True
		else:
			return False

	def equivalentlevelas(self, other) -> bool:
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci do not have to be from the same work
		:param self:
		:param other:
		:return:
		"""

		if self.mynonbaselevels == other.mynonbaselevels:
			return True
		else:
			return False

	def toplevel(self) -> int:
		top = 0
		for lvl in self.mylevels:
			if str(lvl) != '-1':
				top += 1
			else:
				return top

		# should not need this, but...
		return top

	def unformattedline(self) -> str:
		"""
		remove markup from contents

		this is the only place where τ’ and δ’ are not τ and δ

		:return:
		"""

		markup = re.compile(r'(<.*?>)')

		unformatted = re.sub(markup, str(), self.markedup)
		unformatted = unformatted.replace('&nbsp;', str())

		return unformatted

	def showlinehtml(self) -> str:
		"""

		make HTML of marked up line visible

		:return:
		"""

		if not self.hasbeencleaned:
			self.generatehtmlversion()

		markup = re.compile(r'(<)(.*?)(>)')
		left = '<smallcode>&lt;'
		right = '&gt;</smallcode>'

		visiblehtml = re.sub(markup, left + r'\2' + right, self.markedup)

		return visiblehtml

	def wordcount(self) -> int:
		"""
		return a wordcount
		"""

		line = self.stripped
		return len([x for x in line.split(' ') if x])

	def wordlist(self, version) -> List[str]:
		"""
		return a list of words in the line; will include the full version of a hyphenated last word
		:param version:
		:return:
		"""

		line = None

		if version in ['polytonic', 'stripped']:
			line = getattr(self, version)
			# Non-breaking space needs to go
		elif version in ['marked_up_line']:
			line = self.unformattedline()

		line = re.sub(r'\xa0', ' ', line)
		wordlist = [w for w in line.split(' ') if w]

		return wordlist

	def indexablewordlist(self) -> List[str]:
		# don't use set() - that will yield undercounts
		polytonicwords = self.wordlist('polytonic')
		polytonicgreekwords = [tidyupterm(w, dbWorkLine.greekpunct).lower() for w in polytonicwords if re.search(dbWorkLine.minimumgreek, w)]
		polytoniclatinwords = [tidyupterm(w, dbWorkLine.latinpunct).lower() for w in polytonicwords if not re.search(dbWorkLine.minimumgreek, w)]
		polytonicwords = polytonicgreekwords + polytoniclatinwords
		# need to figure out how to grab τ’ and δ’ and the rest
		# but you can't say that 'me' is elided in a line like 'inquam, ‘teque laudo. sed quando?’ ‘nihil ad me’ inquit ‘de'
		unformattedwords = set(self.wordlist('marked_up_line'))
		listofwords = [w for w in polytonicwords if w+'’' not in unformattedwords or not re.search(dbWorkLine.minimumgreek, w)]
		elisions = [w+"'" for w in polytonicwords if w+'’' in unformattedwords and re.search(dbWorkLine.minimumgreek, w)]
		listofwords.extend(elisions)
		listofwords = [w.translate(dbWorkLine.gravetoacute) for w in listofwords]
		listofwords = [w.replace('v', 'u') for w in listofwords]
		return listofwords

	def wordset(self) -> set:
		return set(self.indexablewordlist())

	def lastword(self, version: str) -> str:
		last = str()
		if version in ['accented', 'stripped']:
			line = getattr(self, version).split(' ')
			last = line[-1]
		return last

	def firstword(self, version: str) -> str:
		first = str()
		if version in ['accented', 'stripped']:
			line = getattr(self, version).split(' ')
			first = line[0]
		return first

	def allbutlastword(self, version: str) -> str:
		"""
		return the line less its final word
		"""
		allbutlastword = str()
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			line = line.split(' ')
			allbutlast = line[:-1]
			allbutlastword = ' '.join(allbutlast)

		return allbutlastword

	def allbutfirstword(self, version: str) -> str:
		"""
		return the line less its first word
		"""
		allbutfirstword = str()
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(<.*?>)', r'', line)
			line = line.split(' ')
			allbutfirst = line[1:]
			allbutfirstword = ' '.join(allbutfirst)

		return allbutfirstword

	def allbutfirstandlastword(self, version: str) -> str:
		"""
		terun the line lest the first and last words (presumably both are hypenated)
		:param version:
		:return:
		"""
		allbutfirstandlastword = str()
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(<.*?>)', r'', line)
			line = line.split(' ')
			middle = line[1:-1]
			allbutfirstandlastword = ' '.join(middle)

		return allbutfirstandlastword

	def insetannotations(self) -> List[str]:
		"""

		<hmu_metadata_notes value="Non. 104M" />

		note that in 'Gel. &3N.A.& 20.3.2' the '&3' turns on italics

		:return:
		"""

		# metadatafinder = re.compile(r'<hmu_metadata_notes value="(.*?)" />')
		# andsfinder = re.compile(r'&(\d{1,2})(.*?)(&\d?)')

		notes = re.findall(dbWorkLine.metadatafinder, self.markedup)
		notes = [re.sub(dbWorkLine.andsfinder, andsubstitutes, n) for n in notes]

		return notes

	def markeditorialinsersions(self, editorialcontinuationdict, bracketfinder=None):
		"""

		set a '<span>...</span>' around bracketed line segments
			square: [abc]
			rounded:  (abc)
			angled: ⟨abc⟩
			curly: {abc}
			angledquotes: »abc« BUT some texts are «abc»; therefore this is HOPELESSLY BROKEN

		editorialcontinuationdict looks like:
			{ 'square': True, 'round': False, 'curly': False, 'angled': False }

		:param self:
		:return:
		"""

		if not bracketfinder:
			bracketfinder = dbWorkLine.editorialbrackets

		theline = self.markedup

		# the brackets in the metadata will throw off the bracketfinder:
		#   <hmu_metadata_publicationinfo value="BSA 47.1952.187,3 [SEG 12.419]" />
		# but we do not need that info when (merely) displaying the line: it is extracted elsewhere
		# insetvaluefinder = re.compile(r'value=".*?" ')

		theline = re.sub(dbWorkLine.insetvaluefinder, r'value="" ', theline)

		for t in editorialcontinuationdict.keys():
			try:
				bracketfinder[t]
			except IndexError:
				return theline

			o = bracketfinder[t]['o']
			c = bracketfinder[t]['c']
			cl = bracketfinder[t]['class']
			openandmaybeclose = bracketfinder[t]['ocreg']
			closeandmaybeopen = bracketfinder[t]['coreg']

			if re.search(openandmaybeclose, theline):
				theline = re.sub(openandmaybeclose, r'{o}<span class="{cl}">\1</span>\2'.format(o=o, cl=cl), theline)
			elif re.search(closeandmaybeopen, theline):
				theline = re.sub(closeandmaybeopen, r'\1<span class="{cl}">\2</span>{c}'.format(cl=cl, c=c), theline)
			elif editorialcontinuationdict[t]:
				theline = '<span class="{cl}">{sa}</span>'.format(cl=cl, sa=theline)

		return theline

	def separategreekandlatinfonts(self):
		"""

		convert:
			'Ἀϲίᾳ ἐπιγραφομένῃ (FHG I 25)· ‘γυναῖκεϲ δ’ ἐπὶ τῆϲ'

		into
			'<greekfont>Ἀϲίᾳ ἐπιγραφομένῃ (</greekfont><latinfont>FHG I 25)· ‘</latinfont><greekfont>γυναῖκεϲ δ’ ἐπὶ τῆϲ</greekfont>'

		you might want to adjust the definition of punct to avoid too much mix-and-match of fonts

		:return:
		"""
		# unicode space: greek and coptic 370-400; greek extended 1f00, 2000
		greekset = set(range(int(0x370), int(0x400))).union(set(range(int(0x1f00), int(0x2000))))

		ignore = '· “”’.'
		tagging = {'g': {'open': '<greekfont>', 'close': '</greekfont>'},
		           'l': {'open': '<latinfont>', 'close': '</latinfont>'},
		           'x': {'open': '', 'close': ''}}

		linechars = list(self.markedup)
		linechars.reverse()
		if not linechars:
			# otherwise you will throw exceptions in a second
			linechars = [' ']

		newline = list()
		currently = self.determinecharacterset(linechars[-1], greekset, ignore)
		# prevsiously = self.determinecharacterset(linechars[-1], greekset)
		if linechars[-1] != '<':
			newline.append(tagging[currently]['open'])
			insideofmarkup = False
		else:
			insideofmarkup = True
			newline.append(linechars[-1])
			linechars.pop()

		while linechars:
			thischar = linechars.pop()
			if thischar == '<':
				insideofmarkup = True
			if not insideofmarkup:
				if self.determinecharacterset(thischar, greekset, ignore) != currently and self.determinecharacterset(thischar, greekset, ignore) != 'x':
					newline.append(tagging[currently]['close'])
					currently = self.determinecharacterset(thischar, greekset, ignore)
					newline.append(tagging[currently]['open'])
			newline.append(thischar)
			if thischar == '>':
				insideofmarkup = False

		newline.append(tagging[currently]['close'])
		newline = ''.join(newline)
		return newline

	@staticmethod
	def determinecharacterset(character, greekset, ignore):
		if character in ignore:
			return 'x'
		if ord(character) in greekset:
			return 'g'
		else:
			return 'l'

	def probablylatin(self):
		mostlylatindbs = ['lt', 'ch']
		if self.db in mostlylatindbs:
			return True
		else:
			return False

	def probablygreek(self):
		mostlygreekdbs = ['gr', 'in', 'dp']
		if self.db in mostlygreekdbs:
			return True
		else:
			return False

	def bracketopenedbutnotclosed(self, btype='square', bracketfinder=None):
		"""

		return True if you have 'abcd[ef ghij' and so need to continue marking editorial material

		note that only 'square' really works unless/until candomultilinecontinuation expands in markeditorialinsersions()
		this will actually be tricky since the code was built only to keep track of one continuing item...

		:return:
		"""

		if not bracketfinder:
			bracketfinder = dbWorkLine.bracketfinder

		openandnotclose = bracketfinder[btype]['regex']

		try:
			falsify = [re.search(e, self.markedup) for e in bracketfinder[btype]['exceptions']]
		except:
			falsify = [None]

		if re.search(openandnotclose, self.markedup) and True not in falsify:
			return True
		else:
			return False

	def bracketclosed(self, btype='square', bracketfinder=None):
		"""

		return true if there is a ']' in the line

		note that only 'square' really works unless/until candomultilinecontinuation expands in markeditorialinsersions()

		:return:
		"""

		if not bracketfinder:
			bracketfinder = dbWorkLine.bracketclosedfinder

		close = bracketfinder[btype]['c']
		if re.search(close, self.markedup):
			return True
		else:
			return False

	def hmuspanrewrite(self):
		"""

		convert <hmu_span_xxx> ... </hmu_span_xxx> into
		<span class="xxx">...</span>

		:return:
		"""
		try:
			alreadyconverted = buildoptions[self.db]['htmlifydatabase']
		except KeyError:
			alreadyconverted = 'n'

		if alreadyconverted == 'n':
			self.markedup = re.sub(dbWorkLine.hmuspanopenfinder, r'<span class="\1">', self.markedup)
			self.markedup = re.sub(dbWorkLine.hmuspanclosefinder, r'</span>', self.markedup)

	def hmufontshiftsintospans(self):
		"""

		turn '<hmu_fontshift_latin_italic>b </hmu_fontshift_latin_italic>'

		into '<span class="latin italic">b </span>'

		:param texttoclean:
		:return:
		"""

		try:
			alreadyconverted = buildoptions[self.db]['htmlifydatabase']
		except KeyError:
			alreadyconverted = 'n'

		if alreadyconverted == 'n':
			if self.probablygreek():
				language = 'greek'
			else:
				language = 'latin'

			self.markedup = re.sub(dbWorkLine.hmushiftfinder, lambda x: self.matchskipper(x.group(1), x.group(2), language), self.markedup)
			self.markedup = re.sub(dbWorkLine.hmushiftcleaner, r'</span>', self.markedup)

	@staticmethod
	def matchskipper(groupone, grouptwo, language: str) -> str:
		"""

		r'<span class="\1 \2">'

		or

		r'<span class="\2">'

		skip a matchgroup if it matches language

		this is useful because "latin normal" in a latin author can lead to
		a color shift, vel sim. when you really don't need to flag 'latinity' in this
		context

		also convert 'smallerthannormal_italic' into 'smallerthannormal italic'


		:param groupone:
		:param grouptwo:
		:param language:
		:return:
		"""

		grouptwo = grouptwo.replace('_', ' ')

		if groupone != language:
			spanner = '<span class="{a} {b}">'.format(a=groupone, b=grouptwo)
		else:
			spanner = '<span class="{b}">'.format(a=groupone, b=grouptwo)

		return spanner

	def hmuopenedbutnotclosed(self):
		"""

		we are looking for paragraphs of formatting that are just getting started

		return the tag name if there is an <hmu_...> and not a corresponding </hmu...> in the line

		otherwise return false

		:return:
		"""

		opentag = False

		opened = set(re.findall(dbWorkLine.hmuopenfinder, self.markedup))
		closed = set(re.findall(dbWorkLine.hmuclosefinder, self.markedup))
		differ = opened.difference(closed)
		differ = {d for d in differ if 'standalone' not in d}

		if differ:
			# note that if there are two unbalanced tags we just failed to do something about that
			opentag = differ.pop()

		return opentag

	def hmuclosedbeforeopened(self, tagtocheck) -> bool:
		"""

		true if there is a stray '</tagtocheck>' in the line

		:return:
		"""

		closecheck = r'</{t}>'.format(t=tagtocheck)
		try:
			closed = re.search(closecheck, self.markedup)
		except re.error:
			# re.error: unknown extension ?) at position 33
			# lt0407@138016 | Antonio. ad ea autem quae scripsisti (tris enim acceperam <span class="smallcapitals">iii</span>
			# print('hmuclosedbeforeopened() re.error: {ln}'.format(ln=self.markedup))
			return False
		if closed:
			closedat = closed.span()[0]
			open = r'<{t}>'.format(t=tagtocheck)
			opened = re.search(open, self.markedup)
			if opened:
				openedat = opened.span()[0]
				if openedat < closedat:
					return False
				else:
					return True
			else:
				return True
		else:
			return False

	def fixhmuirrationaloragnization(self):
		"""

		Note the irrationality (for HTML) of the following (which is masked by the 'spanner'):
		[have 'EX_ON' + 'SM_ON' + 'EX_OFF' + 'SM_OFF']
		[need 'EX_ON' + 'SM_ON' + 'SM_OFF' + 'EX_OFF' + 'SM_ON' + 'SM_OFF' ]

		hipparchiaDB=# SELECT index, marked_up_line FROM gr0085 where index = 14697;
		 index |                                                                           marked_up_line
		-------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------
		 14697 | <hmu_span_expanded_text><hmu_fontshift_greek_smallerthannormal>τίϲ ἡ τάραξιϲ</hmu_span_expanded_text> τοῦ βίου; τί βάρβιτοϲ</hmu_fontshift_greek_smallerthannormal>
		(1 row)


		hipparchiaDB=> SELECT index, marked_up_line FROM gr0085 where index = 14697;
		 index |                                                marked_up_line
		-------+---------------------------------------------------------------------------------------------------------------
		 14697 | <span class="expanded_text"><span class="smallerthannormal">τίϲ ἡ τάραξιϲ</span> τοῦ βίου; τί βάρβιτοϲ</span>
		(1 row)


		fixing this is an interesting question; it seems likely that I have missed some way of doing it wrong...
		but note 'b' below: this is pretty mangled and the output is roughly right...

		invalidline = '<hmu_span_expanded_text><hmu_fontshift_greek_smallerthannormal>τίϲ ἡ τάραξιϲ</hmu_span_expanded_text> τοῦ βίου; τί βάρβιτοϲ</hmu_fontshift_greek_smallerthannormal>'
		openspans {0: 'span_expanded_text', 24: 'fontshift_greek_smallerthannormal'}
		closedspans {76: 'span_expanded_text', 123: 'fontshift_greek_smallerthannormal'}
		balancetest [(False, False, True)]

		validline = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<hmu_fontshift_latin_smallcapitals>errantes</hmu_fontshift_latin_smallcapitals><hmu_fontshift_latin_normal> pascentes, ut alibi “mille meae Siculis</hmu_fontshift_latin_normal>'
		openspans {36: 'fontshift_latin_smallcapitals', 115: 'fontshift_latin_normal'}
		closedspans {79: 'fontshift_latin_smallcapitals', 183: 'fontshift_latin_normal'}
		balancetest [(False, True, False)]

		# need a third check: or not (open[okeys[x]] == closed[ckeys[x]])
		z = '&nbsp;&nbsp;&nbsp;<hmu_fontshift_latin_normal>II 47.</hmu_fontshift_latin_normal><hmu_fontshift_latin_italic> prognosticorum causas persecuti sunt et <hmu_span_latin_expanded_text>Boëthus Stoicus</hmu_span_latin_expanded_text>,</hmu_fontshift_latin_italic>'
		openspans {18: 'fontshift_latin_normal', 81: 'fontshift_latin_italic', 150: 'span_latin_expanded_text'}
		closedspans {52: 'fontshift_latin_normal', 195: 'span_latin_expanded_text', 227: 'fontshift_latin_italic'}
		balancetest [(False, True, False), (True, False, True)]

		a = '[]κακ<hmu_span_superscript>η</hmu_span_superscript> βου<hmu_span_superscript>λ</hmu_span_superscript>'
		openspans {5: 'span_superscript', 55: 'span_superscript'}
		closedspans {28: 'span_superscript', 78: 'span_superscript'}
		balancetest [(False, True, False)]

		b = []κακ<hmu_span_superscript>η</hmu_span_superscript> β<hmu_span_x>ο<hmu_span_y>υab</hmu_span_x>c<hmu_span_superscript>λ</hmu_span_y></hmu_span_superscript>
		testresult (False, True, False)
		testresult (False, False, True)
		testresult (False, False, True)
		balanced to:
			[]κακ<hmu_span_superscript>η</hmu_span_superscript> β<hmu_span_x>ο<hmu_span_y>υab</hmu_span_y></hmu_span_x><hmu_span_y>c<hmu_span_superscript>λ</hmu_span_superscript></hmu_span_y><hmu_span_superscript></hmu_span_superscript>

		"""

		if self._tagsalreadyrational():
			# that is, your HipparchiaBuilder settings mood executing this code here and now
			return

		line = self.markedup
		opener = dbWorkLine.hmuformattingopener
		closer = dbWorkLine.hmuformattingcloser

		openings = list(re.finditer(opener, line))
		openspans = {x.span()[0]: '{a}_{b}'.format(a=x.group(1), b=x.group(2)) for x in openings}

		closings = list(re.finditer(closer, line))
		closedspans = {x.span()[0]: '{a}_{b}'.format(a=x.group(1), b=x.group(2)) for x in closings}

		balancetest = list()
		invalidpattern = (False, False, True)

		if len(openspans) == len(closedspans) and len(openspans) > 1:
			# print('openspans', openspans)
			# print('closedspans', closedspans)

			rng = range(len(openspans) - 1)
			okeys = sorted(openspans.keys())
			ckeys = sorted(closedspans.keys())
			# test 1: a problem if the next open ≠ this close and next open position comes before this close position
			#   	open: {0: 'span_expanded_text', 24: 'fontshift_greek_smallerthannormal'}
			# 		closed: {76: 'span_expanded_text', 123: 'fontshift_greek_smallerthannormal'}
			# test 2: succeed if the next open comes after the this close AND the this set of tags match
			#       open {18: 'fontshift_latin_normal', 81: 'fontshift_latin_italic', 150: 'span_latin_expanded_text'}
			# 		closed {52: 'fontshift_latin_normal', 195: 'span_latin_expanded_text', 227: 'fontshift_latin_italic'}
			# test 3: succeed if the next open comes before the previous close

			testone = [not (openspans[okeys[x + 1]] != closedspans[ckeys[x]]) and (okeys[x + 1] < ckeys[x]) for x in rng]
			testtwo = [okeys[x + 1] > ckeys[x] and openspans[okeys[x]] == closedspans[ckeys[x]] for x in rng]
			testthree = [okeys[x + 1] < ckeys[x] for x in rng]

			balancetest = [(testone[x], testtwo[x], testthree[x]) for x in rng]
			# print('balancetest', balancetest)

		if invalidpattern in balancetest:
			# print('{a} needs balancing:\n\t{b}'.format(a=str(), b=line))
			modifications = list()
			balancetest.reverse()
			itemnumber = 0
			while balancetest:
				testresult = balancetest.pop()
				if testresult == invalidpattern:
					needinsertionat = ckeys[itemnumber]
					insertionreopentag = openings[itemnumber + 1].group(0)
					insertionclosetag = re.sub(r'<', r'</', openings[itemnumber + 1].group(0))
					modifications.append({'item': itemnumber,
					                      'position': needinsertionat,
					                      'closetag': insertionclosetag,
					                      'opentag': insertionreopentag})
				itemnumber += 1

			newline = str()
			placeholder = 0
			for m in modifications:
				item = m['item']
				newline += line[placeholder:m['position']]
				newline += m['closetag']
				newline += closings[item].group(0)
				newline += m['opentag']
				placeholder = m['position'] + len(closings[item].group(0))
			newline += line[placeholder:]

			# print('{a} balanced to:\n\t{b}'.format(a=str(), b=newline))
			self.markedup = newline
