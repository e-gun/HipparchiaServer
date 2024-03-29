# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server import hipparchia
from server.dbsupport.citationfunctions import finddblinefromincompletelocus, finddblinefromlocus, locusintocitation, \
	perseusdelabeler
from server.dbsupport.dblinefunctions import dblineintolineobject, returnfirstorlastlinenumber
from server.dbsupport.miscdbfunctions import perseusidmismatch, simplecontextgrabber
from server.formatting.bibliographicformatting import formatpublicationinfo
from server.formatting.browserformatting import insertparserids
from server.hipparchiaobjects.browserobjects import BrowserOutputObject, BrowserPassageObject
from server.hipparchiaobjects.dbtextobjects import dbAuthor, dbOpus
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.listsandsession.sessionfunctions import findactivebrackethighlighting
from server.startup import workdict
from server.textsandindices.textandindiceshelperfunctions import paragraphformatting, setcontinuationvalue


def buildbrowseroutputobject(authorobject: dbAuthor, workobject: dbOpus, locusindexvalue: int, dbcursor) -> BrowserOutputObject:
	"""

	this function does a lot of work via a number of subfunctions

	lots of refactoring required if you change anything...

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
	if session['debugdb']:
		lineprefix = '<smallcode>{id}&nbsp;&nbsp;&nbsp;</smallcode>&nbsp;'

	# [b] format the lines and insert them into the BrowserPassageObject
	# [b1] check to see if this line is part of a larger formatting block: really only servius?

	lines = paragraphformatting(lines)

	# [b2]
	for line in lines:
		if workobject.isnotliterary() and line.index == workobject.starts:
			# line.index == workobject.starts added as a check because
			# otherwise you will re-see date info in the middle of some documents:
			# it gets reasserted with a CD block reinitialization
			metadata = checkfordocumentmetadata(line, workobject)
			if metadata:
				passage.browsedlines.append(metadata)

		if session['debughtml']:
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

		prefix = lineprefix.format(id=line.getlineurl())
		columnb = prefix+columnb

		notes = '; '.join(line.insetannotations())

		if columna and session['simpletextoutput']:
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

	date = re.search(datefinder, workline.markedup)
	region = re.search(regionfinder, workline.markedup)
	city = re.search(cityfinder, workline.markedup)
	pub = re.search(pubfinder, workline.markedup)

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

	metadatahtml = str().join(metadata)

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


def browserfindlinenumberfromcitation(method: str, citationlist: list, workobject: dbOpus, dbcursor) -> tuple:
	"""

	a BrowserInputParsingObject has a pre-cleaned passageaslist that should be used

	you have been given a locus in one of THREE possible formats

		linenumber : already a line number
		locus : a locus that corresponds to a hipparchia level-list
		perseus : a locus embedded in the dictionary data; these are regularly wonky

	try to turn what you have into a line number in a database table

	:param citationlist:
	:param workobject:
	:param dbcursor:
	:return:
	"""

	resultmessage = 'success'

	dispatcher = {
		'linenumber': browserfindlinenumberfromlinenumber,
		'locus': browserfindlinenumberfromlocus,
		'perseus': browserfindlinenumberfromperseus
	}

	thelinenumber, resultmessage = dispatcher[method](citationlist, workobject, resultmessage, dbcursor)

	return thelinenumber, resultmessage


def browserfindlinenumberfromlinenumber(citationlist: list, workobject: dbOpus, resultmessage: str, dbcursor) -> tuple:
	"""

	you got here either by the hit list or a forward/back button in the passage browser

	dbcursor unused, but we want same parameters for all // functions

	all we do here is make sure the original input was valid

	the list should have one item and look like ['1234']

	:param citationlist:
	:param workobject:
	:param dbcursor:
	:return:
	"""

	try:
		thelinenumber = citationlist[0]
	except IndexError:
		thelinenumber = 'X'

	thelinenumber = re.sub(r'\D', str(), thelinenumber)

	if not thelinenumber:
		thelinenumber = workobject.starts

	return thelinenumber, resultmessage


def browserfindlinenumberfromlocus(citationlist: list, workobject: dbOpus, resultmessage: str, dbcursor) -> tuple:
	"""

	you were sent here by the citation builder autofill boxes

	note that
		browse/locus/gr0016w001/3|11|5
	is
		Herodotus, Historiae, Book 3, section 11, line 5

	and
		locus/lt1056w001/3|5|_0
	is
		Vitruvius, De Architectura, book 3, chapter 5, section 1, line 1

	unfortunately you might need to find '300,19' as in 'Democritus, Fragmenta: Fragment 300,19, line 4'
	'-' is used for something like Ar., Nubes 1510-1511
	'_' is used for '_0' (which really means 'first available line at this level')
	( ) and / should be converted to equivalents in the builder: they do us no good here
	see dbswapoutbadcharsfromciations() in HipparchiaBuilder

	see also citationcharacterset() in InputParsingObject()

	:param citationlist:
	:param workobject:
	:param resultmessage:
	:param dbcursor:
	:return:
	"""

	ct = tuple(citationlist)

	if len(ct) == workobject.availablelevels:
		thelinenumber = finddblinefromlocus(workobject, ct, dbcursor)
	else:
		elements = finddblinefromincompletelocus(workobject, citationlist, dbcursor)
		resultmessage = elements['code']
		thelinenumber = elements['line']

	return thelinenumber, resultmessage


def browserfindlinenumberfromperseus(citationlist: list, workobject: dbOpus, resultmessage: str, dbcursor) -> tuple:
	"""

	here comes the fun part: alien format; inconsistent citation style; incorrect data...

	sample url:

		/browse/perseus/gr0016w001/7:130

	is
		Herodotus, Historiae, Book 7, section 130

	:param citationlist:
	:param workobject:
	:param resultmessage:
	:param dbcursor:
	:return:
	"""

	try:
		# dict does not always agree with our ids...
		# do an imperfect test for this by inviting the exception
		# you can still get a valid but wrong work, of course,
		# but if you ask for w001 and only w003 exists, this is supposed to take care of that
		returnfirstorlastlinenumber(workobject.universalid, dbcursor)
	except:
		# dict did not agree with our ids...: euripides, esp
		# what follows is a 'hope for the best' approach
		workid = perseusidmismatch(workobject.universalid, dbcursor)
		workobject = workdict[workid]

	# life=cal. or section=32
	# this has already been nuked?
	needscleaning = [True for c in citationlist if len(c.split('=')) > 1]
	if True in needscleaning:
		citationlist = perseusdelabeler(citationlist, workobject)

	# another problem 'J. ' in sallust <bibl id="perseus/lt0631w001/J. 79:3" default="NO" valid="yes"><author>Sall.</author> J. 79, 3</bibl>
	# 'lt0631w002/79:3' is what you need to send to finddblinefromincompletelocus()
	# note that the work number is wrong, so the next is only a partial fix and valid only if wNNN has been set right

	if ' ' in citationlist[-1]:
		citationlist[-1] = citationlist[-1].split(' ')[-1]

	p = finddblinefromincompletelocus(workobject, citationlist, dbcursor)
	resultmessage = p['code']
	thelinenumber = p['line']

	return thelinenumber, resultmessage

