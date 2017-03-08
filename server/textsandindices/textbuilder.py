# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from server.dbsupport.dbfunctions import dblineintolineobject

def buildtext(work, firstline, lastline, linesevery, cursor):
	"""
	make a readable/printable version of a work

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

	# consecutive lines can get numbered twice
	# 660	       ἤν τιϲ ὀφείλων ἐξαρνῆται. Πρ. πόθεν οὖν ἐδάνειϲ’ ὁ
	# 660	           δανείϲαϲ,
	avoiddoubletap = False

	if len(results) > 0:
		previousline = dblineintolineobject(results[0])
		for line in results:
			thisline = dblineintolineobject(line)
			
			if work[0:2] in ['in', 'dp', 'ch']:
				if thisline.annotations != '' and re.search(r'documentnumber',thisline.annotations) is None:
					columna = ''
					columnb = '<span class="crossreference">{notes}</span>'.format(notes=thisline.annotations)
					xref = '<tr><td class="browsercite">{ca}</td><td class="textcrossreference">{cb}</td></tr>\n'.format(ca=columna, cb=columnb)
					output.append(xref)
			date = re.search(finder, thisline.accented)
			if date is not None and thisline.index == firstline:
				columna = ''
				columnb = '<span class="textdate">Date:&nbsp;{date}</span>'.format(date=date.group(1))
				datehtml = '<tr><td class="browsercite">{ca}</td><td class="textdate">{cb}</td></tr>\n'.format(ca=columna, cb=columnb)
				output.append(datehtml)
			
			columnb = thisline.accented
			if thisline.samelevelas(previousline) is not True:
				columna = thisline.shortlocus()
			else:
				columna = ''
			try:
				linenumber = int(thisline.l0)
			except:
				# 973b is not your friend
				linenumber = 0
			if linenumber % linesevery == 0 and avoiddoubletap == False:
				columna = thisline.locus()
				avoiddoubletap = True
			else:
				avoiddoubletap = False
			
			linehtml = '<tr><td class="browsercite">{ca}</td><td class="lineoftext">{cb}</td></tr>\n'.format(ca=columna, cb=columnb)
	
			output.append(linehtml)
			previousline = thisline
	
	output.append('</table>\n')
	
	return output
