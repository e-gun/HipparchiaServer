# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.browsing.browserfunctions import checkfordocumentmetadata
from server.dbsupport.dbfunctions import dblineintolineobject
from server.listsandsession.sessionfunctions import findactivebrackethighlighting
from server.startup import workdict
from server.textsandindices.textandindiceshelperfunctions import setcontinuationvalue


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

	workobject = workdict[work]

	auid = work[0:6]

	qtemplate = """
	SELECT index, wkuniversalid, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, 
			marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM {a}
	        WHERE (index >= %s and index <= %s) ORDER BY index ASC
	"""
	query = qtemplate.format(a=auid)

	data = (firstline, lastline)
	cursor.execute(query, data)
	results = cursor.fetchall()

	output = ['<table>\n']

	# consecutive lines can get numbered twice
	# 660	       ἤν τιϲ ὀφείλων ἐξαρνῆται. Πρ. πόθεν οὖν ἐδάνειϲ’ ὁ
	# 660	           δανείϲαϲ,
	avoiddoubletap = False

	shownotes = True
	if shownotes:
		linetemplate = """
			<tr>
				<td class="browsercite">{ca}</td>
				<td class="lineoftext">{cb}</td>
				<td class="textmakerembeddedannotations">{cc}</td>
			</tr>
		"""
	else:
		linetemplate = """
			<tr>
				<td class="browsercite">{ca}</td>
				<td class="lineoftext">{cb}</td>
			</tr>
		"""

	# pull these outside the loop lest you compile the regex 4000x over 1000 lines
	bracketfinder = {
				'square': {
					'ocreg': re.compile(r'\[(.*?)(\]|$)'),
					'coreg': re.compile(r'(^|\[)(.*?)\]'),
					'class': 'editorialmarker_squarebrackets',
					'o': '[',
					'c': ']'
					},
				'round': {
					'ocreg': re.compile(r'\((.*?)(\)|$)'),
					'coreg': re.compile(r'(^|\()(.*?)\)'),
					'class': 'editorialmarker_roundbrackets',
					'o': '(',
					'c': ')'
				},
				'angled': {
					'ocreg': re.compile(r'⟨(.*?)(⟩|$)'),
					'coreg': re.compile(r'(^|⟨)(.*?)⟩'),
					'class': 'editorialmarker_angledbrackets',
					'o': '⟨',
					'c': '⟩'
				},
				'curly': {
					'ocreg': re.compile(r'\{(.*?)(\}|$)'),
					'coreg': re.compile(r'(^|\{)(.*?)\}'),
					'class': 'editorialmarker_curlybrackets',
					'o': '{',
					'c': '}'
				}
			}

	openfinder = {
		'square': {'regex': re.compile(r'\[[^\]]{0,}$'),
		            'exceptions': [re.compile(r'\[(ϲτρ|ἀντ)\. .\.'), re.compile(r'\[ἐπῳδόϲ')]},
		'round': {'regex': re.compile(r'\([^\)]{0,}$')},
		'angled': {'regex': re.compile(r'⟨[^⟩]{0,}$')},
		'curly': {'regex': re.compile(r'\{[^\}]{0,}$')},
	}

	closefinder = {
			'square': {'c': re.compile(r'\]')},
			'round': {'c': re.compile(r'\)')},
			'angled': {'c': re.compile(r'⟩')},
			'curly': {'c': re.compile(r'\}')},
	}

	if results:
		previousline = dblineintolineobject(results[0])
		brackettypes = findactivebrackethighlighting()
		editorialcontinuation = {'square': False, 'round': False, 'curly': False, 'angled': False}

		for line in results:
			thisline = dblineintolineobject(line)
			if workobject.isnotliterary() and thisline.index == workobject.starts:
				# line.index == workobject.starts added as a check because
				# otherwise you will re-see date info in the middle of some documents
				# it gets reasserted with a CD block reinitialization
				metadata = checkfordocumentmetadata(thisline, workobject)
				if metadata:
					output.append(metadata)

			if brackettypes:
				columnb = thisline.markeditorialinsersions(editorialcontinuation, bracketfinder=bracketfinder)
				editorialcontinuation = {t: setcontinuationvalue(thisline, previousline, editorialcontinuation[t], t, openfinder=openfinder, closefinder=closefinder)
				                         for t in brackettypes}
			else:
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
			if linenumber % linesevery == 0 and not avoiddoubletap:
				columna = thisline.locus()
				avoiddoubletap = True
			else:
				avoiddoubletap = False

			notes = '; '.join(thisline.insetannotations())

			linehtml = linetemplate.format(ca=columna, cb=columnb, cc=notes)
	
			output.append(linehtml)

			previousline = thisline
	
	output.append('</table>\n')

	html = '\n'.join(output)

	return html
