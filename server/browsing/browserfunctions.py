# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import configparser




from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject
from server.formatting_helper_functions import getpublicationinfo, insertcrossreferencerow, insertdatarow, avoidlonglines
from server import hipparchia

config = configparser.ConfigParser()
config.read('config.ini')

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

	if workobject.universalid[0:2] not in ['in', 'dp', 'ch']:
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

	lines = [dblineintolineobject(r) for r in rawpassage]
	
	focusline = lines[0]
	for line in lines:
		if line.index == locusindexvalue:
			focusline = line
	
	biblio = getpublicationinfo(workobject, cursor)
	
	citation = locusintocitation(workobject, focusline.locustuple())

	cv = '<span class="author">' + name + '</span>, <span class="work">' + title + '</span><br />'
	# author + title can get pretty long
	cv = avoidlonglines(cv, 100, '<br />', [])
	cv += '<span class="citation">'+citation+'</span>'
	if date != '':
		if int(date) > 1:
			cv += '<br /><span class="assigneddate">(Assigned date of '+date+' CE)</span>'
		else:
			cv += '<br /><span class="assigneddate">(Assigned date of ' + date[1:] + ' BCE)</span>'
	cv = cv + '<br />' + biblio
	
	passage['currentlyviewing'] = '<p class="currentlyviewing">' + cv + '</p>'
	passage['ouputtable'] = []
	
	passage['ouputtable'].append('<table>\n')

	# insert something to highlight the citationtuple line
	previousline = lines[0]
	
	datefinder = re.compile(r'<hmu_metadata_date value="(.*?)" />')
	regionfinder = re.compile(r'<hmu_metadata_region value="(.*?)" />')
	cityfinder = re.compile(r'<hmu_metadata_city value="(.*?)" />')
	pubfinder = re.compile(r'<hmu_metadata_publicationinfo value="(.*?)" />')

	for line in lines:
		if workobject.universalid[0:2] in ['in', 'dp', 'ch']:
			if line.annotations != '':
				xref = insertcrossreferencerow(line)
				passage['ouputtable'].append(xref)
			date = re.search(datefinder, line.accented)
			region = re.search(regionfinder, line.accented)
			city = re.search(cityfinder, line.accented)
			pub = re.search(pubfinder, line.accented)
			# line.index == workobject.starts added as a check because
			# otherwise you will re-see date info in the middle of some documents
			# it gets reasserted with a CD block reinitialization
			if region is not None and line.index == workobject.starts:
				html = insertdatarow('Region', 'regioninfo', region.group(1))
				passage['ouputtable'].append(html)
			if city is not None and line.index == workobject.starts:
				html = insertdatarow('City', 'cityinfo', city.group(1))
				passage['ouputtable'].append(html)
			if workobject.provenance is not None and city is None and line.index == workobject.starts:
				html = insertdatarow('Provenance', 'provenance', workobject.provenance)
				passage['ouputtable'].append(html)
			if pub is not None and line.index == workobject.starts:
				html = insertdatarow('Additional publication info', 'pubinfo', pub.group(1))
				passage['ouputtable'].append(html)
			if date is not None and line.index == workobject.starts:
				html = insertdatarow('Editor\'s date', 'textdate', date.group(1))
				passage['ouputtable'].append(html)

		if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
			columnb = line.showlinehtml()
		else:
			columnb = insertparserids(line)

		if line.index == focusline.index:
			columna = line.locus()
			columnb = '<span class="focusline">' + columnb + '</span>'
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
			prefix = '<smallcode>' + line.universalid + '&nbsp;&nbsp;&nbsp;</smallcode>&nbsp;'
		columnb = prefix+columnb

		linehtml = '<tr class="browser"><td class="browsedline">' + columnb + '</td>'
		linehtml += '<td class="browsercite">' + columna + '</td></tr>\n'
		
		passage['ouputtable'].append(linehtml)
		previousline = line

	if hipparchia.config['HTMLDEBUGMODE'] == 'yes':
		passage['ouputtable'].append('</table>\n<span class="emph">(NB: click-to-parse is off if HTMLDEBUGMODE is set)</span>')
	else:
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
									word = '<observed id="%(wa)s">%(wa)s</observed>%(wb)s ' % {'wa': word[:-1], 'wb': word[-1]}
							except:
								word = '<observed id="%(wa)s">%(wa)s</observed>%(wb)s ' % {'wa': word[:-1], 'wb': word[-1]}
						elif word[-1] == '-' and word == lastword:
							word = '<observed id="%(h)s">%(w)s</observed> ' % {'h': hyphenated, 'w': word}
						elif word[0] in ['(', '‵', '„', '\'']:
							word = '%(w0)s<observed id="%(w1)s">%(w1)s"</observed> ' %{'w0': word[0], 'w1': word[1:]}
						else:
							word = '<observed id="%(w)s">%(w)s</observed> ' %{'w': word}
						newline += word
					except:
						# word = ''
						pass
		except:
			# seg = ''
			pass
		
	return newline
