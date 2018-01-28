# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
from server.formatting.betacodeescapes import andsubstitutes
from server.formatting.wordformatting import attemptsigmadifferentiation, forcelunates
from server.formatting.wordformatting import avoidsmallvariants


class dbAuthor(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	
		
	CREATE TABLE public.authors (
	    universalid character(6) COLLATE pg_catalog."default",
	    language character varying(10) COLLATE pg_catalog."default",
	    idxname character varying(128) COLLATE pg_catalog."default",
	    akaname character varying(128) COLLATE pg_catalog."default",
	    shortname character varying(128) COLLATE pg_catalog."default",
	    cleanname character varying(128) COLLATE pg_catalog."default",
	    genres character varying(512) COLLATE pg_catalog."default",
	    recorded_date character varying(64) COLLATE pg_catalog."default",
	    converted_date integer,
	    location character varying(128) COLLATE pg_catalog."default"
	)
	
	"""

	def __init__(self, universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date,
				 converted_date, location):

		self.universalid = universalid
		self.language = language
		self.idxname = idxname
		self.akaname = akaname
		self.shortname = shortname
		self.cleanname = cleanname
		self.genres = genres
		self.recorded_date = recorded_date
		self.converted_date = converted_date
		self.location = location
		self.authornumber = universalid[2:]
		self.listofworks = list()
		self.name = akaname
		self.id = universalid

	def earlier(self, other):
		return self.converted_date < other

	def later(self, other):
		return self.converted_date > other

	def atorearlier(self, other):
		return self.converted_date <= other

	def atorlater(self, other):
		return self.converted_date >= other

	def datefallsbetween(self, minimum, maximum):
		return minimum <= self.converted_date <= maximum

	def floruitis(self, other):
		return self.converted_date == other

	def floruitisnot(self, other):
		return self.converted_date != other

	def addwork(self, work):
		self.listofworks.append(work)

	def listworkids(self):
		workids = list()
		for w in self.listofworks:
			workids.append(w.universalid)

		return workids


class dbOpus(object):
	"""
	Created out of the DB info, not the IDT vel sim
	Initialized straight out of a DB read
	note the efforts to match a simple Opus, but the fit is potentially untidy
	it is always going to be important to know exactly what kind of object you are handling
	
	CREATE TABLE public.works (
		universalid character(10) COLLATE pg_catalog."default",
		title character varying(512) COLLATE pg_catalog."default",
		language character varying(10) COLLATE pg_catalog."default",
		publication_info text COLLATE pg_catalog."default",
		levellabels_00 character varying(64) COLLATE pg_catalog."default",
		levellabels_01 character varying(64) COLLATE pg_catalog."default",
		levellabels_02 character varying(64) COLLATE pg_catalog."default",
		levellabels_03 character varying(64) COLLATE pg_catalog."default",
		levellabels_04 character varying(64) COLLATE pg_catalog."default",
		levellabels_05 character varying(64) COLLATE pg_catalog."default",
		workgenre character varying(32) COLLATE pg_catalog."default",
		transmission character varying(32) COLLATE pg_catalog."default",
		worktype character varying(32) COLLATE pg_catalog."default",
		provenance character varying(64) COLLATE pg_catalog."default",
		recorded_date character varying(64) COLLATE pg_catalog."default",
		converted_date integer,
		wordcount integer,
		firstline integer,
		lastline integer,
		authentic boolean
	)
	
	
	"""

	def __init__(self, universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02,
				 levellabels_03, levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance,
				 recorded_date, converted_date, wordcount, firstline, lastline, authentic):
		self.universalid = universalid
		self.worknumber = universalid[7:]
		self.authorid = universalid[0:6]
		self.title = title
		self.language = language
		self.publication_info = publication_info
		self.levellabels_00 = levellabels_00
		self.levellabels_01 = levellabels_01
		self.levellabels_02 = levellabels_02
		self.levellabels_03 = levellabels_03
		self.levellabels_04 = levellabels_04
		self.levellabels_05 = levellabels_05
		self.workgenre = workgenre
		self.transmission = transmission
		self.worktype = worktype
		self.provenance = provenance
		self.recorded_date = recorded_date
		self.converted_date = converted_date
		self.wordcount = wordcount
		self.starts = firstline
		self.ends = lastline
		self.authentic = authentic
		self.name = title
		try:
			self.length = lastline - firstline
		except:
			self.length = -1
		self.structure = dict()
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label != '' and label != None:
				self.structure[idx] = label

		availablelevels = 1
		for level in [self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]:
			if level and level != '':
				availablelevels += 1
		self.availablelevels = availablelevels

	def citation(self):
		if self.universalid[0:2] not in ['in', 'dp', 'ch']:
			cit = []
			levels = [self.levellabels_00, self.levellabels_01, self.levellabels_02, self.levellabels_03,
					  self.levellabels_04, self.levellabels_05]
			for l in range(0, self.availablelevels):
				cit.append(levels[l])
			cit.reverse()
			cit = ', '.join(cit)
		else:
			cit = '(face,) line'

		return cit

	def earlier(self, other):
		return self.converted_date < other

	def later(self, other):
		return self.converted_date > other

	def datefallsbetween(self, minval, maxval):
		return minval <= self.converted_date <= maxval

	def bcedate(self):
		if self.converted_date:
			# converted_date is a float
			cds = str(self.converted_date)
			if self.converted_date < 1:
				return '{d} BCE'.format(d=cds[1:])
			elif self.converted_date < 1500:
				return '{d} CE'.format(d=cds)
			else:
				return 'date unknown'
		else:
			return 'date unknown'

	def isnotliterary(self):
		"""
		a check to see if you come from something other than 'gr' or 'lt'
		:return: 
		"""

		if self.universalid[0:2] in ['in', 'dp', 'ch']:
			return True
		else:
			return False

	def isliterary(self):
		"""
		a check to see if you come from 'gr' or 'lt'
		:return: 
		"""

		if self.universalid[0:2] in ['gr', 'lt']:
			return True
		else:
			return False

	def lines(self):
		return set(range(self.starts, self.ends+1))


class dbWorkLine(object):
	"""
	an object that corresponds to a db line
	
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
	
	"""

	def __init__(self, wkuinversalid, index, level_05_value, level_04_value, level_03_value, level_02_value,
				 level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words,
				 annotations):

		self.wkuinversalid = wkuinversalid[:10]
		self.authorid = wkuinversalid[:6]
		self.index = index
		self.l5 = level_05_value
		self.l4 = level_04_value
		self.l3 = level_03_value
		self.l2 = level_02_value
		self.l1 = level_01_value
		self.l0 = level_00_value
		self.accented = marked_up_line
		self.polytonic = accented_line
		self.stripped = stripped_line
		self.annotations = annotations
		self.universalid = self.wkuinversalid+'_LN_'+str(index)
		self.hyphenated = hyphenated_words
		if len(self.hyphenated) > 1:
			self.hashyphenated = True
		else:
			self.hashyphenated = False

		if self.accented is None:
			self.accented = ''
			self.stripped = ''

		if hipparchia.config['RESTOREMEDIALANDFINALSIGMA'] == 'yes':
			self.accented = attemptsigmadifferentiation(self.accented)
		if hipparchia.config['FORCELUNATESIGMANOMATTERWHAT'] == 'yes':
			self.accented = forcelunates(self.accented)

	def uncleanlocus(self):
		"""
		call me to get a formatted citation: "3.2.1"

		but funky chars might be in here...

		:param self:
		:return:
		"""

		if self.wkuinversalid[0:2] not in ['in', 'dp', 'ch']:
			loc = [lvl for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5] if str(lvl) != '-1']
			loc.reverse()
			citation = '.'.join(loc)
		else:
			# papyrus and inscriptions are wonky: usually they have just a recto, but sometimes they have something else
			# only mark the 'something else' version
			if self.l1 != 'recto':
				citation = self.l1 + ' ' + self.l0
			else:
				citation = self.l0

		return citation

	def locus(self):
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

	def anchoredlocus(self):
		"""

		build a clickable url for the locus and wrap the locus in it:

			<indexedlocation id="gr0032w008_LN_30784">1.4.4</indexedlocation>

		:return:
		"""

		template = '<indexedlocation id="{wk}_LN_{idx}">{loc}</indexedlocation>'

		return template.format(wk=self.wkuinversalid, idx=self.index, loc=self.locus())

	def shortlocus(self):
		"""
		try to get a short citation that drops the lvl0 info: "3.2"
		useful for tagging level shifts without constantly seeing 'line 1'
		:return:
		"""
		loc = list()
		for lvl in [self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1' and (self.wkuinversalid[0:2] not in ['in', 'dp', 'ch'] and lvl != 'recto'):
				loc.append(lvl)
		loc.reverse()

		if not loc:
			citation = self.locus()
		else:
			citation = '.'.join(loc)

		return citation

	def uncleanlocustuple(self):
		"""
		call me to get a citation tuple in 0-to-5 order
		:return:
		"""
		cit = []
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
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

	def samelevelas(self, other):
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci have to be from the same work
		:param self:
		:param other:
		:return:
		"""
		if self.wkuinversalid == other.wkuinversalid and self.l5 == other.l5 and self.l4 == other.l4 and \
						self.l3 == other.l3 and self.l2 == other.l2 and self.l1 == other.l1:
			return True
		else:
			return False

	def equivalentlevelas(self, other):
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci do not have to be from the same work
		:param self:
		:param other:
		:return:
		"""
		if self.l5 == other.l5 and self.l4 == other.l4 and self.l3 == other.l3 and self.l2 == other.l2 and \
						self.l1 == other.l1:
			return True
		else:
			return False

	def toplevel(self):
		top = 0
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				top += 1
			else:
				return top

		# should not need this, but...
		return top

	def unformattedline(self):
		"""
		remove markup from contents
		:return:
		"""

		markup = re.compile(r'(<.*?>)')
		nbsp = re.compile(r'&nbsp;')

		unformatted = re.sub(markup, r'', self.accented)
		unformatted = re.sub(nbsp, r'', unformatted)

		return unformatted

	def showlinehtml(self):
		"""

		make HTML of marked up line visible

		:return:
		"""

		markup = re.compile(r'(<)(.*?)(>)')
		left = '<smallcode>&lt;'
		right = '&gt;</smallcode>'

		visiblehtml = re.sub(markup, left+r'\2'+right, self.accented)

		return visiblehtml

	def wordcount(self):
		"""
		return a wordcount
		"""

		line = self.stripped
		return len([x for x in line.split(' ') if x])

	def wordlist(self, version):
		"""
		return a list of words in the line; will include the full version of a hyphenated last word
		:param version:
		:return:
		"""
		wordlist = []

		if version in ['polytonic', 'stripped']:
			line = getattr(self, version)
			# Non-breaking space needs to go
			line = re.sub(r'\xa0', ' ', line)
			wordlist = [w for w in line.split(' ') if w]

		return wordlist

	def lastword(self, version):
		last = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version).split(' ')
			last = line[-1]
		return last

	def firstword(self, version):
		first = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version).split(' ')
			first = line[0]
		return first

	def allbutlastword(self, version):
		"""
		return the line less its final word
		"""
		allbutlastword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			line = line.split(' ')
			allbutlast = line[:-1]
			allbutlastword = ' '.join(allbutlast)

		return allbutlastword

	def allbutfirstword(self, version):
		"""
		return the line less its first word
		"""
		allbutfirstword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(<.*?>)', r'', line)
			line = line.split(' ')
			allbutfirst = line[1:]
			allbutfirstword = ' '.join(allbutfirst)

		return allbutfirstword

	def allbutfirstandlastword(self, version):
		"""
		terun the line lest the first and last words (presumably both are hypenated)
		:param version:
		:return:
		"""
		allbutfirstandlastword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(<.*?>)', r'', line)
			line = line.split(' ')
			middle = line[1:-1]
			allbutfirstandlastword = ' '.join(middle)

		return allbutfirstandlastword

	def insetannotations(self):
		"""

		<hmu_metadata_notes value="Non. 104M" />

		note that in 'Gel. &3N.A.& 20.3.2' the '&3' turns on italics

		:return:
		"""

		pattern = re.compile(r'<hmu_metadata_notes value="(.*?)" />')
		ands = re.compile(r'&(\d{1,2})(.*?)(&\d?)')

		notes = re.findall(pattern, self.accented)
		notes = [re.sub(ands, andsubstitutes, n) for n in notes]

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
			bracketfinder = {
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

		theline = self.accented
		for t in editorialcontinuationdict.keys():
			try:
				bracketfinder[t]
			except:
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

	def bracketopenedbutnotclosed(self, btype='square', bracketfinder=None):
		"""

		return True if you have 'abcd[ef ghij' and so need to continue marking editorial material

		note that only 'square' really works unless/until candomultilinecontinuation expands in markeditorialinsersions()
		this will actually be tricky since the code was built only to keep track of one continuing item...

		:return:
		"""

		if not bracketfinder:
			bracketfinder = {
				'square': {'regex': re.compile(r'\[[^\]]{0,}$'),
				            'exceptions': [re.compile(r'\[(ϲτρ|ἀντ)\. .\.'), re.compile(r'\[ἐπῳδόϲ')]},
				'round': {'regex': re.compile(r'\([^\)]{0,}$')},
				'angled': {'regex': re.compile(r'⟨[^⟩]{0,}$')},
				'curly': {'regex': re.compile(r'\{[^\}]{0,}$')},
				}

		openandnotclose = bracketfinder[btype]['regex']

		try:
			falsify = [re.search(e, self.accented) for e in bracketfinder[btype]['exceptions']]
		except:
			falsify = [None]

		if re.search(openandnotclose, self.accented) and True not in falsify:
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
			bracketfinder = {
				'square': {'c': re.compile(r'\]')},
				'round': {'c': re.compile(r'\)')},
				'angled': {'c': re.compile(r'⟩')},
				'curly': {'c': re.compile(r'\}')},
			}

		close = bracketfinder[btype]['c']
		if re.search(close, self.accented):
			return True
		else:
			return False
