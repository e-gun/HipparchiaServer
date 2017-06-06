# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser
import re

from server import hipparchia
from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject
from server.formatting.bibliographicformatting import getpublicationinfo, avoidlonglines

config = configparser.ConfigParser()
config.read('config.ini')


def getandformatbrowsercontext(authorobject, workobject, locusindexvalue, linesofcontext, numbersevery, cursor):
	"""
	this function does a lot of work via a number of subfunctions
	lots of refactoring required if you change anything...

	sample output:
		{'workid': 'gr7000w001', 'browseback': 'gr7000w001_LN_1089', 'authorboxcontents': 'AG - Anthologia Graeca [gr7000]', 'workboxcontents': 'Anthologia Graeca (w001)', 'ouputtable': ['<table>\n', '<tr class="browser"><td class="browsedline"><observed id="Ἀλκιμέδη">Ἀλκιμέδη</observed> <observed id="ξύνευνον">ξύνευνον</observed> <observed id="Ἀμύντορα">Ἀμύντορα</observed> <observed id="παιδὸϲ">παιδὸϲ</observed> <observed id="ἐρύκει">ἐρύκει</observed>, </td><td class="browsercite"></td></tr>\n', '<tr class="browser"><td class="browsedline">&nbsp;&nbsp;&nbsp;&nbsp;<observed id="Φοίνικοϲ">Φοίνικοϲ</observed> <observed id="δ’">δ’</observed> <observed id="ἐθέλει">ἐθέλει</observed> <observed id="παῦϲαι">παῦϲαι</observed> <observed id="χόλον">χόλον</observed> <observed id="γενέτου">γενέτου</observed>, </td><td class="browsercite"></td></tr>\n', '<tr class="browser"><td class="browsedline"><span class="focusline"><observed id="ὅττι">ὅττι</observed> <observed id="περ">περ</observed> <observed id="ἤχθετο">ἤχθετο</observed> <observed id="πατρὶ">πατρὶ</observed> <observed id="ϲαόφρονοϲ">ϲαόφρονοϲ</observed> <observed id="εἵνεκα">εἵνεκα</observed> <observed id="ματρόϲ">ματρόϲ</observed>, </span></td><td class="browsercite">3.3.3</td></tr>\n', '<tr class="browser"><td class="browsedline">&nbsp;&nbsp;&nbsp;&nbsp;<observed id="παλλακίδοϲ">παλλακίδοϲ</observed> <observed id="δούληϲ">δούληϲ</observed> <observed id="λέκτρα">λέκτρα</observed> <observed id="προϲιεμένῳ">προϲιεμένῳ</observed>· </td><td class="browsercite"></td></tr>\n', '<tr class="browser"><td class="browsedline"><observed id="κεῖνοϲ">κεῖνοϲ</observed> <observed id="δ’">δ’</observed> <observed id="αὖ">αὖ</observed> <observed id="δολίοιϲ">δολίοιϲ</observed> <observed id="ψιθυρίϲμαϲιν">ψιθυρίϲμαϲιν</observed> <observed id="ἤχθετο">ἤχθετο</observed> <observed id="κούρῳ">κούρῳ</observed>, </td><td class="browsercite"></td></tr>\n', '</table>\n'], 'authornumber': 'gr7000', 'currentlyviewing': '<currentlyviewing><span class="author">AG</span>, <span class="work">Anthologia Graeca</span><br />Book 3, epigram 3, line 3<br /><span class="pubvolumename">Anthologia Graeca, <br /></span><span class="pubpress">Heimeran , </span><span class="pubcity">Munich , </span><span class="pubyear">1–2:1965;. </span><span class="pubeditor"> (Beckby, H. )</span></currentlyviewing>', 'browseforwards': 'gr7000w001_LN_1099'}

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
	surroundinglines = simplecontextgrabber(workobject, locusindexvalue, linesofcontext, cursor)

	lines = [dblineintolineobject(l) for l in surroundinglines]
	lines = [l for l in lines if l.wkuinversalid == thiswork]

	focusline = lines[0]
	for line in lines:
		if line.index == locusindexvalue:
			focusline = line

	biblio = getpublicationinfo(workobject, cursor)

	citation = locusintocitation(workobject, focusline.locustuple())
	authorandwork = '<span class="author">{n}</span>, <span class="work">{t}</span><br />'.format(n=name, t=title)
	# author + title can get pretty long
	viewing = avoidlonglines(authorandwork, 100, '<br />', [])
	viewing += '<span class="citation">{c}</span>'.format(c=citation)
	if date != '':
		if int(date) > 1:
			viewing += '<br /><span class="assigneddate">(Assigned date of {d} CE)</span>'.format(d=date)
		else:
			viewing += '<br /><span class="assigneddate">(Assigned date of {d} BCE)</span>'.format(d=date[1:])

	passage['currentlyviewing'] = '<p class="currentlyviewing">{c}<br />{b}</p>'.format(c=viewing, b=biblio)

	ouputtable = []
	ouputtable.append('<table>')

	# guarantee a minimum width to the browser dialogue box; or else skip adding this blank row
	try:
		spacer = ''.join(['&nbsp;' for i in range(0, hipparchia.config['MINIMUMBROWSERWIDTH'])])
		ouputtable.append('<tr class="spacing">{sp}</tr>'.format(sp=spacer))
	except:
		pass


	previousline = lines[0]

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
			columnb = insertparserids(line)

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

		linehtml = '<tr class="browser">\n\t<td class="browsedline">{cb}</td>'.format(cb=columnb)
		linehtml += '\n\t<td class="browsercite">{ca}</td>\n</tr>\n'.format(ca=columna)

		ouputtable.append(linehtml)
		previousline = line

	if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
		ouputtable.append('</table>\n<span class="emph">(NB: click-to-parse is off if HTMLDEBUGMODE is set)</span>')
	else:
		ouputtable.append('</table>')

	passage['ouputtable'] = '\n'.join(ouputtable)

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

	if line.annotations != '':
		xref = insertcrossreferencerow(line)
		metadata.append(xref)
	date = re.search(datefinder, line.accented)
	region = re.search(regionfinder, line.accented)
	city = re.search(cityfinder, line.accented)
	pub = re.search(pubfinder, line.accented)

	if region:
		html = insertdatarow('Region', 'regioninfo', region.group(1))
		metadata.append(html)
	if city:
		html = insertdatarow('City', 'cityinfo', city.group(1))
		metadata.append(html)
	if workobject.provenance and city is None:
		html = insertdatarow('Provenance', 'provenance', workobject.provenance)
		metadata.append(html)
	if pub:
		html = insertdatarow('Additional publication info', 'pubinfo', pub.group(1))
		metadata.append(html)
	if date:
		html = insertdatarow('Editor\'s date', 'textdate', date.group(1))
		metadata.append(html)

	metadatahtml = ''.join(metadata)

	return metadatahtml


def insertparserids(lineobject):
	"""

	set up the clickable thing for the browser by bracketing every word with something the JS can respond to:

		<observed id="ἐπειδὲ">ἐπειδὲ</observed>
		<observed id="δέ">δέ</observed>
		...

	this is tricky because there is html in here and you don't want to tag it

	also you nned to handle hypenated line-ends

	:param lineobject:
	:return:
	"""

	theline = re.sub(r'(\<.*?\>)',r'*snip*\1*snip*',lineobject.accented)
	hyphenated = lineobject.hyphenated
	segments = theline.split('*snip*')
	newline = ''

	for seg in segments:
		try:
			if seg[0] == '<':
				# this is markup don't 'observe' it
				newline += seg
			else:
				words = seg.split(' ')
				lastword = words[-1]
				for word in words:
					try:
						if word[-1] in [',', ';', '.', '?', '!', ')', '′', '“', '·']:
							try:
								if word[-6:] != '&nbsp;':
									word = '<observed id="{wa}">{wa}</observed>{wb} '.format(wa=word[:-1], wb=word[-1])
							except:
								word = '<observed id="{wa}">{wa}</observed>{wb} '.format(wa=word[:-1], wb=word[-1])
						elif word[-1] == '-' and word == lastword:
							word = '<observed id="{h}">{w}</observed> '.format(h=hyphenated, w=word)
						elif word[0] in ['(', '‵', '„', '\'']:
							word = '{wa}<observed id="{wb}">{wb}"</observed> '.format(wa=word[0], wb=word[1:])
						else:
							word = '<observed id="{w}">{w}</observed> '.format(w=word)
						newline += word
					except:
						# word = ''
						pass
		except:
			# seg = ''
			pass
		
	return newline


def insertcrossreferencerow(lineobject):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""
	linehtml = ''

	if re.search(r'documentnumber',lineobject.annotations) is None:
		columna = ''
		columnb = '<span class="crossreference">{ln}</span>'.format(ln=lineobject.annotations)

		linehtml = '<tr class="browser"><td class="crossreference">{c}</td>'.format(c=columnb)
		linehtml += '<td class="crossreference">{c}</td></tr>'.format(c=columna)

	return linehtml


def insertdatarow(label, css, founddate):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""

	columna = ''
	columnb = '<span class="textdate">{l}:&nbsp;{fd}</span>'.format(l=label, fd=founddate)

	linehtml = '<tr class="browser"><td class="{css}">{cb}</td>'.format(css=css, cb=columnb)
	linehtml += '<td class="crossreference">{ca}</td></tr>'.format(ca=columna)

	return linehtml