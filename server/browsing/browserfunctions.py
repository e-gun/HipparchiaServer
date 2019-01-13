# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server import hipparchia
from server.dbsupport.citationfunctions import locusintocitation, finddblinefromlocus, finddblinefromincompletelocus, \
	perseusdelabeler
from server.dbsupport.dblinefunctions import dblineintolineobject, returnfirstlinenumber
from server.dbsupport.miscdbfunctions import simplecontextgrabber, perseusidmismatch
from server.formatting.bibliographicformatting import formatpublicationinfo
from server.formatting.browserformatting import insertparserids
from server.formatting.wordformatting import depunct
from server.hipparchiaobjects.browserobjects import BrowserOutputObject, BrowserPassageObject
from server.hipparchiaobjects.dbtextobjects import dbAuthor, dbOpus, dbWorkLine
from server.listsandsession.sessionfunctions import findactivebrackethighlighting
from server.startup import workdict
from server.textsandindices.textandindiceshelperfunctions import setcontinuationvalue


def buildbrowseroutputobject(authorobject: dbAuthor, workobject: dbOpus, locusindexvalue: int, dbcursor) -> BrowserOutputObject:
	"""
	this function does a lot of work via a number of subfunctions
	lots of refactoring required if you change anything...

	sample output:
		output = {'browseforwards': 'gr0012w001_LN_2662', 'browseback': 'gr0012w001_LN_2652', 'authornumber': 'gr0012', 'workid': 'gr0012w001', 'authorboxcontents': 'Homer - Homerus (Epic.\x80) [gr0012]', 'workboxcontents': 'Ilias (w001)', 'browserhtml': '<p class="currentlyviewing"><span class="author">Homer</span>, <span class="work">Ilias</span><br /><span class="citation">Book 5, line 159</span><br /><span class="pubvolumename">Homeri Ilias. </span><span class="pubpress">Clarendon Press, </span><span class="pubcity">Oxford, </span><span class="pubyear">1931. </span><span class="pubeditor"> (Allen, T.W.)</span></p><table>\n<tr class="spacing">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</tr>\n<tr class="browser">\n\t<td class="browsedline"><observed id="λεῖπ’">λεῖπ’</observed>, <observed id="ἐπεὶ">ἐπεὶ</observed> <observed id="οὐ">οὐ</observed> <observed id="ζώοντε">ζώοντε</observed> <observed id="μάχηϲ">μάχηϲ</observed> <observed id="ἐκνοϲτήϲαντε">ἐκνοϲτήϲαντε</observed> </td>\n\t<td class="browsercite"></td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><observed id="δέξατο">δέξατο</observed>· <observed id="χηρωϲταὶ">χηρωϲταὶ</observed> <observed id="δὲ">δὲ</observed> <observed id="διὰ">διὰ</observed> <observed id="κτῆϲιν">κτῆϲιν</observed> <observed id="δατέοντο">δατέοντο</observed>. </td>\n\t<td class="browsercite"></td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><span class="focusline">&nbsp;&nbsp;&nbsp;&nbsp;<observed id="Ἔνθ’">Ἔνθ’</observed> <observed id="υἷαϲ">υἷαϲ</observed> <observed id="Πριάμοιο">Πριάμοιο</observed> <observed id="δύω">δύω</observed> <observed id="λάβε">λάβε</observed> <observed id="Δαρδανίδαο">Δαρδανίδαο</observed> </span></td>\n\t<td class="browsercite">5.159</td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><observed id="εἰν">εἰν</observed> <observed id="ἑνὶ">ἑνὶ</observed> <observed id="δίφρῳ">δίφρῳ</observed> <observed id="ἐόνταϲ">ἐόνταϲ</observed> <observed id="Ἐχέμμονά">Ἐχέμμονά</observed> <observed id="τε">τε</observed> <observed id="Χρομίον">Χρομίον</observed> <observed id="τε">τε</observed>. </td>\n\t<td class="browsercite">5.160</td>\n</tr>\n\n<tr class="browser">\n\t<td class="browsedline"><observed id="ὡϲ">ὡϲ</observed> <observed id="δὲ">δὲ</observed> <observed id="λέων">λέων</observed> <observed id="ἐν">ἐν</observed> <observed id="βουϲὶ">βουϲὶ</observed> <observed id="θορὼν">θορὼν</observed> <observed id="ἐξ">ἐξ</observed> <observed id="αὐχένα">αὐχένα</observed> <observed id="ἄξῃ">ἄξῃ</observed> </td>\n\t<td class="browsercite"></td>\n</tr>\n\n</table>'}

	:param authorobject:
	:param workobject:
	:param locusindexvalue:
	:param linesofcontext:
	:param numbersevery:
	:param dbcursor:
	:return:
	"""

	thiswork = workobject.universalid
	linesofcontext = int(session['browsercontext'])
	numbersevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	# [a] acquire the lines we need to display
	surroundinglines = simplecontextgrabber(workobject.authorid, locusindexvalue, linesofcontext, dbcursor)
	lines = [dblineintolineobject(l) for l in surroundinglines]
	lines = [l for l in lines if l.wkuinversalid == thiswork]

	focusline = lines[0]
	for line in lines:
		if line.index == locusindexvalue:
			focusline = line

	passage = BrowserPassageObject(authorobject, workobject, locusindexvalue)
	passage.focusline = focusline
	passage.biblio = formatpublicationinfo(workobject.publication_info)
	passage.citation = locusintocitation(workobject, focusline)

	previousline = lines[0]
	brackettypes = findactivebrackethighlighting()
	continuationdict = {'square': False, 'round': False, 'curly': False, 'angled': False}

	lineprefix = str()
	if session['debugdb'] == 'yes':
		lineprefix = '<smallcode>{id}&nbsp;&nbsp;&nbsp;</smallcode>&nbsp;'

	# [b] format the lines and insert them into the BrowserPassageObject
	for line in lines:
		if workobject.isnotliterary() and line.index == workobject.starts:
			# line.index == workobject.starts added as a check because
			# otherwise you will re-see date info in the middle of some documents
			# it gets reasserted with a CD block reinitialization
			metadata = checkfordocumentmetadata(line, workobject)
			if metadata:
				passage.browsedlines.append(metadata)

		if session['debughtml'] == 'yes':
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
			except ValueError:
				# 973b is not your friend
				linenumber = 0
			if line.samelevelas(previousline) is not True:
				columna = line.shortlocus()
			elif linenumber % numbersevery == 0:
				columna = line.locus()
			else:
				# do not insert a line number or special formatting
				columna = str()

		prefix = lineprefix.format(id=line.universalid)
		columnb = prefix+columnb

		notes = '; '.join(line.insetannotations())

		if columna and session['simpletextoutput'] == 'yes':
			columna = '({a})'.format(a=columna)

		linehtml = passage.linetemplate.format(l=columnb, n=notes, c=columna)

		passage.browsedlines.append(linehtml)
		previousline = line

	# [c] build the output
	outputobject = BrowserOutputObject(authorobject, workobject, locusindexvalue)

	outputobject.browserhtml = passage.generatepassagehtml()

	return outputobject


def checkfordocumentmetadata(workline: dbWorkLine, workobject: dbOpus) -> str:
	"""

	if this line contains metadata about the document as a whole, then extract and format it

	useful for papyri and inscriptions

	:param workline:
	:param workobject:
	:return:
	"""

	metadata = list()
	linetemplate = fetchhtmltemplateformetadatarow()

	datefinder = re.compile(r'<hmu_metadata_date value="(.*?)" />')
	regionfinder = re.compile(r'<hmu_metadata_region value="(.*?)" />')
	cityfinder = re.compile(r'<hmu_metadata_city value="(.*?)" />')
	pubfinder = re.compile(r'<hmu_metadata_publicationinfo value="(.*?)" />')

	date = re.search(datefinder, workline.accented)
	region = re.search(regionfinder, workline.accented)
	city = re.search(cityfinder, workline.accented)
	pub = re.search(pubfinder, workline.accented)

	metadatatags = list()
	if region:
		metadatatags.append(('Region', 'regioninfo', region.group(1)))
	if city:
		metadatatags.append(('City', 'cityinfo', city.group(1)))

	if workobject.provenance and city is None:
		metadatatags.append(('Provenance', 'provenance', workobject.provenance))
	if pub:
		metadatatags.append(('Additional publication info', 'pubinfo', pub.group(1)))
	if date:
		metadatatags.append(('Editor\'s date', 'textdate', date.group(1)))

	for m in metadatatags:
		metadata.append(linetemplate.format(lb=m[0], cl=m[1], tx=m[2]))

	# this next is off because the information does not seem useful at all: 'documentnumber: 601', etc.
	# if line.annotations != '':
	# 	html = buildmetadatarow('notation', 'xref', line.annotations)
	# 	metadata.append(html)

	metadata.append('<tr><td>&nbsp;</td></tr>')

	metadatahtml = ''.join(metadata)

	return metadatahtml


def fetchhtmltemplateformetadatarow(shownotes=True):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed

	example:

		label, css, metadata: Region regioninfo Kos
		label, css, metadata: City cityinfo Kos
		label, css, metadata: Additional publication info pubinfo SEG 16.476+
		label, css, metadata: Editor's date textdate 182a

	:param shownotes:
	:return:
	"""

	if shownotes:
		linetemplate = """
		<tr class="browser">
			<td class="blank">&nbsp;</td>
			<td class="documentmeta">
				<span class="documentmetadatalabel">{lb}:</span>&nbsp;
				<span class="{cl}">{tx}</span>
				</td>
			<td class="blank">&nbsp;</td>
		</tr>
		"""
	else:
		linetemplate = """
		<tr class="browser">
			<td class="documentmeta">
				<span class="documentmetadatalabel">{lb}:</span>&nbsp;
				<span class="{cl}">{tx}</span>
				</td>
			<td class="blank">&nbsp;</td>
		</tr>
		"""

	return linetemplate


def findlinenumberfromcitation(method: str, citation: str, workobject: dbOpus, dbcursor) -> tuple:
	"""

	you have been given a locus in one of THREE possible formats

		linenumber : already a line number
		locus : a locus that corresponds to a hipparchia level-list
		perseus : a locus embedded in the dictionary data; these are regularly wonky

	try to turn what you have into a line number in a database table

	:param citation:
	:param workobject:
	:param dbcursor:
	:return:
	"""

	resultmessage = 'success'

	dispatcher = {
		'linenumber': findlinenumberfromlinenumber,
		'locus': findlinenumberfromlocus,
		'perseus': findlinenumberfromperseus
	}

	thelinenumber, resultmessage = dispatcher[method](citation, workobject, resultmessage, dbcursor)

	return thelinenumber, resultmessage


def findlinenumberfromlinenumber(citation: str, workobject: dbOpus, resultmessage: str, dbcursor) -> tuple:
	"""

	you got here either by the hit list or a forward/back button in the passage browser

	dbcursor unused, but we want same parameters for all // functions

	all we do here is make sure the original input was valid

	:param citation:
	:param workobject:
	:param dbcursor:
	:return:
	"""

	thelinenumber = re.sub('[\D]', '', citation)
	if not thelinenumber:
		thelinenumber = workobject.starts

	return thelinenumber, resultmessage


def findlinenumberfromlocus(citation: str, workobject: dbOpus, resultmessage: str, dbcursor) -> tuple:
	"""

	you were sent here by the citation builder autofill boxes

	note that
		browse/locus/gr0016w001/3|11|5
	is
		Herodotus, Historiae, Book 3, section 11, line 5

	unfortunately you might need to find '300,19' as in 'Democritus, Fragmenta: Fragment 300,19, line 4'
	'-' is used for '_0' (which really means 'first available line at this level')
	( ) and / should be converted to equivalents in the builder: they do us no good here
	see dbswapoutbadcharsfromciations() in HipparchiaBuilder

	:param citation:
	:param workobject:
	:param resultmessage:
	:param dbcursor:
	:return:
	"""

	allowedpunct = ',_'

	p = citation.split('|')
	cleanedp = [depunct(level, allowedpunct) for level in p]
	cleanedp.reverse()
	cleanedp = tuple(cleanedp[:5])

	if len(cleanedp) == workobject.availablelevels:
		thelinenumber = finddblinefromlocus(workobject, cleanedp, dbcursor)
	else:
		p = finddblinefromincompletelocus(workobject, list(cleanedp), dbcursor)
		resultmessage = p['code']
		thelinenumber = p['line']

	return thelinenumber, resultmessage


def findlinenumberfromperseus(citation: str, workobject: dbOpus, resultmessage: str, dbcursor) -> tuple:
	"""

	here comes the fun part: alien format; inconsistent citation style; incorrect data...

	sample url:

		/browse/perseus/gr0016w001/7:130

	is
		Herodotus, Historiae, Book 7, section 130

	that is, '7:130' is *NOT REVERSED*

	:param citation:
	:param workobject:
	:param resultmessage:
	:param dbcursor:
	:return:
	"""

	allowedpunct = ',-'

	try:
		# dict does not always agree with our ids...
		# do an imperfect test for this by inviting the exception
		# you can still get a valid but wrong work, of course,
		# but if you ask for w001 and only w003 exists, this is supposed to take care of that
		returnfirstlinenumber(workobject.universalid, dbcursor)
	except:
		# dict did not agree with our ids...: euripides, esp
		# what follows is a 'hope for the best' approach
		workid = perseusidmismatch(workobject.universalid, dbcursor)
		workobject = workdict[workid]

	citationlist = citation.split(':')
	citationlist.reverse()

	# life=cal. or section=32
	needscleaning = [True for c in citationlist if len(c.split('=')) > 1]
	if True in needscleaning:
		citationlist = perseusdelabeler(citationlist, workobject)

	# another problem 'J. ' in sallust <bibl id="lt0631w001_PE_J. 79:3" default="NO" valid="yes"><author>Sall.</author> J. 79, 3</bibl>
	# lt0631w002_PE_79:3 is what you need to send to finddblinefromincompletelocus()
	# note that the work number is wrong, so the next is only a partial fix and valid only if wNNN has been set right

	if ' ' in citationlist[-1]:
		citationlist[-1] = citationlist[-1].split(' ')[-1]

	# meaningful only in the context of someone purposefully submitting bad data...
	citationlist = [depunct(level, allowedpunct) for level in citationlist]

	p = finddblinefromincompletelocus(workobject, citationlist, dbcursor)
	resultmessage = p['code']
	thelinenumber = p['line']

	return thelinenumber, resultmessage

