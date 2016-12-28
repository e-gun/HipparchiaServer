# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re
import time
from string import punctuation
from collections import deque

from server.dbsupport.dbfunctions import grabonelinefromwork, dblineintolineobject, makeanemptyauthor, makeanemptywork
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.listsandsession.listmanagement import polytonicsort
from server.searching.searchfunctions import whereclauses

def tcparserequest(request, authordict, workdict):
	"""
	return the author, work, and locus requested
	also some other handy veriable derived from these items
	:param requestobject:
	:return:
	"""
	
	try:
		uid = re.sub('[\W_]+', '', request.args.get('auth', ''))
	except:
		uid = ''
		
	try:
		workid = re.sub('[\W_]+', '', request.args.get('work', ''))
	except:
		workid = ''

	try:
		locus = re.sub('[!@#$%^&*()=]+', '', request.args.get('locus', ''))
	except:
		locus = ''
	
	workdb = uid + 'w' + workid
	
	if uid != '':
		try:
			ao = authordict[uid]
			if len(workdb) == 10:
				try:
					wo = workdict[workdb]
				except:
					wo = makeanemptywork('gr0000w000')
			else:
					wo = makeanemptywork('gr0000w000')
		except:
			ao = makeanemptyauthor('gr0000')
			wo = makeanemptywork('gr0000w000')
		
		passage = locus.split('|')
		passage.reverse()

	else:
		ao = makeanemptyauthor('gr0000')
		wo = makeanemptywork('gr0000w000')
		passage = []
	
	req = {}
	
	req['authorobject'] = ao
	req['workobject'] = wo
	req['passagelist'] = passage
	req['rawlocus'] = locus
	
	return req


def tcfindstartandstop(authorobject, workobject, passageaslist, cursor):
	"""
	find the first and last lines of a work segment
	:return:
	"""
	
	p = tuple(passageaslist)
	passage = finddblinefromincompletelocus(workobject.universalid, p, cursor)
	line = grabonelinefromwork(authorobject.universalid, passage, cursor)
	lo = dblineintolineobject(workobject.universalid, line)
	
	# let's say you looked for 'book 2' of something that has 'book, chapter, line'
	# that means that you want everything that has the same level2 value as the lineobject
	# build a where clause
	passageaslist.reverse()
	atloc = '|'.join(passageaslist)
	selection = workobject.universalid + '_AT_' + atloc
	
	w = whereclauses(selection, '=', {authorobject.universalid: authorobject})
	d = [workobject.universalid]
	qw = ''
	for i in range(0, len(w)):
		qw += 'AND (' + w[i][0] + ') '
		d.append(w[i][1])

	query = 'SELECT index FROM ' + authorobject.universalid + ' WHERE wkuniversalid=%s ' + qw + ' ORDER BY index DESC LIMIT 1'
	data = tuple(d)

	cursor.execute(query, data)
	found = cursor.fetchone()
	
	startandstop = {}
	startandstop['startline'] = lo.index
	startandstop['endline'] = found[0]
	
	
	return startandstop


def conctohtmltable(concordanceoutput):
	"""
	pre-pack the concordance output into an html table so that the page JS can just iterate through a set of lines when the time comes
	each result in the list is itself a list: [word, count, lociwherefound]
	
	input:
		('καλεῖϲθαι', '1', '1.2')
		('καλεῖται', '1', '1.4')
		...
	:param concordanceoutput:
	:return:
	"""

	outputlines = deque()
	outputlines.append('<table><tr><th>word</th><th>count</th><th>passages</th></tr>\n')
	for c in concordanceoutput:
		outputlines.append('<tr>')
		outputlines.append('<td class="word"><observed id="'+c[0]+'">'+c[0]+'</observed></td>')
		outputlines.append('<td class="count">'+c[1]+'</td>')
		outputlines.append('<td class="passages">' + c[2] + '</td>')
		outputlines.append('</tr>')
	outputlines.append('</table>')
	
	return list(outputlines)
	

def concordancesorter(unsortedoutput):
	"""
	you can't sort the list and then send it to a mp function where it will get unsorted
	so you have to jump through a hoop before you can jump through a hoop:
	make keys -> polytonicsort keys -> use keys to sort the list
	
	input:
		('καλεῖται', '1', '1.4'),
		('ἀθηναίοιϲ', '1', '1.3'),
		...
		
	:param unsortedoutput:
	:return:
	"""
	
	# now you sort
	sortkeys = []
	outputdict = {}
	for o in unsortedoutput:
		sortkeys.append(o[0])
		outputdict[o[0]] = o
		
	sortkeys = polytonicsort(sortkeys)
	del unsortedoutput

	sortedoutput = deque()
	for k in sortkeys:
		sortedoutput.append(outputdict[k])
	return sortedoutput


def cleanwords(word):
	"""
	remove gunk that should not be in a concordance
	:param word:
	:return:
	"""
	punct = re.compile('[%s]' % re.escape(punctuation + '\′‵’‘·“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'))
	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)
	# best do punct before this next one...
	try:
		if re.search(r'[a-zA-z]', word[0]) is None:
			word = re.sub(r'[a-zA-z]', '', word)
	except:
		# must have been ''
		pass
	
	return word
