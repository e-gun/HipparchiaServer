# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

from server.dbsupport.dbfunctions import dblineintolineobject

def buildtext(work, firstline, lastline, linesevery, cursor):
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
	query = 'SELECT index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM ' + work + \
	        ' WHERE (index >= %s and index <= %s) ORDER BY index ASC'
	data = (firstline, lastline)
	cursor.execute(query, data)
	results = cursor.fetchall()
	
	output = ['<table>\n']
	if len(results) > 0:
		previousline = dblineintolineobject(work, results[0])
		linecount = 0
		for line in results:
			linecount += 1
			thisline = dblineintolineobject(work,line)
			columnb = thisline.accented
			if thisline.samelevelas(previousline) is not True:
				linecount = linesevery + 1
				columna = thisline.shortlocus()
			else:
				columna = ''
			if linecount % linesevery == 0:
				columna = thisline.locus()
			
			linehtml = '<tr><td class="browsercite">'+columna+'</td>'
			linehtml += '<td class="lineoftext">'+columnb+'</td></tr>\n'
	
			output.append(linehtml)
			previousline = thisline
	
	output.append('</table>\n')
	
	return output
