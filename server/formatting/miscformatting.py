# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.formatting.searchformatting import formatpublicationinfo


def bcedating(s=session):
	"""
	return the English equivalents for session['earliestdate'] and session['latestdate']
	:return:
	"""

	dmax = s['latestdate']
	dmin = s['earliestdate']
	if dmax[0] == '-':
		dmax = dmax[1:] + ' B.C.E.'
	else:
		dmax = dmax + ' C.E.'

	if dmin[0] == '-':
		dmin = dmin[1:] + ' B.C.E.'
	else:
		dmin = dmin + 'C.E.'

	return dmin, dmax


def insertcrossreferencerow(lineobject):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""
	linehtml = ''

	if re.search(r'documentnumber',lineobject.annotations) is None:
		columna = ''
		columnb = '<span class="crossreference">{ln}</span>'.format(ln=lineobject.annotations)

		linehtml = '<tr class="browser"><td class="crossreference">{c}</td>'.format(c=columnb)
		linehtml += '<td class="crossreference">{c}</td></tr>\n'.format(c=columna)

	return linehtml


def insertdatarow(label, css, founddate):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""

	columna = ''
	columnb = '<span class="textdate">{l}:&nbsp;{fd}</span>'.format(l=label, fd=founddate)

	linehtml = '<tr class="browser"><td class="{css}">{cb}</td>'.format(css=css, cb=columnb)
	linehtml += '<td class="crossreference">{ca}</td></tr>\n'.format(ca=columna)

	return linehtml


def formatauthinfo(authorobject):
	"""

	called by getauthinfo()

	ao data into html
	:param authorobject:
	:return:
	"""

	template = """
	<span class="emph">{n}</span>&nbsp;
	[id: {id}]<br />&nbsp;
	{gn}
	{fl}
	"""

	n = '<span class="emph">{n}</span>'.format(n=authorobject.shortname)
	if authorobject.genres and authorobject.genres != '':
		gn = 'classified among: {g}; '.format(g=authorobject.genres)
	else:
		gn = '<!-- no author genre available -->'

	if authorobject.converted_date:
		if float(authorobject.converted_date) == 2000:
			fl = '"Varia" are not assigned to a date'
		elif float(authorobject.converted_date) == 2500:
			fl = '"Incerta" are not assigned to a date'
		elif float(authorobject.converted_date) > 0:
			fl = 'assigned to approx date: {fl} C.E.'.format(fl=str(authorobject.converted_date))
			fl += ' (derived from "{rd}")'.format(rd=authorobject.recorded_date)
		elif float(authorobject.converted_date) < 0:
			fl = 'assigned to approx date: {fl} B.C.E.'.format(fl=str(authorobject.converted_date)[1:])
			fl += ' (derived from "{rd}")'.format(rd=authorobject.recorded_date)
	else:
		fl = '<!-- no floruit available -->'

	authinfo = template.format(n=n, id=authorobject.universalid[2:], gn=gn, fl=fl)

	return authinfo


def woformatworkinfo(workobject):
	"""

	called by getauthinfo()

	dbdata into html
	send me: universalid, title, workgenre, wordcount

	:param workinfo:
	:return:
	"""

	template = """
	({num})&nbsp;
	<span class="title">{t}</span>
	{g}
	{c}
	{d}
	{p}
	<br />
	"""

	if workobject.workgenre:
		g = '[{g}]&nbsp;'.format(g=workobject.workgenre)
	else:
		g = '<!-- no genre info available -->'

	if workobject.wordcount:
		c = '[' + format(workobject.wordcount, ',d') + ' wds]'
	else:
		c = '<!-- no wordcount available -->'

	if workobject.isnotliterary():
		d = '(<span class="date">{d}</span>)'.format(d=workobject.bcedate())
	else:
		d = ''

	p = formatpublicationinfo(workobject.publication_info)
	if len(p) == 0:
		p = '<!-- no publication info available -->'
	else:
		p = '<br />\n' + p

	workinfo = template.format(num=workobject.universalid[-3:], t=workobject.title, g=g, c=c, d=d, p=p)

	return workinfo