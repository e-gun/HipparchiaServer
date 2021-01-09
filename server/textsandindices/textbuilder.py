# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.browsing.browserfunctions import checkfordocumentmetadata
from server.dbsupport.dblinefunctions import dblineintolineobject, worklinetemplate
from server.listsandsession.sessionfunctions import findactivebrackethighlighting
from server.startup import workdict
from server.textsandindices.textandindiceshelperfunctions import paragraphformatting, setcontinuationvalue


def buildtext(work: str, firstline: int, lastline: int, linesevery: int, cursor) -> str:
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
	SELECT {wltmp} FROM {a} WHERE (index >= %s and index <= %s) ORDER BY index ASC
	"""
	query = qtemplate.format(wltmp=worklinetemplate, a=auid)

	data = (firstline, lastline)
	cursor.execute(query, data)
	results = cursor.fetchall()

	output = ['<table>\n']

	# consecutive lines can get numbered twice
	# 660	       ἤν τιϲ ὀφείλων ἐξαρνῆται. Πρ. πόθεν οὖν ἐδάνειϲ’ ὁ
	# 660	           δανείϲαϲ,
	avoiddoubletap = False

	linetemplate = determinelinetemplate()

	# pull these outside the "line in results" loop lest you compile the regex 12000x over 1000 lines
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

		lines = [dblineintolineobject(line) for line in results]
		lines = paragraphformatting(lines)  # polish up the HTML of the lines
		for thisline in lines:
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
				columnb = thisline.markedup

			if thisline.samelevelas(previousline) is not True:
				columna = thisline.shortlocus()
			else:
				columna = ''
			try:
				linenumber = int(thisline.l0)
			except ValueError:
				# 973b is not your friend
				linenumber = 0
			if linenumber % linesevery == 0 and not avoiddoubletap:
				columna = thisline.locus()
				avoiddoubletap = True
			else:
				avoiddoubletap = False

			notes = '; '.join(thisline.insetannotations())

			if columna and session['simpletextoutput']:
				columna = '({a})'.format(a=columna)

			linehtml = linetemplate.format(ca=columna, cb=columnb, cc=notes)
	
			output.append(linehtml)

			previousline = thisline
	
	output.append('</table>\n')

	html = '\n'.join(output)

	return html


def determinelinetemplate(shownotes=True) -> str:
	"""

	not esp DRY-friendly: there is a near copy inside the BrowserPassageObject()

	:param shownotes:
	:return:
	"""
	if session['simpletextoutput']:
		linetemplate = """
		<p class="lineoftext">
			{cb}
			&nbsp;
			<span class="browsercite">{ca}</span>
		</p>

		"""
		return linetemplate

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
	return linetemplate
