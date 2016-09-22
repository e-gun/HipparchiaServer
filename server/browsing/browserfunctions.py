import re

from server.dbsupport.citationfunctions import locusintocitation
from server.dbsupport.dbfunctions import simplecontextgrabber
from server.formatting_helper_functions import getpublicationinfo


def getandformatbrowsercontext(authorobject, worknumber, citationtuple, linesofcontext, numbersevery, cursor):
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

	# citationtuple ('9','109','8') to focus on line 9, section 109, book 8
	# we will grab more than we need so we can set the 'nextpage' stuff right
	rawpassage = simplecontextgrabber(workobject, citationtuple, linesofcontext*2, cursor)
	# (71, None, '-1', '-1', '-1', '1', '70', "ὃϲ ᾔδη τά τ' ἐόντα τά τ' ἐϲϲόμενα πρό τ' ἐόντα, <hmu_endofpage /> ", "οϲ ηδη τα τ' εοντα τα τ' εϲϲομενα προ τ' εοντα,  ", '', '')
	# info for the 'back' and 'forward' buttons: need something like 'gr0026w001_AT_3|88' in the end
	formattedpassage = []
	# enable a check to see if you tried to bite more than you can chew
	workstarts, workstops = findfirstandlastlineofwork(workobject.universalid, cursor)

	try:
		first = list(rawpassage[0][1:7])
	except:
		first = list(workstarts[1:7])
	first.reverse()
	
	try:
		last = list(rawpassage[-1][1:7])
	except:
		last = list(workstops[1:7])
	last.reverse()
	
	first[:] = [x for x in first if (x != '-1') and (x != None)]
	last[:] = [x for x in last if (x != '-1') and (x != None)]
	first = '|'.join(first)
	last = '|'.join(last)

	first = table + '_AT_' + first
	last = table + '_AT_' + last
	formattedpassage.append({'forwardsandback': [last,first]})
	# now we get what we really want to see
	# recalling rather than pruning because think about what happens if you are at the beginning or end of the work
	rawpassage = simplecontextgrabber(workobject, citationtuple, linesofcontext, cursor)
	biblio = getpublicationinfo(workobject, cursor)
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