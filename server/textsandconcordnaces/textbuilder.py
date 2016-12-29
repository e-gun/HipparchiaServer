# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
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

	auid = work[0:6]

	query = 'SELECT index, wkuniversalid, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, ' \
			'marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM ' + auid + \
	        ' WHERE (index >= %s and index <= %s) ORDER BY index ASC'
	data = (firstline, lastline)
	cursor.execute(query, data)
	results = cursor.fetchall()
	
	finder = re.compile(r'<hmu_metadata_date value="(.*?)" />')
	
	output = ['<table>\n']
	if len(results) > 0:
		previousline = dblineintolineobject(work, results[0])
		linecount = 0
		for line in results:
			linecount += 1
			thisline = dblineintolineobject(work,line)
			
			if work[0:2] in ['in', 'dp', 'ch']:
				if thisline.annotations != '' and re.search(r'documentnumber',thisline.annotations) is None:
					columna = ''
					columnb = '<span class="crossreference">' + thisline.annotations + '</span>'
					xref = '<tr><td class="browsercite">' + columna + '</td>'
					xref += '<td class="textcrossreference">' + columnb + '</td></tr>\n'
					output.append(xref)
			date = re.search(finder, thisline.accented)
			if date is not None:
				columna = ''
				columnb = '<span class="textdate">Date:&nbsp;' + date.group(1) + '</span>'
				datehtml = '<tr><td class="browsercite">' + columna + '</td>'
				datehtml += '<td class="textdate">' + columnb + '</td></tr>\n'
				output.append(datehtml)
			
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
