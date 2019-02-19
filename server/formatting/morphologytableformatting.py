# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session


def findmygreektenses(mood: str, voice: str) -> dict:
	"""

	what might actually be available?

	:param mood:
	:param voice:
	:return:
	"""

	# the lists of moods, voices is set to match the parser abbreviations
	# note that 'mp' is used for 'middle/passive': it should have disappeared before now

	moods = ['ind', 'subj', 'opt', 'imperat', 'inf', 'part']
	voices = ['act', 'mid', 'pass']

	assert mood in moods, 'invalid mood submitted to findmygreektenses(): {m}'.format(m=mood)
	assert voice in voices, 'invalid voice submitted to findmygreektenses(): {v}'.format(v=voice)

	alltenses = {1: 'Present', 2: 'Imperfect', 3: 'Future', 4: 'Aorist', 5: 'Perfect', 6: 'Pluperfect', 7: 'Future Perfect'}

	availabletenses = {
		'act': {
			'ind': {1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: False},
			'subj': {1: True, 2: False, 3: False, 4: True, 5: True, 6: False, 7: False},
			'opt': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: False},
			'imperat': {1: True, 2: False, 3: False, 4: True, 5: True, 6: False, 7: False},
			'inf': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: False},
			'part': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: False}
			},
		'mid': {
			'ind': {1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: False},
			'subj': {1: True, 2: False, 3: False, 4: True, 5: True, 6: False, 7: False},
			'opt': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: False},
			'imperat': {1: True, 2: False, 3: False, 4: True, 5: True, 6: False, 7: False},
			'inf': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: False},
			'part': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: False}
			},
		'pass': {
			'ind': {1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: True},
			'subj': {1: True, 2: False, 3: False, 4: True, 5: True, 6: False, 7: False},
			'opt': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: True},
			'imperat': {1: True, 2: False, 3: False, 4: True, 5: True, 6: False, 7: False},
			'inf': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: True},
			'part': {1: True, 2: False, 3: True, 4: True, 5: True, 6: False, 7: True}
			}
		}

	mytenses = {k: alltenses[k] if availabletenses[voice][mood][k] else str() for k in alltenses}

	return mytenses


def findmylatintenses(mood: str, voice: str) -> dict:
	"""

	what might actually be available?

	:param mood:
	:param voice:
	:return:
	"""

	# the lists of moods, voices is set to match the parser abbreviations
	# note that 'mp' is used for 'middle/passive': it should have disappeared before now

	# don't actually know how to do 'gerund', 'gerundive', 'supine' yet
	moods = ['ind', 'subj', 'imperat', 'inf', 'part', 'gerundive', 'supine']
	voices = ['act', 'pass']

	assert mood in moods, 'invalid mood submitted to findmygreektenses(): {m}'.format(m=mood)
	assert voice in voices, 'invalid voice submitted to findmygreektenses(): {v}'.format(v=voice)

	alltenses = {1: 'Present', 2: 'Imperfect', 3: 'Future', 5: 'Perfect', 6: 'Pluperfect', 7: 'Future Perfect'}

	# note that ppf subj pass, etc are 'False' because 'laudātus essem' is not going to be found
	# one could generate it...
	availabletenses = {
		'act': {
			'ind': {1: True, 2: True, 3: True, 5: True, 6: True, 7: True},
			'subj': {1: True, 2: False, 3: False, 5: True, 6: True, 7: False},
			'imperat': {1: True, 2: False, 3: True, 5: False, 6: False, 7: False},
			'inf': {1: True, 2: False, 3: False, 5: True, 6: False, 7: False},
			'part': {1: True, 2: False, 3: True, 5: False, 6: False, 7: False}
			},
		'pass': {
			'ind': {1: True, 2: True, 3: True, 5: False, 6: False, 7: False},
			'subj': {1: True, 2: True, 3: False, 5: False, 6: False, 7: False},
			'imperat': {1: True, 2: False, 3: True, 5: False, 6: False, 7: False},
			'inf': {1: True, 2: False, 3: False, 5: False, 6: False, 7: False},
			'part': {1: False, 2: False, 3: False, 5: True, 6: False, 7: False}
			}
		}

	mytenses = {k: alltenses[k] if availabletenses[voice][mood][k] else str() for k in alltenses}

	return mytenses


def verbtabletemplate(mood: str, voice: str, dialect='attic', duals=True, lang='greek') -> str:
	"""

	Smythe §383ff

	cells look like:

		<td class="morphcell">_attic_subj_pass_pl_2nd_pres_</td>

	:return:
	"""

	if session['morphduals'] == 'no':
		duals = False

	if lang == 'greek':
		mytenses = findmygreektenses(mood, voice)

	if lang == 'latin':
		mytenses = findmylatintenses(mood, voice)

	tabletemplate = """
	<table class="verbanalysis">
	<tbody>
	{header}
	{rows}
	</tbody>
	</table>
	<hr class="styled">
	"""

	headerrowtemplate = """
	<tr align="center">
		<td rowspan="1" colspan="{s}" class="dialectlabel">{dialect}<br>
		</td>
	</tr>
	<tr align="center">
		<td rowspan="1" colspan="{s}" class="voicelabel">{voice}<br>
		</td>
	</tr>
	<tr align="center">
		<td rowspan="1" colspan="{s}" class="moodlabel">{mood}<br>
		</td>
	{tenseheader}
	</tr>"""

	tensestemplate = """<tr>
		<td class="tenselabel">&nbsp;</td>
		{alltenses}
	</tr>"""

	blank = """
	<tr><td>&nbsp;</td>{columns}</tr>
	"""

	blankrow = blank.format(columns=''.join(['<td>&nbsp;</td>' for k in sorted(mytenses.keys()) if mytenses[k]]))

	tensecell = '<td class="tensecell">{t}<br></td>'
	tenserows = [tensecell.format(t=mytenses[k]) for k in sorted(mytenses.keys()) if mytenses[k]]
	tenserows = '\n\t\t'.join(tenserows)
	tenseheader = tensestemplate.format(alltenses=tenserows)
	fullheader = headerrowtemplate.format(dialect=dialect, voice=voice, mood=mood, tenseheader=tenseheader, s=len(mytenses))

	allrows = list()

	# cell arrangement: left to right and top to bottom is vmnpt
	# i.e., voice, mood, number, person, tense
	# we are doing the npt part here

	# the lists of numbers, persons, tenses, etc is set to match the parser abbreviations

	cases = list()
	if lang == 'latin':
		cases = ['nom', 'gen', 'dat', 'acc', 'abl', 'voc']

	if lang == 'greek':
		cases = ['nom', 'gen', 'dat', 'acc', 'voc']

	genders = ['masc', 'fem', 'neut']

	if duals:
		numbers = ['sg', 'dual', 'pl']
	else:
		numbers = ['sg', 'pl']

	persons = ['1st', '2nd', '3rd']
	tensedict = {1: 'pres', 2: 'imperf', 3: 'fut', 4: 'aor', 5: 'perf', 6: 'plup', 7: 'futperf'}
	tenses = [tensedict[k] for k in sorted(mytenses.keys()) if mytenses[k]]

	morphrowtemplate = """
	<tr class="morphrow">
		{allcells}
	</tr>
	"""

	morphlabelcell = '<td class="morphlabelcell">{ml}</td>'
	morphcell = '<td class="morphcell">{mo}</td>'
	regextemplate = '_{d}_{m}_{v}_{n}_{p}_{t}_'
	pcpltemplate = '_{d}_{m}_{v}_{n}_{t}_{g}_{c}_'

	# note that we cant do infinitives and participles yet

	if mood != 'part' and mood != 'inf':
		for n in numbers:
			for p in persons:
				if p == '1st' and n == 'dual':
					pass
				else:
					allcellsinrow = list()
					ml = '{n} {p}'.format(n=n, p=p)
					allcellsinrow.append(morphlabelcell.format(ml=ml))
					for t in tenses:
						mo = regextemplate.format(d=dialect, m=mood, v=voice, n=n, p=p, t=t)
						allcellsinrow.append(morphcell.format(mo=mo))
					thisrow = '\n\t\t'.join(allcellsinrow)
					allrows.append(morphrowtemplate.format(allcells=thisrow))
	elif mood == 'part':
		for n in numbers:
			for g in genders:
				for c in cases:
					allcellsinrow = list()
					ml = '{g} {n} {c}'.format(n=n, c=c, g=g)
					allcellsinrow.append(morphlabelcell.format(ml=ml))
					for t in tenses:
						mo = pcpltemplate.format(d=dialect, m=mood, v=voice, n=n, c=c, t=t, g=g)
						allcellsinrow.append(morphcell.format(mo=mo))
					thisrow = '\n\t\t'.join(allcellsinrow)
					allrows.append(morphrowtemplate.format(allcells=thisrow))
				if session['morphemptyrows'] == 'yes':
					allrows.append(blankrow)
	elif mood == 'inf':
		allcellsinrow = list()
		allcellsinrow.append(morphlabelcell.format(ml='infinitive'))
		for t in tenses:
			mo = regextemplate.format(d=dialect, m=mood, v=voice, n=None, p=None, t=t)
			allcellsinrow.append(morphcell.format(mo=mo))
		thisrow = '\n\t\t'.join(allcellsinrow)
		allrows.append(morphrowtemplate.format(allcells=thisrow))

	rows = '\n'.join(allrows)
	thetablehtml = tabletemplate.format(header=fullheader, rows=rows)

	return thetablehtml


def filloutverbtabletemplate(lookupdict: dict, wordcountdict: dict, template: str) -> str:
	"""

	regex swap the verbtabletemplate items

	:param lookupdict:
	:param template:
	:return:
	"""

	formtemplate = '<verbform searchterm="{sf}">{f}</verbform>'
	formandcountertemplate = '{f} (<span class="counter">{c}</span>)'

	seeking = r'<td class="morphcell">(.*?)</td>'
	cells = re.findall(seeking, template)

	# print('lookupdict', lookupdict)
	# print('template', template)

	for c in cells:
		# ['_attic_subj_pass_pl_2nd_pres_', '_attic_subj_pass_pl_2nd_imperf_', ...]
		# 2nd sg attic mid indic of τίκτω yields: τέξηι / τέξει / τέξῃ / τεκῇ
		try:
			formlist = lookupdict[c]
		except KeyError:
			formlist = None

		if formlist:
			strippedforms = {f: re.sub(r"'$", r'', f) for f in formlist}
			substitutetuplelist = [(re.sub(r"'$", r'', f), formtemplate.format(sf=strippedforms[f], f=f)) for f in formlist]
			counted = list()
			for s in substitutetuplelist:
				try:
					counted.append(formandcountertemplate.format(f=s[1], c=wordcountdict[s[0]]))
				except KeyError:
					counted.append(s[1])
			substitute = ' / '.join(counted)
		else:
			substitute = '---'

		try:
			substitute = '{s} (<span class="counter">{c}</span>)'.format(s=substitute, c=wordcountdict[lookupdict[c]])
		except KeyError:
			pass
		except TypeError:
			# needs fixing...
			pass

		template = re.sub(c, substitute, template)

	if session['morphemptyrows'] == 'no':
		template = purgeemptyrows(template)

	return template


def purgeemptyrows(templatetoclean: str) -> str:
	"""

	kill off '---' if it appears over and over again in a row

	:param templatetoclean:
	:return:
	"""

	badpattern = '<tr class="morphrow">\n\t\t<td class="morphlabelcell">.*?</td>{rows}\n\t</tr>'
	rowshape = '\n\t\t<td class="morphcell">---</td>'

	for i in range(1, 8):
		rows = ''.join([rowshape for _ in range(i)])
		search = badpattern.format(rows=rows)
		templatetoclean = re.sub(search, '', templatetoclean)

	return templatetoclean

# t = greekverbtabletemplate('subj', 'pass')
# print(t)

