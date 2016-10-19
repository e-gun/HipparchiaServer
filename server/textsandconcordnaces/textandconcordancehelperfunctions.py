# -*- coding: utf-8 -*-
import re

from server.dbsupport.dbfunctions import grabonelinefromwork, dblineintolineobject, makeanemptyauthor, makeanemptywork
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.searching.searchfunctions import whereclauses

def tcparserequest(request, authordict, workdict):
	"""
	return the author, work, and locus requested
	also some other handy veriable derived from these items
	:param requestobject:
	:return:
	"""
	
	try:
		workid = re.sub('[\W_]+', '', request.args.get('work', ''))
	except:
		workid = ''

	try:
		uid = re.sub('[\W_]+', '', request.args.get('auth', ''))
	except:
		uid = ''

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
					ao = makeanemptyauthor('gr0000')
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
	line = grabonelinefromwork(workobject.universalid, passage, cursor)
	lo = dblineintolineobject(workobject.universalid, line)
	
	# let's say you looked for 'book 2' of something that has 'book, chapter, line'
	# that means that you want everything that has the same level2 value as the lineobject
	# build a where clause
	passageaslist.reverse()
	atloc = '|'.join(passageaslist)
	selection = workobject.universalid + '_AT_' + atloc
	
	w = whereclauses(selection, '=', {authorobject.universalid: authorobject})
	d = []
	qw = ''
	for i in range(0, len(w)):
		qw += 'AND (' + w[i][0] + ') '
		d.append(w[i][1])
	# remove the leading AND
	qw = qw[4:]
	query = 'SELECT index FROM ' + workobject.universalid + ' WHERE ' + qw + ' ORDER BY index DESC LIMIT 1'
	data = tuple(d)
	cursor.execute(query, data)
	found = cursor.fetchone()
	
	startandstop = {}
	startandstop['startline'] = lo.index
	startandstop['endline'] = found[0]
	
	
	return startandstop