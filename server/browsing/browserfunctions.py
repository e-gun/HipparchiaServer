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
	viewing = avoidlonglines(authorandwork, 100, '<br />', [])
	viewing += '<span class="citation">{c}</span>'.format(c=citation)
	if date != '':
		if int(date) > 1:
			viewing += '<br /><span class="assigneddate">(Assigned date of {d} CE)</span>'.format(d=date)
		else:
			viewing += '<br /><span class="assigneddate">(Assigned date of {d} BCE)</span>'.format(d=date[1:])

	viewing = '<p class="currentlyviewing">{c}<br />{b}</p>'.format(c=viewing, b=biblio)

	ouputtable = []
	ouputtable.append('<table>')

	# guarantee a minimum width to the browser dialogue box; or else skip adding this blank row
	try:
		spacer = ''.join(['&nbsp;' for i in range(0, hipparchia.config['MINIMUMBROWSERWIDTH'])])
		ouputtable.append('<tr class="spacing">{sp}</tr>'.format(sp=spacer))
	except:
		pass

	previousline = lines[0]
	editorialcontinuation = False

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
			columnb = insertparserids(line, editorialcontinuation)

		brackettypes = findactivebrackethighlighting()
		if brackettypes:
			editorialcontinuation = setcontinuationvalue(line, previousline, editorialcontinuation)

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


def insertparserids(lineobject, editorialcontinuation=False):
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

	theline = lineobject.accented

	brackettypes = findactivebrackethighlighting()
	if brackettypes:
		theline = lineobject.markeditorialinsersions(brackettypes, editorialcontinuation)

	theline = re.sub(r'(\<.*?\>)',r'*snip*\1*snip*',theline)
	hyphenated = lineobject.hyphenated
	segments = [s for s in theline.split('*snip*') if s]
	newline = ['']

	# it is tricky to get the tags and the spaces right: it looks like you either get one kind of glitch or another kind
	# the lesser of two evils has been chosen?
	spacedclosings = re.compile(r'[,;.?!:·′“”†]$')
	sometimesspacedclosings = re.compile(r'[)⟩}]$')
	openings = re.compile(r'^[(‵„“⟨{†]')

	for seg in segments:
		if seg[0] == '<':
			# this is markup don't 'observe' it
			# '+=' will prevent an extra whitespace from appearing in the html
			# as seen below: these require extra cleaning in the end
			newline[-1] += seg
		else:
			words = seg.split(' ')
			words = [w for w in words if len(w) > 0]
			try:
				lastword = words[-1]
			except IndexError:
				lastword = ''

			for word in words:
				try:
					if re.search(spacedclosings, word) or re.search(sometimesspacedclosings, word):
						try:
							if word[-6:] != '&nbsp;':
								word = '<observed id="{wa}">{wa}</observed>{wb} '.format(wa=word[:-1], wb=word[-1])
						except:
							word = '<observed id="{wa}">{wa}</observed>{wb} '.format(wa=word[:-1], wb=word[-1])
					# elif re.search(sometimesspacedclosings, word):
					# 	word = '<observed id="{wa}">{wa}</observed>{wb}'.format(wa=word[:-1], wb=word[-1])
					elif word[-1] == '-' and word == lastword:
						word = '<observed id="{h}">{w}</observed> '.format(h=hyphenated, w=word)
					elif re.search(openings, word):
						word = '{wa}<observed id="{wb}">{wb}</observed> '.format(wa=word[0], wb=word[1:])
					else:
						word = '<observed id="{w}">{w}</observed> '.format(w=word)
					newline.append(word)
				except:
					# word = ''
					pass

	# address dodgy word division and ill-formatted word spacing issues: 'ἱε[ ρέω ]ϲ' instead of 'ἱε[ρέω]ϲ'
	ob = re.compile(r'<observed id=""></observed>')
	newline = [re.sub(ob, '', n) for n in newline]
	newline = [re.sub('> <', '><', n) for n in newline]
	newline = ''.join(newline)
	newline = re.sub(r'\s(</span>)([⟩\)\]\}])', r'\1\2', newline)
	newline = re.sub(r'([⟨\(\[\{])\s(<span)', r'\1\2', newline)

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