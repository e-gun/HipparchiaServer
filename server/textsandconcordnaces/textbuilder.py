# -*- coding: utf-8 -*-
from server.hipparchiaclasses import dbWorkLine
from server.dbsupport.dbfunctions import dblineintolineobject

def buildfulltext(work, linesevery, cursor):
	"""
	make a readable/printable version of a work and send it to its own page
	huge works will overwhelm the ability of most/all browsers to parse that much html
	printing to pdf is a good idea, but for the incredibly slow pace of such
	:param work:
	:param levelcount:
	:param higherlevels:
	:param linesevery:
	:param cursor:
	:return:
	"""
	query = 'SELECT index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, stripped_line, annotations FROM ' + work + ' ORDER BY index ASC'
	cursor.execute(query)
	results = cursor.fetchall()
	
	previousline = dblineintolineobject(work, results[0])

	output = []
	linecount = 0
	for line in results:
		linecount += 1
		thisline = dblineintolineobject(work,line)
		linecore = thisline.marked_up_line
		if thisline.samelevelas(previousline) is not True:
			linecount = linesevery + 1
			linehtml = linecore + '&nbsp;&nbsp;<span class="browsercite">(' + thisline.locus() + ')</span>'
		else:
			linehtml = linecore
			
		if linecount % linesevery == 0:
			linehtml = linecore + '&nbsp;&nbsp;<span class="browsercite">(' + thisline.locus() + ')</span>'

		output.append(linehtml)
		previousline = thisline
	
	return output
