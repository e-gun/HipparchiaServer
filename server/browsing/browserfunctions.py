import re

from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject
from server.formatting_helper_functions import getpublicationinfo


def getandformatbrowsercontext(authorobject, workobject, locusindexvalue, linesofcontext, numbersevery, cursor):
	"""
	this function does a lot of work via a number of subfunctions
	lots of refactoring required if you change anything...
	:param authorobject:
	:param worknumber:
	:param citationtuple:
	:param linesofcontext:
	:param numbersevery:
	:param cursor:
	:return:
	"""
	
	table = workobject.universalid
	title = workobject.title

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
	
	formattedpassage = []
	formattedpassage.append({'forwardsandback': [last,first]})

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

	cv = '<span class="author">'+authorobject.shortname+'</span>, <span class="work">'+title+'</span>, '+ citation
	cv = cv + '<br />' + biblio
	formattedpassage.append({'value':'<currentlyviewing>'+cv+'</currentlyviewing><br /><br />'})
	
	formattedpassage.append({'value': '<table>\n'})
	
	linecount = numbersevery - 3
	# insert something to highlight the citationtuple line
	previousline = lines[0]
	for line in lines:
		linecount += 1
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
				columna = ''
		
		linehtml = '<tr class="browser"><td class="browsedline">' + columnb + '</td>'
		linehtml += '<td class="browsercite">' + columna + '</td></tr>\n'
		
		formattedpassage.append({'value':linehtml})
		previousline = line
	
	formattedpassage.append({'value': '</table>\n'})
	
	return formattedpassage


def insertparserids(lineobject):
	# set up the clickable thing for the browser
	# this is tricky because there is html in here and you don't want to tag it
	
	theline = re.sub(r'(\<.*?\>)',r'*snip*\1*snip*',lineobject.contents)
	hyphenated = lineobject.hyphenated['accented']
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
