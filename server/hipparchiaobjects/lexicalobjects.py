# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from flask import session

from server import hipparchia
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
		self.body = self._spacebetween(self._xmltohtmlquickconversions(entry_body))
		if hipparchia.config['DEABBREVIATEAUTHORS'] != 'no':
			self._deabbreviateauthornames()
		self.xrefspresent = False
		self.xmlhasbeenconverted = False
		self.havesensehierarchy = False
		self.haveclickablelookups = False
		self.nextentryid = -1
		self.preventryid = -1
		self.nextentry = '(none)'
		self.preventry = '(none)'
		self.authorlist = list()
		self.quotelist = list()
		self.senselist = list()
		self.flaggedsenselist = list()
		self.flagauthor = None

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

	def _deabbreviateauthornames(self):
		afinder = re.compile(r'<author>(.*?)</author>')
		if self.isgreek():
			d = 'greek'
		elif self.islatin():
			d = 'latin'
		self.body = re.sub(afinder, lambda x: self._deabbreviateauthornamewrapper(x.group(1), d), self.body)

	@staticmethod
	def _deabbreviateauthornamewrapper(foundauthor: str, dictionary: str) -> str:
		author = deabbreviateauthors(foundauthor, dictionary)
		wrapper = '<author>{au}</author>'.format(au=author)
		return wrapper

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
		afinder = re.compile(r'<author>(.*?)</author>')
		authorlist = re.findall(afinder, self.body)
		authorlist = list(set(authorlist))
		notin = ['id.', 'ib.', 'Id.']
		authorlist[:] = [value for value in authorlist if value not in notin]
		authorlist.sort()
		authorlist = [deabbreviateauthors(au, self.usedictionary) for au in authorlist]

		if session['authorssummary']:
			aa = len(authorlist)
			if aa != 1:
				authorlist = ['{n} authors'.format(n=aa)]
			else:
				authorlist = ['1 author']

		return authorlist

	def generateflaggedsummary(self) -> List:
		listofsenses = self.flaggedsenselist
		listofsenses = [s[0].upper() + s[1:] for s in listofsenses if len(s) > 1]
		listofsenses.sort()
		if False:
			ss = len(listofsenses)
			if ss != 1:
				listofsenses = ['{n} senses'.format(n=ss)]
			else:
				listofsenses = ['1 sense']

		return listofsenses

	def generatesensessummary(self) -> List:
		### this parsing code got moved into the builder ###

		# listofsenses = self.soup.find_all(self.translationlabel)
		# exclusions = ['ab', 'de', 'ex', 'ut', 'nihil', 'quam', 'quid']
		# try:
		# 	listofsenses = [s.string for s in listofsenses]
		# 	listofsenses = [s for s in listofsenses if '.' not in s]
		# 	listofsenses = [s for s in listofsenses if s not in exclusions]
		# except:
		# 	listofsenses = list()
		#
		# # so 'go' and 'go,' are not both on the list
		# depunct = '[{p}]$'.format(p=re.escape(punctuation))
		# listofsenses = [re.sub(depunct, '', s) for s in listofsenses]
		# listofsenses = [re.sub(r'^To', 'to', s) for s in listofsenses]
		# listofsenses = list(set(listofsenses))
		# listofsenses.sort()

		listofsenses = self.translations
		listofsenses = [s[0].upper() + s[1:] for s in listofsenses if len(s) > 1]
		listofsenses.sort()

		if session['sensesummary']:
			ss = len(listofsenses)
			if ss != 1:
				listofsenses = ['{n} senses'.format(n=ss)]
			else:
				listofsenses = ['1 sense']

		return listofsenses

	def generatequotesummary(self, lemmaobject=None) -> List:
		qfinder = re.compile(r'<quote lang="\w+">(.*?)</quote>')
		quotelist = re.findall(qfinder, self.body)

		# many of the 'quotes' are really just forms of the word
		# trim these
		if lemmaobject:
			morphologylist = lemmaobject.formlist
		else:
			morphologylist = list()

		quotelist = [x for x in quotelist if x not in morphologylist]
		quotelist = polytonicsort(quotelist)

		if session['quotesummary']:
			qq = len(quotelist)
			if qq != 1:
				quotelist = ['{n} quotes'.format(n=qq)]
			else:
				quotelist = ['1 quote']

		return quotelist

	def grabheadmaterial(self) -> str:
		"""
		find the information at the top of a dictionary entry: used to get the basic info about the word
		:param fullentry:
		:return:
		"""

		# after formatting a newline marks the first paragraph of the body
		h = re.search(r'\n', self.body)
		try:
			return self.body[:h.end()]
		except AttributeError:
			return str()

	def grabnonheadmaterial(self) -> str:
		"""
		find the information at the top of a dictionary entry: used to get the basic info about the word
		:param fullentry:
		:return:
		"""

		# after formatting a newline marks the first paragraph of the body
		h = re.search(r'\n', self.body)
		if not h:
			microentry = '<p></p>\n{b}'.format(b=self.body)
			return microentry

		try:
			return self.body[h.end():]
		except AttributeError:
			return str()

	def insertclickablelookups(self):
		"""

		in:
			<bibl n="Perseus:abo:tlg,0019,003:1214" default="NO" valid="yes">

		out:
			<bibl id="perseus/gr0019/003/1214" default="NO" valid="yes">

		:return:
		"""

		# first retag the items that should not click-to-browse

		biblios = re.compile(r'(<bibl.*?)(.*?)(</bibl>)')
		bibs = re.findall(biblios, self.body)
		bdict = dict()

		for bib in bibs:
			if 'Perseus:abo' not in bib[1]:
				# OR: if 'Perseus:abo' not in bib[1] and 'urn:cts:latinLit:phi' not in bib[1]:
				head = '<unclickablebibl'
				tail = '</unclickablebibl>'
			else:
				head = bib[0]
				tail = bib[2]
			bdict[''.join(bib)] = head + bib[1] + tail

		# print('here',bdict)
		htmlentry = self.body
		for key in bdict.keys():
			htmlentry = re.sub(key, bdict[key], htmlentry)

		# now do the work of finding the lookups
		# latin old style: <bibl n="Perseus:abo:phi,0550,001:3:765" default="NO" valid="yes">
		# latin new styleA: <bibl n="urn:cts:latinLit:phi0550.phi001:3:765">
		# latin new styleB: <bibl n="urn:cts:latinLit:phi1276.phi001.perseus-lat1:1:90"><author>Juv.</author> 1, 90</bibl>
		# and there are other oddities to the new style, including arrant author ids
		# accordingly not building with that data at the moment
		tlgfinder = re.compile(r'n="Perseus:abo:tlg,(\d\d\d\d),(\d\d\d):(.*?)"')
		phifinder = re.compile(r'n="Perseus:abo:phi,(\d\d\d\d),(\d\d\d):(.*?)"')
		# diofindera = re.compile(r'n="urn:cts:latinLit:phi(\d\d\d\d)\.phi(\d\d\d):(.*?)"')
		# diofinderb = re.compile(r'n="urn:cts:latinLit:phi(\d\d\d\d)\.phi(\d\d\d)\.perseus-lat\d:(.*?)"')

		clickableentry = re.sub(tlgfinder, r'id="perseus/gr\1/\2/\3"', htmlentry)
		clickableentry = re.sub(phifinder, r'id="perseus/lt\1/\2/\3"', clickableentry)
		# clickableentry = re.sub(diofindera, r'id="perseus/lt\1/\2/\3"', clickableentry)
		# clickableentry = re.sub(diofinderb, r'id="perseus/lt\1/\2/\3"', clickableentry)

		if self.flagauthor:
			myid = r'id="perseus/{a}'.format(a=self.flagauthor)
			clickableentry = re.sub(myid, r'class="flagged" ' + myid, clickableentry)
		self.body = clickableentry
		self.haveclickablelookups = True
		return

	def constructsensehierarchy(self):
		"""
		look for all of the senses of a work in its dictionary entry
		return them as a list of definitions with HTML <p> attributes that set them in their proper hierarchy:
			A ... A1 ... A1b ...
		"""

		sensefinder = re.compile(r'<sense.*?/sense>')
		levelfinder = re.compile(r'<sense\s.*?level="(.*?)".*?>')
		numfinder = re.compile(r'<sense.*?\sn="(.*?)".*?>')

		self.body = re.sub(sensefinder, lambda x: self._sensewrapper(x.group(0), levelfinder, numfinder), self.body)
		return

	@staticmethod
	def _sensewrapper(foundsense, levelfinder, numfinder):
		"""
		take a "<sense></sense>" and wrap it in a "<p><span></span><sense></sense></p>" blanket

		pass levelfinder, numfinder to avoid re.compile inside a loop

		:param self:
		:return:
		"""

		template = """
		<p class="level{pl}">
			<span class="levellabel{lv}">{nm}</span>
			{sn}
		</p>"""

		lvl = re.search(levelfinder, foundsense)
		num = re.search(numfinder, foundsense)

		if not lvl or not num:
			return foundsense

		paragraphlevel = lvl.group(1)

		rewritten = template.format(pl=paragraphlevel, lv=lvl.group(1), nm=num.group(1), sn=foundsense)

		# print('wrappedsense\n', rewritten)

		return rewritten

	def xmltohtmlconversions(self):
		"""

		a heavy rewrite of the xml into html

		latintagtypes = {'itype', 'cb', 'sense', 'etym', 'trans', 'tr', 'quote', 'number', 'pos', 'usg', 'bibl', 'hi', 'gen', 'author', 'cit', 'orth', 'pb'}
		greektagtypes = {'itype', 'ref', 'tr', 'quote', 'pos', 'foreign', 'xr', 'gramgrp', 'lbl', 'sense', 'etym', 'gram', 'orth', 'date', 'hi', 'abbr', 'pb', 'biblscope', 'placename', 'bibl', 'title', 'author', 'cit'}

		latinattrtypes = {'extent', 'rend', 'opt', 'lang', 'level', 'id', 'valid', 'type', 'n', 'default'}
		greekattrtypes = {'extent', 'targorder', 'rend', 'opt', 'lang', 'level', 'id', 'type', 'valid', 'n', 'default'}

		built and then abandoned bs4 versions of the various requisite functions
		BUT then learned that bs4 profiles as a *very* slow collection of code:
			'search' and '_find_all' are desperately inefficient
			they make a crazy number of calls and you end up spending 11s on a single large entry

			ncalls  tottime  percall  cumtime  percall filename:lineno(function)
		  4961664    0.749    0.000    1.045    0.000 {built-in method builtins.isinstance}
		   308972    0.697    0.000    1.375    0.000 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:1792(_matches)
		   679678    0.677    0.000    3.214    0.000 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:1766(search)
		     6665    0.430    0.000    0.432    0.000 {method 'sub' of 're.Pattern' objects}
		   296982    0.426    0.000    2.179    0.000 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:1725(search_tag)
		      244    0.352    0.001    3.983    0.016 /Users/erik/hipparchia_venv/lib/python3.7/site-packages/bs4/element.py:571(_find_all)

		:param string:
		:return:
		"""

		tagfinder = re.compile(r'<(.*?)>')
		# notes that dropping 'n' will ruin your ability to generate the sensehierarchy
		dropset = {'default', 'valid', 'extent', 'n', 'opt'}

		propertyfinder = re.compile(r'(\w+)=".*?"')
		pruned = re.sub(tagfinder, lambda x: self._droptagsfromxml(x.group(1), dropset, propertyfinder), self.body)

		preservetags = {'bibl', 'span', 'p', 'dictionaryentry', 'biblscope', 'sense', 'unclickablebibl'}
		pruned = re.sub(tagfinder, lambda x: self._converttagstoclasses(x.group(1), preservetags), pruned)

		closefinder = re.compile(r'</(.*?)>')
		self.body = re.sub(closefinder, lambda x: self._xmlclosetospanclose(x.group(1), preservetags), pruned)

		self.xmlhasbeenconverted = True
		return

	@staticmethod
	def _xmlclosetospanclose(xmlstring: str, leaveuntouched: set) -> str:
		if xmlstring in leaveuntouched:
			newxmlstring = '</{x}>'.format(x=xmlstring)
		else:
			newxmlstring = '</span>'
		return newxmlstring

	@staticmethod
	def _droptagsfromxml(xmlstring: str, dropset: set, propertyfinder) -> str:
		"""

		if
			dropset = {opt}
		&
			xmlstring = 'orth extent="full" lang="greek" opt="n"'

		return is
			'orth extent="full" lang="greek"'

		:param xmlstring:
		:param dropset:
		:return:
		"""

		components = xmlstring.split(' ')
		combined = [components[0]]
		preserved = [c for c in components[1:] if re.search(propertyfinder, c) and re.search(propertyfinder, c).group(1) not in dropset]
		combined.extend(preserved)
		newxml = '<{x}>'.format(x=' '.join(combined))
		return newxml

	@staticmethod
	def _converttagstoclasses(xmlstring: str, leaveuntouched: set) -> str:
		"""
		in:
			<orth extent="full" lang="greek" opt="n">

		out:
			<span class="dictorth dictextent_full dictlang_greek dictopt_n">

		skip all closings: '</orth>'

		be careful about collapsing "id"

		:param xmlstring:
		:return:
		"""

		components = xmlstring.split(' ')
		if components[0] in leaveuntouched or components[0][0] == '/':
			newxml = '<{x}>'.format(x=xmlstring)
			# print('passing on', newxml)
			return newxml
		else:
			finder = re.compile(r'(\w+)="(.*?)"')
			combined = ['dict' + components[0]]
			collapsedtags = [re.sub(finder, r'dict\1_\2', t) for t in components[1:]]
			combined.extend(collapsedtags)
		newxml = '<span class="{x}">'.format(x=' '.join(combined))
		return newxml

	@staticmethod
	def _entrywordcleaner(foundword, substitutionstring):
		# example substitute: r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>'
		stripped = stripaccents(foundword)
		newstring = substitutionstring.format(clean=stripped, dirty=foundword)
		# print('entrywordcleaner()', foundword, stripped)
		return newstring

	@staticmethod
	def _spacebetween(string: str) -> str:
		"""

		some tages should have a space between them

		_xmltohtmlconversions should be run first unless you want to change the fingerprints

		:param string:
		:return:
		"""

		fingerprints = [r'(</author>)(<bibtitle>)',
		                r'(</author>)(<biblScope>)',
		                r'(</bibtitle>)(<biblScope>)',
		                r'(<bibl n=".*?" default="NO">)(<bibtitle>)']
		substitute = r'\1&nbsp;\2'

		for f in fingerprints:
			string = re.sub(f, substitute, string)

		return string

	@staticmethod
	def _xmltohtmlquickconversions(string: str) -> str:
		"""

		some xml items should be rewritten, especially if they collide with html

		:param string:
		:return:
		"""
		swaps = {'title': 'bibtitle'}

		for s in swaps.keys():
			input = r'<{old}>(.*?)</{old}>'.format(old=s)
			output = r'<{new}>\1</{new}>'.format(new=swaps[s])
			string = re.sub(input, output, string)

		return string


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
		if not self.xrefspresent:
			self._greekgreaterthanlessthan()
			self._greekdictionaryentrywrapper('ref')
			self._greekdictionaryentrywrapper('etym')
			self._greeksvfinder()
			self._greekequivalentformfinder()
			self._cffinder()
			self.xrefspresent = True

	def _greekgreaterthanlessthan(self):
		# but this is really a builder problem... [present in v.1.0 and below]
		self.body = re.sub(r'&λτ;', r'&lt;', self.body)
		self.body = re.sub(r'&γτ;', r'&gt;', self.body)

	def _greekirregularvowelquantities(self):
		# also a builder problem: δαμευέϲϲθο_ vs δαμευέϲϲθο̄
		# same story with ε for η in dialects/inscriptions
		# but note that it would take a while to get all of the accent possibilities in there
		pass

	def _greekdictionaryentrywrapper(self, tag):
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
		                r'(<foreign lang="greek">)(\w+)(</foreign> \(q\. v\.\))',
		                r'(<lbl opt="n">=</lbl> <ref targOrder="U" lang="greek">)(\w+)(,)',
		                r'(<gram type="dim" opt="n">Dim. of</gram></gramGrp> <foreign lang="greek">)(\w+)(,{0,1}</foreign>)']
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
		if not self.xrefspresent:
			self._latinxreffinder()
			self._latinsynonymfinder()
			self.xrefspresent = True

	def _latinxreffinder(self):
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

		sv = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
		fingerprints = [r'(v\. )(\w+)( <sense)',
					r'(v\. )(\w+)(\.)$',
					r'(v\. )(\w+)(, [A-Z])',
					r'(\(cf\. )(\w+)(\))',
					r'(; cf\. )(\w+)(\))',
					r'(; cf\.: )(\w+)(\))',
					r'(\(sc. )(\w+)([,)])',
					r'(<etym opt="\w">\d\. )(\w+)(, q\. v\.)',
					r'(from )(\w+)(</etym>)',
					r'(<etym opt=".">)(\w+)(</etym>)',
					r'(<etym opt=".">\d\. )(\w+)(</etym>)',
					r'(<etym opt=".">)(\w+)([;,])',
					r'(= )(\w+)([., ])',
					r'(cf\. Gr\. )(\w+)(,)',
					r'( i\. q\. )(\w+)([),])',
					r'(pure Lat\.)(\w+)([),])',
					r'(\(for )(\w+)(, q\. v\.\))'
					]
		# xreffinder.append(re.compile(r'<lbl opt="n">(s\.v\.)</lbl> <ref targOrder="U" lang="greek">(\w+)</ref>()'))

		xreffinder = [re.compile(f) for f in fingerprints]
		for x in xreffinder:
			self.body = re.sub(x, sv, self.body)

		findandeaccentuate = re.compile(r'<orth extent="full" lang="\w+" opt="\w">(\w+)</orth>, q. v.')
		qv = r'<dictionaryentry id="{clean}">{dirty}</dictionaryentry>, q. v.'

		self.body = re.sub(findandeaccentuate, lambda x: self._entrywordcleaner(x.group(1), qv), self.body)

	def _latinsynonymfinder(self):
		fingerprints = [r'(\(syn\.:{0,} )(.*?)([);])']
		# the next is dangerous because cf. might be a word or a passage: "dux" or "Pliny, Pan 12,1"
		# r'(\(cf\.:{0,} )(.*?)([);])']
		for f in fingerprints:
			self.body = re.sub(f, lambda x: self._entrylistsplitter(x), self.body)

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


class dbColumnorderGreekword(dbGreekWord):
	"""

	the order inside the db lines is not the __init__ order of dbGreekWord()

	hipparchiaDB=# select * from greek_dictionary limit 0;
	entry_name | metrical_entry | unaccented_entry | id_number | pos | translations | entry_body
	------------+----------------+------------------+-----------+-----+--------------+------------
	(0 rows)

	"""
	def __int__(self, entry_name, metrical_entry, unaccented_entry, id_number, pos, translations, entry_body):
		super().__init__(entry_name, metrical_entry, id_number, pos, translations, entry_body, unaccented_entry)


class dbColumnorderLatinword(dbLatinWord):
	"""

	the order inside the db lines is not the __init__ order of dbLatinWord()

	hipparchiaDB=# select * from latin_dictionary limit 0;
	 entry_name | metrical_entry | id_number | entry_key | pos | translations | entry_body
	------------+----------------+-----------+-----------+-----+--------------+------------


	"""

	def __init__(self, entry_name, metrical_entry, id_number, entry_key, pos, translations, entry_body):
		super().__init__(entry_name, metrical_entry, id_number, pos, translations, entry_body, entry_key)


"""
[probably not] TODO: clickable INS or DDP xrefs in dictionary entries

it looks like we are now in a position where we have the data to make *some* of these papyrus xrefs work

but you will end up with too many dead ends? a test case eventuated in more sorrow than joy

example:

	κύριοϲ

	3  of gods, esp. in the East, Ϲεκνεβτῦνιϲ ὁ κ. θεόϲ PTeb.284.6 (i B.C.);
	Κρόνοϲ κ. CIG4521 (Abila, i A.D.); Ζεὺϲ κ. Supp.Epigr.2.830 (Damascus,
	iii A.D.); κ. Ϲάραπιϲ POxy.110.2 (ii A.D); ἡ κ. Ἄρτεμιϲ IG 4.1124
	(Tibur, ii A.D.); of deified rulers, τοῦ κ. βαϲιλέοϲ θεοῦ OGI86.8
	(Egypt, i B.C.); οἱ κ. θεοὶ μέγιϲτοι, of Ptolemy XIV and Cleopatra,
	Berl.Sitzb.1902.1096: hence, of rulers in general, βαϲιλεὺϲ Ἡρώδηϲ κ.
	OGI415 (Judaea, i B.C.); of Roman Emperors, BGU1200.11 (Augustus),
	POxy.37 i 6 (Claudius), etc.


[success] PTeb.284.6
	select universalid,title from works where title like '%PTeb%284'
		"dp8801w056";"PTebt (Vol 1) - 284"

	select marked_up_line from dp8801 where wkuniversalid='dp8801w056' and level_00_value='6'
		"ὁ κύριοϲ θεὸϲ καταβή-"


[success] BGU1200.11 can be had by:

	select universalid,title from works where title like '%BGU%1200%'
		"dp0004w057"; "BGU (Vol 4) - 1200"

	select marked_up_line from dp0004 where wkuniversalid='dp0004w057' and level_00_value='11'
		"ὑπὲρ τοῦ θε̣[οῦ] καὶ κυρίου Αὐτοκράτοροϲ Κ̣α̣[ίϲαροϲ καθηκούϲαϲ]"


[fail] Supp.Epigr.2.830

	select universalid,title from works where title like '%Supp%Epigr%830%'
		"in001aw1en";"Attica (Suppl. Epigr. Gr. 1-41 [SEG]) - 21:830"
		[not v2, not damascus, not ii AD, ...]


[fail] CIG4521:

	select universalid,title from works where title like '%CIG%45%'
		"ch0201w01v";"Constantinople [Chr.] (CIG IV [part]) - 9445"
		"ch0305w02z";"Greece [Chr.] (Attica [various sources]) - CIG 9345"


[fail] Berl.Sitzb.1902.1096:
	select universalid,title from works where title like '%Berl%Sitzb%'
		[nothing returned]


[fail] POxy.37 i 6:
	select universalid,title from works where title like '%POxy% 37'
		"dp6f01w035";"POxy (Vol 1) - 37"
	you'll get stuck in the end:
		"<hmu_roman_in_a_greek_text>POxy 1,37=CPapGr 1,19</hmu_roman_in_a_greek_text>"


[fail (but mabe LSJ failed?)] POxy.110.2:
	select universalid,title from works where title like '%POxy% 102'
		"dp6f01w003";"POxy (Vol 1) - 102"

	select * from dp6f01 where wkuniversalid='dp6f01w003' and stripped_line like '%κυρ%'
		three hits; none of them about Sarapis...
		"<hmu_metadata_provenance value="Oxy" /><hmu_metadata_date value="AD 306" /><hmu_metadata_documentnumber value="65" />ἐπὶ ὑπάτων τ[ῶν] κ[υ]ρίων ἡ[μ]ῶν Αὐτοκρατόρων"


"""
