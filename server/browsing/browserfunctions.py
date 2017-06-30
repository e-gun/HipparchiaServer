# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import re
from collections import deque

from server import hipparchia
from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject
from server.formatting.bibliographicformatting import getpublicationinfo, avoidlonglines
from server.listsandsession.sessionfunctions import findactivebrackethighlighting
from server.textsandindices.textandindiceshelperfunctions import setcontinuationvalue

config = configparser.ConfigParser()
config.read('config.ini')


def getandformatbrowsercontext(authorobject, workobject, locusindexvalue, linesofcontext, numbersevery, cursor):
	"""
	this function does a lot of work via a number of subfunctions
	lots of refactoring required if you change anything...

	sample output:
		passage = {'browseforwards': 'gr0012w001_LN_2662', 'browseback': 'gr0012w001_LN_2652', 'authornumber': 'gr0012', 'workid': 'gr0012w001', 'authorboxcontents': 'Homer - Homerus (Epic.\x80) [gr0012]', 'workboxcontents': 'Ilias (w001)', 'browserhtml': '<p class="currentlyviewing"><span class="author">Homer</span>, <span class="work">Ilias</span><br /><span class="citation">Book 5, line 159</span><br /><span class="pubvolumename">Homeri Ilias. </span><span class="pubpress">Clarendon Press, </span><span class="pubcity">Oxford, </span><span class="pubyear">1931. </span><span class="pubeditor"> (Allen, T.W.)</span></p><table>\n<tr class="spacing">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</tr>\n<tr class="browser">\n\t<td class="browsedline"><observed id="λεῖπ’">λεῖπ’</observed>, <observed id="ἐπεὶ">ἐπεὶ</observed> <observed id="οὐ">οὐ</observed> <observed id="ζώοντε">ζώοντε</observed> <observed id="μάχηϲ">μάχηϲ</observed> <observed id="ἐκνοϲτήϲαντε">ἐκνοϲτήϲαντε</observed> </td>\n\t<td class="browsercite"></td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><observed id="δέξατο">δέξατο</observed>· <observed id="χηρωϲταὶ">χηρωϲταὶ</observed> <observed id="δὲ">δὲ</observed> <observed id="διὰ">διὰ</observed> <observed id="κτῆϲιν">κτῆϲιν</observed> <observed id="δατέοντο">δατέοντο</observed>. </td>\n\t<td class="browsercite"></td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><span class="focusline">&nbsp;&nbsp;&nbsp;&nbsp;<observed id="Ἔνθ’">Ἔνθ’</observed> <observed id="υἷαϲ">υἷαϲ</observed> <observed id="Πριάμοιο">Πριάμοιο</observed> <observed id="δύω">δύω</observed> <observed id="λάβε">λάβε</observed> <observed id="Δαρδανίδαο">Δαρδανίδαο</observed> </span></td>\n\t<td class="browsercite">5.159</td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><observed id="εἰν">εἰν</observed> <observed id="ἑνὶ">ἑνὶ</observed> <observed id="δίφρῳ">δίφρῳ</observed> <observed id="ἐόνταϲ">ἐόνταϲ</observed> <observed id="Ἐχέμμονά">Ἐχέμμονά</observed> <observed id="τε">τε</observed> <observed id="Χρομίον">Χρομίον</observed> <observed id="τε">τε</observed>. </td>\n\t<td class="browsercite">5.160</td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><observed id="ὡϲ">ὡϲ</observed> <observed id="δὲ">δὲ</observed> <observed id="λέων">λέων</observed> <observed id="ἐν">ἐν</observed> <observed id="βουϲὶ">βουϲὶ</observed> <observed id="θορὼν">θορὼν</observed> <observed id="ἐξ">ἐξ</observed> <observed id="αὐχένα">αὐχένα</observed> <observed id="ἄξῃ">ἄξῃ</observed> </td>\n\t<td class="browsercite"></td>\n</tr>\n\n</table>'}

	:param authorobject:
	:param workobject:
	:param locusindexvalue:
	:param linesofcontext:
	:param numbersevery:
	:param cursor:
	:return:
	"""

	thiswork = workobject.universalid

	if workobject.isliterary():
		name = authorobject.shortname
	else:
		name = authorobject.idxname

	title = workobject.title

	try:
		if int(workobject.converted_date) < 1500:
			date = str(workobject.converted_date)
		else:
			date = ''
	except:
		date = ''

	if locusindexvalue - linesofcontext < workobject.starts:
		# note that partial db builds can leave works that do not have this value
		# None will return and you will not get a browser window for this author
		starts = workobject.starts
	else:
		starts = locusindexvalue - linesofcontext

	if locusindexvalue + linesofcontext > workobject.ends:
		ends = workobject.ends
	else:
		ends = locusindexvalue + linesofcontext

	passage = {}
	# [A] populating various corners of the UI
	# urls to send to the browse forwards and back buttons
	passage['browseforwards'] = thiswork + '_LN_' + str(ends)
	passage['browseback'] = thiswork + '_LN_' + str(starts)

	# will be used to fill the autocomplete boxes
	passage['authornumber'] = authorobject.universalid
	passage['workid'] = workobject.universalid

	# as per offerauthorhints() in views.py
	passage['authorboxcontents'] = '{n} [{id}]'.format(n=authorobject.cleanname, id=authorobject.universalid)
	# offerworkhints()
	passage['workboxcontents'] = '{t} ({id})'.format(t=workobject.title, id=workobject.universalid[-4:])

	# [B] now get into the actual text to display in the main browser element
	surroundinglines = simplecontextgrabber(workobject.authorid, locusindexvalue, linesofcontext, cursor)

	lines = [dblineintolineobject(l) for l in surroundinglines]
	lines = [l for l in lines if l.wkuinversalid == thiswork]

	focusline = lines[0]
	for line in lines:
		if line.index == locusindexvalue:
			focusline = line

	biblio = getpublicationinfo(workobject, cursor)

	citation = locusintocitation(workobject, focusline)
	authorandwork = '<span class="author">{n}</span>, <span class="work">{t}</span><br />'.format(n=name, t=title)
	# author + title can get pretty long
	viewing = [avoidlonglines(authorandwork, 100, '<br />\n', [])]
	viewing.append('<span class="citation">{c}</span>'.format(c=citation))
	if date != '':
		if int(date) > 1:
			viewing.append('<br /><span class="assigneddate">(Assigned date of {d} CE)</span>'.format(d=date))
		else:
			viewing.append('<br /><span class="assigneddate">(Assigned date of {d} BCE)</span>'.format(d=date[1:]))

	viewing = '\n'.join(viewing)
	viewing = '<p class="currentlyviewing">{c}\n<br />\n{b}\n</p>'.format(c=viewing, b=biblio)

	ouputtable = []
	ouputtable.append('<table>')

	# guarantee a minimum width to the browser dialogue box; or else skip adding this blank row
	try:
		spacer = ''.join(['&nbsp;' for i in range(0, hipparchia.config['MINIMUMBROWSERWIDTH'])])
		ouputtable.append('<tr class="spacing">{sp}</tr>'.format(sp=spacer))
	except:
		pass

	previousline = lines[0]
	brackettypes = findactivebrackethighlighting()
	continuationdict = { 'square': False, 'round': False, 'curly': False, 'angled': False }

	shownotes = True
	if shownotes:
		linetemplate = """
		<tr class="browser">
			<td class="browserembeddedannotations">{n}</td>
			<td class="browsedline">{l}</td>
			<td class="browsercite">{c}</td>
		</tr>
		"""
	else:
		linetemplate = """
		<tr class="browser">
			<td class="browsedline">{l}</td>
			<td class="browsercite">{c}</td>
		</tr>
		"""

	for line in lines:
		if workobject.isnotliterary() and line.index == workobject.starts:
			# line.index == workobject.starts added as a check because
			# otherwise you will re-see date info in the middle of some documents
			# it gets reasserted with a CD block reinitialization
			metadata = checkfordocumentmetadata(line, workobject)
			if metadata:
				ouputtable.append(metadata)

		if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
			columnb = line.showlinehtml()
		else:
			columnb = insertparserids(line, continuationdict)

		if brackettypes:
			continuationdict = {t: setcontinuationvalue(line, previousline, continuationdict[t], t)
			                         for t in brackettypes}

		if line.index == focusline.index:
			# highlight the citationtuple line
			columna = line.locus()
			columnb = '<span class="focusline">{c}</span>'.format(c=columnb)
		else:
			try:
				linenumber = int(line.l0)
			except:
				# 973b is not your friend
				linenumber = 0
			if line.samelevelas(previousline) is not True:
				columna = line.shortlocus()
			elif linenumber % numbersevery == 0:
				columna = line.locus()
			else:
				# do not insert a line number or special formatting
				columna = ''

		prefix = ''
		if hipparchia.config['DBDEBUGMODE'] == 'yes':
			prefix = '<smallcode>{id}&nbsp;&nbsp;&nbsp;</smallcode>&nbsp;'.format(id=line.universalid)
		columnb = prefix+columnb

		notes = '; '.join(line.insetannotations())

		linehtml = linetemplate.format(l=columnb, n=notes, c=columna)

		ouputtable.append(linehtml)
		previousline = line

	if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
		ouputtable.append('</table>\n<span class="emph">(NB: click-to-parse is off if HTMLDEBUGMODE is set)</span>')
	else:
		ouputtable.append('</table>')

	passage['browserhtml'] = viewing + '\n'.join(ouputtable)

	return passage


def checkfordocumentmetadata(line, workobject):
	"""

	if this line metadata about the document as a whole, then extract and format it

	:param line:
	:param workobject:
	:return:
	"""

	metadata = []

	datefinder = re.compile(r'<hmu_metadata_date value="(.*?)" />')
	regionfinder = re.compile(r'<hmu_metadata_region value="(.*?)" />')
	cityfinder = re.compile(r'<hmu_metadata_city value="(.*?)" />')
	pubfinder = re.compile(r'<hmu_metadata_publicationinfo value="(.*?)" />')

	date = re.search(datefinder, line.accented)
	region = re.search(regionfinder, line.accented)
	city = re.search(cityfinder, line.accented)
	pub = re.search(pubfinder, line.accented)

	if region:
		html = buildmetadatarow('Region', 'regioninfo', region.group(1))
		metadata.append(html)
	if city:
		html = buildmetadatarow('City', 'cityinfo', city.group(1))
		metadata.append(html)
	if workobject.provenance and city is None:
		html = buildmetadatarow('Provenance', 'provenance', workobject.provenance)
		metadata.append(html)
	if pub:
		html = buildmetadatarow('Additional publication info', 'pubinfo', pub.group(1))
		metadata.append(html)
	if date:
		html = buildmetadatarow('Editor\'s date', 'textdate', date.group(1))
		metadata.append(html)

	# this next is off because the information does not seem useful at all: 'documentnumber: 601', etc.
	# if line.annotations != '':
	# 	html = buildmetadatarow('notation', 'xref', line.annotations)
	# 	metadata.append(html)

	metadata.append('<tr><td>&nbsp;</td></tr>')

	metadatahtml = ''.join(metadata)

	return metadatahtml


def insertparserids(lineobject, continuationdict):
	"""
	set up the clickable thing for the browser by bracketing every word with something the JS can respond to:
		<observed id="ἐπειδὲ">ἐπειδὲ</observed>
		<observed id="δέ">δέ</observed>
		...
	this is tricky because there is html in here and you don't want to tag it
	also you need to handle hypenated line-ends

	there is a lot of dancing around required to both mark up the brackets and to make
	the clickable observeds

	a lot of hoops to jump trhough for a humble problem: wrong whitespace position

	the main goal is to avoid 'ab[ <span>cd' when what you want is 'ab[<span>cd'
	the defect is that anything that is chopped up by bracketing markup will be
	'unobservable' and so unclickable: 'newline[-1] +=' removes you from consideration
	but if you turn off the highlighting the clicks come back

	this rewriting of the rewritten and marking up of the marked up explains the ugliness below: kludgy, but...

	Aeschylus, Fragmenta is a great place to give the parser a workout

	anything that works with Aeschylus should then be checked against a fragmentary INS and a fragmentary DDP

	in the course of debugging it is possible to produce versions that work with only some of those three types of passage

	:param lineobject:
	:return:
	"""

	theline = lineobject.accented
	newline = ['']

	brackettypes = findactivebrackethighlighting()
	if brackettypes:
		continuationdict = {e: continuationdict[e] for e in brackettypes}
		theline = lineobject.markeditorialinsersions(continuationdict)

	theline = re.sub(r'(\<.*?\>)',r'*snip*\1*snip*',theline)
	hyphenated = lineobject.hyphenated
	segments = deque([s for s in theline.split('*snip*') if s])
	
	# OK, you have your segments, but the following will have a spacing problem ('</observed><span...>' vs '</observed> <span...>':
	#	['ὁ μὲν ', '<span class="expanded">', 'Μυρμιδόϲιν·', '</span>']
	# you can fix the formatting issue by adding an item that is just a blank space: ' '
	#	['ὁ μὲν ', ' ', '<span class="expanded">', 'Μυρμιδόϲιν·', '</span>']
	# another place where you need space:
	#	['</span>', ' Κωπάιδων']
	properlyspacedsegments = []
	while len(segments) > 1:
		if len(segments[0]) > 1 and re.search(r'\s$', segments[0]) and re.search(r'^<', segments[1]):
			# ['ὁ μὲν ', '<span class="expanded">', 'Μυρμιδόϲιν·', '</span>']
			properlyspacedsegments.append(segments.popleft())
			properlyspacedsegments.append(' ')
		elif re.search(r'>$', segments[0]) and re.search(r'^\s', segments[1]):
			# ['</span>', ' Κωπάιδων']
			properlyspacedsegments.append(segments.popleft())
			properlyspacedsegments.append(' ')
		else:
			properlyspacedsegments.append(segments.popleft())
	properlyspacedsegments.append(segments.popleft())

	for segment in properlyspacedsegments:
		# here come the spacing and joining games
		if segment[0] == '<':
			# this is markup don't 'observe' it
			newline[-1] += segment
		else:
			words = segment.split(' ')
			words = ['{wd} '.format(wd=w) for w in words if len(w) > 0]
			words = deque(words)

			# first and last words matter because only they can crash into markup
			# and, accordingly, only they can produce the clash between markup and brackets

			try:
				lastword = words.pop()
			except IndexError:
				lastword = None

			try:
				lastword = re.sub(r'\s$', r'', lastword)
			except TypeError:
				pass

			try:
				firstword = words.popleft()
			except IndexError:
				firstword = None

			if not firstword:
				firstword = lastword
				lastword = None

			if not firstword:
				newline[-1] += ' '

			if firstword:
				if bracketcheck(firstword):
					newline[-1] += '{w}'.format(w=firstword)
				else:
					newline.append(addobservedtags(firstword, lastword, hyphenated))

			while words:
				word = words.popleft()
				newline.append(addobservedtags(word, lastword, hyphenated))

			if lastword:
				if bracketcheck(lastword):
					newline[-1] += '{w}'.format(w=lastword)
				else:
					newline.append(addobservedtags(lastword, lastword, hyphenated))

	newline = ''.join(newline)

	return newline


def bracketcheck(word):
	"""

	true if there are brackets in the word

	:param word:
	:return:
	"""

	brackets = re.compile(r'[\[\(\{⟨\]\)\}⟩]')

	if re.search(brackets, word):
		return True
	else:
		return False


def addobservedtags(word, lastword, hyphenated):
	"""

	take a word and sandwich it with a tag

		'<observed id="imperator">imperator</observed>'

	:param word:
	:return:
	"""

	nsp = re.compile(r'&nbsp;$')
	untaggedclosings = re.compile(r'[\])⟩},;.?!:·’′“”»†]$')
	neveropens = re.compile(r'^[‵„“«†]')

	if re.search(r'\s$',word):
		word = re.sub(r'\s$',r'', word)
		sp = ' '
	else:
		sp = ''

	try:
		word[-1]
	except:
		return ''

	if word[-1] == '-' and word == lastword:
		o = '<observed id="{h}">{w}</observed>{sp}'.format(h=hyphenated, w=word, sp=sp)
	elif re.search(neveropens, word) and not re.search(untaggedclosings, word):
		o = '{wa}<observed id="{wb}">{wb}</observed>{sp}'.format(wa=word[0], wb=word[1:], sp=sp)
	elif re.search(neveropens, word) and re.search(untaggedclosings, word) and not re.search(nsp, word):
		wa = word[0]
		wb = word[1:-1]
		wc = word[-1]
		o = '{wa}<observed id="{wb}">{wb}</observed>{wc}{sp}'.format(wa=wa, wb=wb, wc=wc, sp=sp)
	elif not re.search(neveropens, word) and re.search(untaggedclosings, word) and not re.search(nsp, word):
		wa = word[0:-1]
		wb = word[-1]
		o = '<observed id="{wa}">{wa}</observed>{wb}{sp}'.format(wa=wa, wb=wb, sp=sp)
	elif re.search(neveropens, word):
		o = '{wa}<observed id="{wb}">{wb}</observed>{sp}'.format(wa=word[0], wb=word[1:], sp=sp)
	else:
		o = '<observed id="{w}">{w}</observed>{sp}'.format(w=word, sp=sp)

	return o


def buildmetadatarow(label, css, metadata):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed

	example:

		label, css, metadata: Region regioninfo Kos
		label, css, metadata: City cityinfo Kos
		label, css, metadata: Additional publication info pubinfo SEG 16.476+
		label, css, metadata: Editor's date textdate 182a

	:param lineobject:
	:return:
	"""

	shownotes = True
	if shownotes:
		linetemplate = """
		<tr class="browser">
			<td class="blank">&nbsp;</td>
			<td class="documentmeta">
				<span class="documentmetadatalabel">{l}:</span>&nbsp;
				<span class="{css}">{md}</span>
				</td>
			<td class="blank">&nbsp;</td>
		</tr>
		"""
	else:
		linetemplate = """
		<tr class="browser">
			<td class="documentmeta">
				<span class="documentmetadatalabel">{l}:</span>&nbsp;
				<span class="{css}">{md}</span>
				</td>
			<td class="blank">&nbsp;</td>
		</tr>
		"""

	linehtml = linetemplate.format(l=label, css=css, md=metadata)

	return linehtml