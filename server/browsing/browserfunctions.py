import re

from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber, indexintocitationtuple
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

	# enable a check to see if you tried to bite more than you can chew
	workstarts, workstops = findfirstandlastlineofwork(workobject.universalid, cursor)
	
	if locusindexvalue - linesofcontext < workstarts[0]:
		first = workstarts[0]
	else:
		first = locusindexvalue - linesofcontext
	
	if locusindexvalue + linesofcontext > workstops[0]:
		last = workstops[0]
	else:
		last = locusindexvalue + linesofcontext
	
	first = table + '_LN_' + str(first)
	last = table + '_LN_' + str(last)
	
	formattedpassage = []
	formattedpassage.append({'forwardsandback': [last,first]})

	rawpassage = simplecontextgrabber(workobject, locusindexvalue, linesofcontext, cursor)
	biblio = getpublicationinfo(workobject, cursor)
	
	# ripe for refactoring?
	citationtuple = indexintocitationtuple(workobject.universalid, locusindexvalue, cursor)
	cv = locusintocitation(workobject, citationtuple)
	cv = '<span class="author">'+authorobject.shortname+'</span>, <span class="work">'+title+'</span>, '+cv
	cv = cv + '<br />' + biblio
	formattedpassage.append({'value':'<currentlyviewing>'+cv+'</currentlyviewing>'})
	linecount = 0
	# insert something to highlight the citationtuple line
	for line in rawpassage:
		linecount += 1
		linecore = line[7]
		linecore = insertparserids(linecore)
		if (linecount % numbersevery != 0) and divmod(linesofcontext,linecount) != (1,linecount-1) and divmod(linesofcontext,linecount) != (1,linecount-2):
			# nothing special: neither the focus line nor a numbered line
			linehtml = '<p class="browsedline">'+linecore+'</p>'
		elif (linecount % numbersevery == 0) and (divmod(linesofcontext,linecount) == (1,linecount-1) or divmod(linesofcontext,linecount) == (1,linecount-2)):
			# a numbered line and a focus line
			linehtml = '<p class="focusline">' + linecore +'&nbsp;&nbsp;<span class="browsercite">('
			for level in range(len(citationtuple) - 1, -1, -1):
				linehtml += line[6 - level] + '.'
			linehtml = linehtml[:-1] + ')</span></p>'
		elif divmod(linesofcontext,linecount) == (1,linecount-1) or divmod(linesofcontext,linecount) == (1,linecount-2):
			# a focusline
			linehtml = '<p class="focusline">' + linecore +'</p>'
		else:
			# a numbered line
			linehtml = '<p class="browsedline">'+linecore+'&nbsp;&nbsp;<span class="browsercite">('
			for level in range(len(citationtuple)-1,-1,-1):
				linehtml += line[6-level]+'.'
			linehtml = linehtml[:-1]+')</span></p>'
		formattedpassage.append({'value':linehtml})
		
	return formattedpassage


def insertparserids(onelineoftext):
	# set up the clickable thing for the browser
	# this is tricky because there is html in here and you don't want to tag it

	theline = re.sub(r'(\<.*?\>)',r'*snip*\1*snip*',onelineoftext)
	segments = theline.split('*snip*')
	newline = ''
	
	for seg in segments:
		try:
			if seg[0] == '<':
				# this is markup don't 'observe' it
				newline += seg
			else:
				words = seg.split(' ')
				for word in words:
					try:
						if word[-1] in [',', ';', '.', '?', '!', ')', '′', '“', '·']:
							try:
								if word[-6:] != '&nbsp;':
									word = '<observed id="' + word[:-1] + '">' + word[:-1] + '</observed>' + word[-1] + ' '
							except:
								word = '<observed id="' + word[:-1] + '">' + word[:-1] + '</observed>' + word[-1] + ' '
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