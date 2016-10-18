import re

from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, dblineintolineobject
from server.formatting_helper_functions import getpublicationinfo


def getandformatbrowsercontext(authorobject, worknumber, locusindexvalue, linesofcontext, numbersevery, cursor):
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
	
	# work ID va work position on list of works problem: Euripides' work list starts at "gr0006w020";"Fragmenta"
	# so you need to match the wk # to the right object early
	for worktocheck in authorobject.listofworks:
		if worktocheck.worknumber == worknumber:
			workobject = worktocheck
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
	formattedpassage.append({'value':'<currentlyviewing>'+cv+'</currentlyviewing>'})
	
	linecount = 0
	# insert something to highlight the citationtuple line
	previousline = lines[0]
	for line in lines:
		linecount += 1
		linecore = insertparserids(line)
		if line.index == focusline.index:
			linecount = numbersevery + 1
			linehtml = '<p class="focusline">' + linecore + '&nbsp;&nbsp;(' + line.locus() + ')</p>'
		else:
			if line.samelevelas(previousline) is not True:
				linecount = numbersevery + 1
				linehtml = '<p class="browsedline">' + linecore + '&nbsp;&nbsp;<span class="browsercite">(' + line.shortlocus() + ')</span></p>'
			elif linecount % numbersevery == 0:
				linehtml = '<p class="browsedline">' + linecore + '&nbsp;&nbsp;<span class="browsercite">(' + line.locus() + ')</span></p>'
			else:
				linehtml = '<p class="browsedline">' + linecore + '</p>'
		
		formattedpassage.append({'value':linehtml})
		previousline = line
		
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


# slated for removal

def findfirstandlastlineofwork(workdbname, cursor):
	"""
	used to keep the browser from attempting to browse beyond the end of the text
	:param worknumber:
	:return:
	"""
	query = 'SELECT * FROM ' + workdbname + ' ORDER BY index ASC'
	cursor.execute(query)
	firstline = cursor.fetchone()
	
	query = 'SELECT * FROM ' + workdbname + ' ORDER BY index DESC'
	cursor.execute(query)
	lastline = cursor.fetchone()
	
	return firstline,lastline
