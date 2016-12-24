# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re

from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject
from server.formatting_helper_functions import getpublicationinfo, insertcrossreferencerow, insertdatarow


def getandformatbrowsercontext(authorobject, workobject, locusindexvalue, linesofcontext, numbersevery, cursor):
	"""
	his function does a lot of work via a number of subfunctions
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

	table = workobject.universalid
	title = workobject.title
	try:
		if int(workobject.converted_date) < 1500:
			date = str(workobject.converted_date)
		else:
			date = ''
	except:
		date = ''
	
	if locusindexvalue - linesofcontext < workobject.starts:
		first = workobject.starts
	else:
		first = locusindexvalue - linesofcontext
	
	if locusindexvalue + linesofcontext > workobject.ends:
		last = workobject.ends
	else:
		last = locusindexvalue + linesofcontext
	
	# for the <-- and --> buttons on the browser
	first = table + '_LN_' + str(first)
	last = table + '_LN_' + str(last)
	
	passage = {}
	# will be used with the browse forwards and back buttons
	passage['browseforwards'] = last
	passage['browseback'] = first
	
	# will be used to fill the autocomplete boxes
	passage['authornumber'] = authorobject.universalid
	passage['workid'] = workobject.universalid
	# as per offerauthorhints() in views.py
	passage['authorboxcontents'] = authorobject.cleanname+' ['+authorobject.universalid+']'
	# offerworkhints()
	passage['workboxcontents'] = workobject.title+' ('+workobject.universalid[-4:]+')'
	
	rawpassage = simplecontextgrabber(workobject, locusindexvalue, linesofcontext, cursor)
	
	lines = []
	for r in rawpassage:
		lines.append(dblineintolineobject(workobject.universalid, r))
	
	focusline = lines[0]
	for line in lines:
		if line.index == locusindexvalue:
			focusline = line
	
	biblio = getpublicationinfo(workobject, cursor)
	
	citation = locusintocitation(workobject, focusline.locustuple())
	
	cv = '<span class="author">' + authorobject.shortname + '</span>, <span class="work">' + title + '</span><br />' + citation
	if date != '':
		if int(date) > 1:
			cv += '<br /><span class="assigneddate">(Assigned date of '+date+' CE)</span>'
		else:
			cv += '<br /><span class="assigneddate">(Assigned date of ' + date[1:] + ' BCE)</span>'
	cv = cv + '<br />' + biblio
	
	passage['currentlyviewing'] = '<currentlyviewing>' + cv + '</currentlyviewing>'
	passage['ouputtable'] = []
	
	passage['ouputtable'].append('<table>\n')
	
	linecount = numbersevery - 3
	# insert something to highlight the citationtuple line
	previousline = lines[0]
	
	datefinder = re.compile(r'<hmu_metadata_date value="(.*?)" />')
	regionfinder = re.compile(r'<hmu_metadata_region value="(.*?)" />')
	cityfinder = re.compile(r'<hmu_metadata_city value="(.*?)" />')
	pubfinder = re.compile(r'<hmu_metadata_publicationinfo value="(.*?)" />')

	for line in lines:
		linecount += 1
		if workobject.universalid[0:2] in ['in', 'dp']:
			if line.annotations != '':
				xref = insertcrossreferencerow(line)
				passage['ouputtable'].append(xref)
			date = re.search(datefinder, line.accented)
			region = re.search(regionfinder, line.accented)
			city = re.search(cityfinder, line.accented)
			pub = re.search(pubfinder, line.accented)
			if region is not None:
				html = insertdatarow('Region', 'regioninfo', region.group(1))
				passage['ouputtable'].append(html)
			if city is not None:
				html = insertdatarow('City', 'cityinfo', city.group(1))
				passage['ouputtable'].append(html)
			if pub is not None:
				html = insertdatarow('Publication', 'pubinfo', pub.group(1))
				passage['ouputtable'].append(html)
			if date is not None and line.index == workobject.starts:
				# otherwise you will resee date info in the middle of some documents because
				# it gets reasserted with a CD block reinitialization
				html = insertdatarow('Editor\'s date', 'textdate', date.group(1))
				passage['ouputtable'].append(html)

		columnb = insertparserids(line)
		if line.index == focusline.index:
			# linecount = numbersevery + 1
			columna = line.locus()
			columnb = '<span class="focusline">' + columnb + '</span>'
		else:
			if line.samelevelas(previousline) is not True:
				linecount = numbersevery + 1
				columna = line.shortlocus()
			elif linecount % numbersevery == 0:
				columna = line.locus()
			else:
				# do not insert a line number or special formatting
				columna = ''
		
		linehtml = '<tr class="browser"><td class="browsedline">' + columnb + '</td>'
		linehtml += '<td class="browsercite">' + columna + '</td></tr>\n'
		
		passage['ouputtable'].append(linehtml)
		previousline = line
		
	passage['ouputtable'].append('</table>\n')
	
	return passage


def insertparserids(lineobject):
	# set up the clickable thing for the browser
	# this is tricky because there is html in here and you don't want to tag it
	
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
									word = '<observed id="' + word[:-1] + '">' + word[:-1] + '</observed>' + word[-1] + ' '
							except:
								word = '<observed id="' + word[:-1] + '">' + word[:-1] + '</observed>' + word[-1] + ' '
						elif word[-1] == '-' and word == lastword:
							word = '<observed id="' + hyphenated + '">' + word + '</observed> '
						elif word[0] in ['(', '‵', '„', '\'']:
							word = word[0] + '<observed id="' + word[1:] + '">' + word[1:] + '</observed> '
						else:
							word = '<observed id="' + word + '">' + word + '</observed> '
						newline += word
					except:
						# word = ''
						pass
		except:
			# seg = ''
			pass
		
	return newline
