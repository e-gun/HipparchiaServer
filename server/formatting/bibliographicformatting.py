# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session


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


def formatname(workobject, authorobject):
	"""

	shift name depending on type of hit

	neede by
		formattedcitationincontext()
		nocontexthtmlifysearchfinds()

	:param workobject:
	:param authorobject:
	:return:
	"""

	if workobject.isliterary():
		name = authorobject.shortname
	else:
		name = '[<span class="date">{d}</span>] {n}'.format(n=authorobject.idxname, d=workobject.bcedate())

	return name


def getpublicationinfo(workobject, cursor):
	"""
	what's in a name?
	:param workobject:
	:return: html for the bibliography
	"""

	uid = workobject.universalid
	query = 'SELECT publication_info FROM works WHERE universalid = %s'
	data = (uid,)
	cursor.execute(query, data)
	pi = cursor.fetchone()
	pi = pi[0]

	publicationhtml = formatpublicationinfo(pi)

	return publicationhtml


def formatpublicationinfo(pubinfo):
	"""
	in:
		<volumename>FHG </volumename>4 <press>Didot </press><city>Paris </city><year>1841–1870</year><pages>371 </pages><pagesintocitations>Frr. 1–2</pagesintocitations><editor>Müller, K. </editor>
	out:
		<span class="pubvolumename">FHG <br /></span><span class="pubpress">Didot , </span><span class="pubcity">Paris , </span><span class="pubyear">1841–1870. </span><span class="pubeditor"> (Müller, K. )</span>

	:param pubinfo:
	:return:
	"""

	maxlinelen = 120

	tags = [
		{'volumename': ['', '. ']},
		{'press': ['', ', ']},
		{'city': ['', ', ']},
		{'year': ['', '. ']},
		{'series': ['', '']},
		{'editor': [' (', ')']},
		# {'pages':[' (',')']}
	]

	publicationhtml = ''

	for t in tags:
		tag = next(iter(t.keys()))
		val = next(iter(t.values()))
		seek = re.compile('<' + tag + '>(.*?)</' + tag + '>')
		if re.search(seek, pubinfo):
			found = re.search(seek, pubinfo)
			data = re.sub(r'\s+$','',found.group(1))
			foundinfo = avoidlonglines(data, maxlinelen, '<br />', [])
			publicationhtml += '<span class="pub{t}">{va}{fi}{vb}</span>'.format(t=tag, va=val[0], fi=foundinfo, vb=val[1])

	return publicationhtml


def avoidlonglines(string, maxlen, splitval, stringlist=[]):
	"""

	Authors like Livy can swallow the browser window by sending 351 characters worth of editors to one of the lines

	break up a long line into multiple lines by splitting every N characters

	splitval will be something like '<br />' or '\n'

	:param string:
	:param maxlen:
	:return:
	"""

	breakcomeswithinamarkupseries = re.compile(r'^\s[^\s]{1,}>')

	if len(string) < maxlen:
		stringlist.append(string)
		newstringhtml = splitval.join(stringlist)
	else:
		searchzone = string[0:maxlen]
		stop = False
		stopval = len(string)

		for c in range(maxlen-1,-1,-1):
			if searchzone[c] == ' ' and stop == False and re.search(breakcomeswithinamarkupseries, string[c:]) is None:
				stop = True
				stringlist.append(string[0:c])
				stopval = c
		newstringhtml = avoidlonglines(string[stopval+1:], maxlen, splitval, stringlist)

	return newstringhtml


def formatauthorandworkinfo(authorname, workobject):
	"""
	dbdata into html
	send me: authorname + universalid, title, workgenre, wordcount
	:param workinfo:
	:return:
	"""

	if workobject.wordcount:
		c = '[' + format(workobject.wordcount, ',d') + ' wds]'
	else:
		c = ''

	authorandworkinfo = '{a}, <span class="italic">{t}</span> {c}<br />'.format(a=authorname, t=workobject.title, c=c)

	return authorandworkinfo