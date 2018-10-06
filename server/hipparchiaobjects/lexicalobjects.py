# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
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
		self.body = self._spacebetween(self._xmltohtmlquickconversions(entry_body))

		self.soup = None
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

		if re.search(r'[a-z]', self.entry):
			self.usedictionary = 'latin'
			self.translationlabel = 'hi'
		else:
			self.usedictionary = 'greek'
			self.translationlabel = 'tr'

	def runbodyxrefsuite(self):
		# add dictionary clicks to "cf.", etc. in the entry body
		raise NotImplementedError

	def isagloss(self):
		fingerprint = re.compile(r'<author>Gloss\.</author>')
		if re.search(fingerprint, self.body):
			return True
		else:
			return False

	def makesoup(self):
		if not self.xrefspresent:
			self.runbodyxrefsuite()
		self.soup = BeautifulSoup(self.body, 'html.parser')

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

		if session['authorssummary'] == 'yes':
			aa = len(authorlist)
			if aa != 1:
				authorlist = ['{n} authors'.format(n=aa)]
			else:
				authorlist = ['1 author']

		return authorlist

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

		if session['sensesummary'] == 'yes':
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

		if session['quotesummary'] == 'yes':
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
		heading = re.compile(r'(.*?)<sense')
		head = re.search(heading, self.body)

		try:
			return head.group(1)
		except AttributeError:
			return str()

	def grabnonheadmaterial(self) -> str:
		"""
		find the information at the top of a dictionary entry: used to get the basic info about the word
		:param fullentry:
		:return:
		"""
		heading = re.compile(r'(.*?)<sense')
		head = re.search(heading, self.body)

		try:
			return self.body[head.end(1):]
		except AttributeError:
			return str()

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
			<span class="levellabel{lv}">
				{nm}
			</span>{sn}
		</p>"""

		lvl = re.search(levelfinder, foundsense)
		num = re.search(numfinder, foundsense)
		# note that the two dictionaries do not necc agree with one another (or themselves) when it comes to nesting labels
		if re.search(r'[A-Z]', num.group(1)):
			paragraphlevel = '1'
		elif re.search(r'\d', num.group(1)):
			paragraphlevel = '3'
		elif re.search(r'[ivx]', num.group(1)):
			paragraphlevel = '4'
		elif re.search(r'[a-hj-w]', num.group(1)):
			paragraphlevel = '2'
		else:
			paragraphlevel = '1'

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
			they make a crazy number of calls

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

		pruned = re.sub(tagfinder, lambda x: self.droptagsfromxml(x.group(1), dropset), self.body)

		preservetags = {'bibl', 'span', 'p', 'dictionaryentry', 'biblscope', 'sense', 'unclickablebibl'}
		pruned = re.sub(tagfinder, lambda x: self.converttagstoclasses(x.group(1), preservetags), pruned)

		closefinder = re.compile(r'</(.*?)>')
		self.body = re.sub(closefinder, lambda x: self.xmlclosetospanclose(x.group(1), preservetags), pruned)

		self.xmlhasbeenconverted = True
		return

	@staticmethod
	def xmlclosetospanclose(xmlstring: str, leaveuntouched: set) -> str:
		if xmlstring in leaveuntouched:
			newxmlstring = '</{x}>'.format(x=xmlstring)
		else:
			newxmlstring = '</span>'
		return newxmlstring

	@staticmethod
	def droptagsfromxml(xmlstring: str, dropset: set) -> str:
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

		finder = re.compile(r'(\w+)=".*?"')
		components = xmlstring.split(' ')
		combined = [components[0]]
		preserved = [c for c in components[1:] if re.search(finder, c) and re.search(finder, c).group(1) not in dropset]
		combined.extend(preserved)
		newxml = '<{x}>'.format(x=' '.join(combined))
		return newxml

	@staticmethod
	def converttagstoclasses(xmlstring: str, leaveuntouched: set) -> str:
		"""
		in:
			<orth extent="full" lang="greek" opt="n">

		out:
			<span class="orth extent_full lang_greek opt_n">

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
			combined = [components[0]]
			collapsedtags = [re.sub(finder, r'\1_\2', t) for t in components[1:]]
			combined.extend(collapsedtags)
		newxml = '<span class="{x}">'.format(x=' '.join(combined))
		return newxml

	def printclasses(self):
		"""

		a debugging function to find out what CSS styles are needed:

		πρόϲ:
		{'dicthi rend_ital', 'levellabel3', 'dictref lang_greek targorder_U', 'level1', 'level_1', 'dictquote
		lang_greek', 'dictgram type_comp', 'dictdate', 'dictabbr', 'dictplacename', 'dicttr', 'dictpb',
		'dictitype lang_greek', 'level_2', 'dictlbl', 'levellabel1', 'dictunclickablebibl', 'dictbibtitle',
		'dictgramgrp', 'level2', 'dictcit', 'level_4', 'dictxr', 'dictorth lang_greek', 'level3', 'dictauthor',
		'dictetym lang_greek', 'dictpos', 'dictgram type_dialect', 'level_3', 'levellabel2', 'levellabel4',
		'dictforeign lang_greek'}

		bonus:
		{'dictitype', 'dicthi rend_ital', 'levellabel3', 'level1', 'dictnumber', 'level_1', 'level_5',
		'levellabel5', 'dictusg type_style', 'dictgen', 'dictorth lang_la', 'dictetym', 'dicttrans', 'dicttr',
		'dictquote lang_la', 'dictpb', 'level_2', 'levellabel1', 'dictunclickablebibl', 'level2', 'dictcb',
		'dictcit', 'level_4', 'level3', 'dictauthor', 'dictpos', 'level_3', 'levellabel2', 'levellabel4'}

		:return:
		"""
		tags = self.soup.find_all(True)
		allclasses = list()
		for t in tags:
			try:
				allclasses.append(t['class'])
			except KeyError:
				pass
		print(set(allclasses))
		return

	@staticmethod
	def entrywordcleaner(foundword, substitutionstring):
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

	@staticmethod
	def isgreek():
		raise NotImplementedError

	@staticmethod
	def islatin():
		raise NotImplementedError

	def bsgrabheadmaterial(self) -> str:
		soupitems = self.soup.find_all()
		done = False
		head = list()

		while soupitems and not done:
			item = soupitems.pop()
			if item.name == 'sense':
				done = True
			else:
				head.append(item)

		headmaterial = '\n'.join([repr(h) for h in head])
		return headmaterial

	def insertclickablelookups(self):
		"""

		in:
			<bibl n="Perseus:abo:tlg,0019,003:1214" default="NO" valid="yes">

		out:
			<bibl id="gr0019w003_PE_1214" default="NO" valid="yes">

		:return:
		"""

		# first retag the items that should not click-to-browse

		biblios = re.compile(r'(<bibl.*?)(.*?)(</bibl>)')
		bibs = re.findall(biblios, self.body)
		bdict = dict()

		for bib in bibs:
			if 'Perseus:abo' not in bib[1]:
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

		tlgfinder = re.compile(r'n="Perseus:abo:tlg,(\d\d\d\d),(\d\d\d):(.*?)"')
		phifinder = re.compile(r'n="Perseus:abo:phi,(\d\d\d\d),(\d\d\d):(.*?)"')

		clickableentry = re.sub(tlgfinder, r'id="gr\1w\2_PE_\3"', htmlentry)
		clickableentry = re.sub(phifinder, r'id="lt\1w\2_PE_\3"', clickableentry)
		self.body = clickableentry
		self.haveclickablelookups = True
		return


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
			self._greekxmltagwrapper('ref')
			self._greekxmltagwrapper('etym')
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
			self._latinetymologyfinder()
			self._latinsubvidefinder()
			self._latinsynonymfinder()
			self.xrefspresent = True

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
		xreffinder.append(re.compile(r'(v\. )(\w+)(, I+)'))
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

	def _latinetymologyfinder(self):
		"""

		make "balneum" clickable if you are told a word comes from it.

		sample from entry:

			<etym opt="n">balneum</etym>

			<gen opt="n">m.</gen>, = βούβαλοϲ,

			i. q. εἴδωγον)   [nb: this example has a typo in the original data: εἴδωλον is meant]

		note problem with:

			<etym opt="n">Spanish</etym>

		:return:
		"""

		xreffinder = list()
		xreffinder.append(re.compile(r'(<etym opt=".">)(\w+)(</etym>)'))
		xreffinder.append(re.compile(r'(<etym opt=".">\d\. )(\w+)(</etym>)'))
		xreffinder.append(re.compile(r'(<etym opt=".">)(\w+)([;,])'))
		xreffinder.append(re.compile(r'(= )(\w+)([, ])'))
		xreffinder.append(re.compile(r'(cf\. Gr\. )(\w+)(,)'))
		xreffinder.append(re.compile(r'( i\. q\. )(\w+)(\))'))

		sv = r'\1<dictionaryentry id="\2">\2</dictionaryentry>\3'
		for x in xreffinder:
			self.body = re.sub(x, sv, self.body)
