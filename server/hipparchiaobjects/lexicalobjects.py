# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
from string import punctuation
from typing import List

from bs4 import BeautifulSoup
from flask import session

from server.formatting.abbreviations import deabbreviateauthors
from server.formatting.wordformatting import stripaccents
from server.listsandsession.genericlistfunctions import polytonicsort


class dbDictionaryEntry(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE greek_dictionary (
	    entry_name character varying(64),
	    metrical_entry character varying(64),
	    unaccented_entry character varying(64),
	    id_number integer,
		pos character varying(32),
	    translations text,
	    entry_body text
	);

	CREATE TABLE latin_dictionary (
	    entry_name character varying(64),
	    metrical_entry character varying(64),
	    id_number integer,
	    entry_key character varying(64),
	    pos character varying(32),
	    translations text,
	    entry_body text
	);

	Latin only: entry_key
	Greek only: unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, pos, translations, entry_body):
		self.entry = entry_name
		self.metricalentry = metrical_entry
		self.id = id_number
		self.translations = translations.split(' ‖ ')
		self.pos = pos.split(' ‖ ')
		self.body = entry_body
		self.soup = BeautifulSoup(self.body, 'html.parser')
		self.nextentryid = -1
		self.preventryid = -1
		self.nextentry = '(none)'
		self.preventry = '(none)'
		self.authorlist = list()
		self.quotelist = list()
		self.senselist = list()

		if re.search(r'[a-z]', self.entry):
			self.usedictionary = 'latin'
			self.translationlabel = 'hi'
		else:
			self.usedictionary = 'greek'
			self.translationlabel = 'tr'

	@staticmethod
	def isgreek():
		raise NotImplementedError

	@staticmethod
	def islatin():
		raise NotImplementedError

	def runbodyxrefsuite(self):
		# add dictionary clicks to "cf.", etc. in the entry body
		raise NotImplementedError

	def isagloss(self):
		fingerprint = re.compile(r'<author>Gloss\.</author>')
		if re.search(fingerprint, self.body):
			return True
		else:
			return False

	def generateauthorsummary(self) -> List:
		"""

		returns a collection of lists: all authors to be found in an entry

		entryxref allows you to trim 'quotes' that are really just morphology examples

		for example, ἔρχομαι will drop 12 items via this check

		:param fullentry:
		:param lang:
		:param translationlabel:
		:param lemmaobject:
		:return:
		"""

		authorlist = self.soup.find_all('author')
		authorlist = list(set(authorlist))
		# the list is composed of objj. that are <class 'bs4.element.Tag'>
		authorlist[:] = [value.string for value in authorlist]
		notin = ['id.', 'ib.', 'Id.']
		authorlist[:] = [value for value in authorlist if value not in notin]
		authorlist.sort()
		authorlist = [deabbreviateauthors(au, self.usedictionary) for au in authorlist]

		if session['authorssummary'] == 'yes':
			authorlist = ['{n} authors'.format(n=len(authorlist))]

		return authorlist

	def generatesensessummary(self) -> List:
		listofsenses = self.soup.find_all(self.translationlabel)
		exclusions = ['ab', 'de', 'ex', 'ut', 'nihil', 'quam', 'quid']
		try:
			listofsenses = [s.string for s in listofsenses]
			listofsenses = [s for s in listofsenses if '.' not in s]
			listofsenses = [s for s in listofsenses if s not in exclusions]
		except:
			listofsenses = list()

		# so 'go' and 'go,' are not both on the list
		depunct = '[{p}]$'.format(p=re.escape(punctuation))
		listofsenses = [re.sub(depunct, '', s) for s in listofsenses]
		listofsenses = [re.sub(r'^To', 'to', s) for s in listofsenses]
		listofsenses = list(set(listofsenses))
		listofsenses.sort()

		if session['sensesummary'] == 'yes':
			listofsenses = ['{n} senses'.format(n=len(listofsenses))]

		return listofsenses

	def generatequotesummary(self, lemmaobject=None) -> List:
		quotelist = self.soup.find_all('quote')
		quotelist = [q.string for q in quotelist]

		# many of the 'quotes' are really just forms of the word
		# trim these
		if lemmaobject:
			morphologylist = lemmaobject.formlist
		else:
			morphologylist = list()

		quotelist = [x for x in quotelist if x not in morphologylist]
		quotelist = polytonicsort(quotelist)

		if session['quotesummary'] == 'yes':
			quotelist = ['{n} quotes'.format(n=len(quotelist))]

		return quotelist

	def returnsensehierarchy(self) -> List[str]:
		"""

		look for all of the senses of a work in its dictionary entry

		return them as a list of definitions with HTML <p> attributes that set them in their proper hierarchy:
			A ... A1 ... A1b ...

		"""
		sensing = re.compile(r'<sense.*?/sense>')
		senses = re.findall(sensing, self.body)
		leveler = re.compile(r'<sense\s.*?level="(.*?)".*?>')
		nummer = re.compile(r'<sense.*?\sn="(.*?)".*?>')
		numberedsenses = list()
		i = 0

		for sense in senses:
			i += 1
			lvl = re.search(leveler, sense)
			num = re.search(nummer, sense)
			# note that the two dictionaries do not necc agree with one another (or themselves) when it comes to nesting labels
			if re.search(r'[A-Z]', num.group(1)):
				paragraphlevel = '1'
			elif re.search(r'[0-9]', num.group(1)):
				paragraphlevel = '3'
			elif re.search(r'[ivx]', num.group(1)):
				paragraphlevel = '4'
			elif re.search(r'[a-hj-w]', num.group(1)):
				paragraphlevel = '2'
			else:
				paragraphlevel = '1'

			try:
				rewritten = '<p class="level{pl}"><span class="levellabel{lv}">{nm}</span>{sn}</p>\n'.format(
					pl=paragraphlevel, lv=lvl.group(1), nm=num.group(1), sn=sense)
			except:
				print('exception in grabsenses() at sense number:', i)
				rewritten = ''
			numberedsenses.append(rewritten)

		return numberedsenses

	@staticmethod
	def entrywordcleaner(foundword, substitutionstring):
		# example substitute: r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>'
		stripped = stripaccents(foundword)
		newstring = substitutionstring.format(clean=stripped, dirty=foundword)
		# print('entrywordcleaner()', foundword, stripped)
		return newstring


class dbGreekWord(dbDictionaryEntry):
	"""

	an object that corresponds to a db line

	differs from Latin in self.language and unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, pos, translations, entry_body, unaccented_entry):
		self.language = 'Greek'
		self.unaccented_entry = unaccented_entry
		super().__init__(entry_name, metrical_entry, id_number, pos, translations, entry_body)
		self.entry_key = None

	@staticmethod
	def isgreek():
		return True

	@staticmethod
	def islatin():
		return False

	def runbodyxrefsuite(self):
		# modify self.body to add clicks to "cf" words, etc
		self._greekgreaterthanlessthan()
		self._greekxmltagwrapper('ref')
		self._greekxmltagwrapper('etym')
		self._greeksvfinder()
		self._greekequivalentformfinder()
		self._cffinder()

	def _greekgreaterthanlessthan(self):
		# but this is really a builder problem... [present in v.1.0 and below]
		self.body = re.sub(r'&λτ;', r'&lt;', self.body)
		self.body = re.sub(r'&γτ;', r'&gt;', self.body)

	def _greekirregularvowelquantities(self):
		# also a builder problem: δαμευέϲϲθο_ vs δαμευέϲϲθο̄
		# same story with ε for η in dialects/inscriptions
		# but note that it would take a while to get all of the accent possibilities in there
		pass

	def _greekxmltagwrapper(self, tag):
		"""

		sometimes you have "<tag>WORD</tag>" and sometimes you have "<tag>WORD.</tag>"

		note the potential false-positive finds with things like:

			'<etym lang="greek" opt="n">ἀνα-</etym>'

		The tag will generate a hit but the '-' will disqualify it.

		Many tags are a mess in the XML. 'foreign' is used in all sorts of ways, etc.

		bs4 screws things up if you try to use it because it can swap item order:
			in text:    '<ref targOrder="U" lang="greek">γαιών</ref>'
			bs4 return: '<ref lang="greek" targorder="U">γαιών</ref>'

		:return:
		"""

		# don't need to strip the accents with a greek word; do need to strip longs and shorts in a latin word

		markupfinder = re.compile(r'(<{t}.*?>)(\w+)(\.?<.*?{t}>)'.format(t=tag))

		self.body = re.sub(markupfinder, r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3', self.body)

	def _greeksvfinder(self):
		fingerprint = r'(<abbr>v\.</abbr> sub <foreign lang="greek">)(\w+)(</foreign>)'
		replacement = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
		self.body = re.sub(fingerprint, replacement, self.body)

	def _greekequivalentformfinder(self):
		fingerprints = [r'(used for <foreign lang="greek">)(\w+)(</foreign>)',
		                r'(Lat. <tr opt="n">)(\w+)(</tr>)']
		replacement = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
		for f in fingerprints:
			self.body = re.sub(f, replacement, self.body)

	def _cffinder(self):
		# such as: <foreign lang="greek">εὐθύϲ</foreign> (q. v.).
		fingerprints = [r'(cf. <foreign lang="greek">)(\w+)(</foreign>)',
		                r'(<foreign lang="greek">)(\w+)(</foreign> \(q\. v\.\))']
		replacement = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
		for f in fingerprints:
			self.body = re.sub(f, replacement, self.body)


class dbLatinWord(dbDictionaryEntry):
	"""

	an object that corresponds to a db line

	differs from Greek in self.language and unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, pos, translations, entry_body, entry_key):
		self.language = 'Latin'
		self.unaccented_entry = None
		super().__init__(entry_name, metrical_entry, id_number, pos, translations, entry_body)
		self.entry_key = entry_key

	@staticmethod
	def isgreek():
		return False

	@staticmethod
	def islatin():
		return True

	def runbodyxrefsuite(self):
		# modify self.body to add clicks to "cf" words, etc
		self._latinetymologyfinder()
		self._latinsubvidefinder()
		self._latinsynonymfinder()

	def _latinsubvidefinder(self):
		"""

		make "balneum" clickable if you are told to "v. balneum"

		sample entries:

			<orth extent="full" lang="la" opt="n">bălĭnĕum</orth>, v. balneum <sense id="n4869.0" n="I" level="1" opt="n"><hi rend="ital">init.</hi></sense>

			<orth extent="full" lang="la" opt="n">balneae</orth>, v. balneum.

		note that the following 's.v.' is not quite the same beast...

			<lbl opt="n">s.v.</lbl> <ref targOrder="U" lang="greek">ἐπευνακταί</ref>

		then we have the following where you need to clean the word before searching:
			<orth extent="full" lang="la" opt="n">fĕrē</orth>, q. v.

		:return:
		"""

		xreffinder = list()
		xreffinder.append(re.compile(r'(v\. )(\w+)( <sense)'))
		xreffinder.append(re.compile(r'(v\. )(\w+)(\.)$'))
		xreffinder.append(re.compile(r'(\(cf\. )(\w+)(\))'))
		xreffinder.append(re.compile(r'(; cf\. )(\w+)(\))'))
		xreffinder.append(re.compile(r'(<etym opt="\w">\d\. )(\w+)(, q\. v\.)'))
		xreffinder.append(re.compile(r'(from )(\w+)(</etym>)'))
		# xreffinder.append(re.compile(r'<lbl opt="n">(s\.v\.)</lbl> <ref targOrder="U" lang="greek">(\w+)</ref>()'))

		sv = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'

		for x in xreffinder:
			self.body = re.sub(x, sv, self.body)

		findandeaccentuate = re.compile(r'<orth extent="full" lang="\w+" opt="\w">(\w+)</orth>, q. v.')
		qv = r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>, q. v.'

		self.body = re.sub(findandeaccentuate, lambda x: self.entrywordcleaner(x.group(1), qv), self.body)

	def _latinsynonymfinder(self):
		fingerprint = r'(\(syn\.:{0,} )(.*?)([);])'
		self.body = re.sub(fingerprint, lambda x: self._entrylistsplitter(x), self.body)

	@staticmethod
	def _entrylistsplitter(matchgroup):
		entrytemplate = r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>'
		head = matchgroup.group(1)
		tail = matchgroup.group(3)

		synonymns = matchgroup.group(2)
		synonymns = synonymns.split(', ')

		substitutes = [entrytemplate.format(clean=stripaccents(s), dirty=s) for s in synonymns]
		substitutes = ', '.join(substitutes)

		newstring = head + substitutes + tail

		return newstring

	def _latinetymologyfinder(self):
		"""

		make "balneum" clickable if you are told a word comes from it.

		sample from entry:

			<etym opt="n">balneum</etym>

			<gen opt="n">m.</gen>, = βούβαλοϲ,

		note problem with:

			<etym opt="n">Spanish</etym>

		:return:
		"""

		xreffinder = list()
		xreffinder.append(re.compile(r'(<etym opt=".">)(\w+)(</etym>)'))
		xreffinder.append(re.compile(r'(= )(\w+)(,)'))
		xreffinder.append(re.compile(r'(cf\. Gr\. )(\w+)(,)'))

		sv = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
		for x in xreffinder:
			self.body = re.sub(x, sv, self.body)
