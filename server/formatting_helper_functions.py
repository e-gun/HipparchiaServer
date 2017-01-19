# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import re
import configparser
from flask import session
from server import hipparchia

config = configparser.ConfigParser()
config.read('config.ini')

def removegravity(accentedword):
	"""
	turn all graves into accutes so you can match the dictionary form
	:param accentedword:
	:return:
	"""
	# this failed to work when i typed the greekkeys versions: look out for identical looks with diff unicode vals...
	# meanwhile eta did not work until the unicode codes were forced...
	accenttuples = (
		(r'ὰ', r'ά'),
		(r'ὲ', r'έ'),
		(r'ὶ', r'ί'),
		(r'ὸ',r'ό'),
		(r'ὺ', r'ύ'),
		(r'ὴ', r'ή'),
		(r'ὼ', r'ώ'),
		(r'ἃ', r'ἅ'),
		(r'ἓ', r'ἕ'),
		(r'ἳ', r'ἵ'),
		(r'ὃ', r'ὅ'),
		(r'ὓ', r'ὕ'),
		(r'ἣ', r'ἥ'),
		(r'ὣ', r'ὥ'),
		(r'ἂ', r'ἄ'),
		(r'ἒ', r'ἔ'),
		(r'ἲ', r'ἴ'),
		(r'ὂ', r'ὄ'),
		(r'ὒ', r'ὔ'),
		(r'ἢ', r'ἤ'),
		(r'ὢ', r'ὤ'),
		(r'ᾃ', r'ᾅ'),
		(r'ᾓ', r'ᾕ'),
		(r'ᾣ', r'ᾥ'),
		(r'ᾂ', r'ᾄ'),
		(r'ᾒ', r'ᾔ'),
		(r'ᾢ', r'ᾤ'),
	)

	for i in range(0, len(accenttuples)):
		accentedword = re.sub(accenttuples[i][0], accenttuples[i][1], accentedword)

	return accentedword


def stripaccents(texttostrip):
	"""
	turn ᾶ into α, etc

	:return:
	"""
	substitutes = (
		('v', 'u'),
		('U', 'V'),
		('(Á|Ä)', 'A'),
		('(á|ä)', 'a'),
		('(É|Ë)', 'E'),
		('(é|ë)', 'e'),
		('(Í|Ï)', 'I'),
		('(í|ï)', 'i'),
		('(Ó|Ö)', 'O'),
		('(ó|ö)', 'o'),
		('(ῤ|ῥ|Ῥ)', 'ρ'),
		# some sort of problem with acute alpha which seems to be unkillable
		# (u'u\1f71',u'\u03b1'),
		('(ἀ|ἁ|ἂ|ἃ|ἄ|ἅ|ἆ|ἇ|ᾀ|ᾁ|ᾂ|ᾃ|ᾄ|ᾅ|ᾆ|ᾇ|ᾲ|ᾳ|ᾴ|ᾶ|ᾷ|ᾰ|ᾱ|ὰ|ά)', 'α'),
		('(ἐ|ἑ|ἒ|ἓ|ἔ|ἕ|ὲ|έ)', 'ε'),
		('(ἰ|ἱ|ἲ|ἳ|ἴ|ἵ|ἶ|ἷ|ὶ|ί|ῐ|ῑ|ῒ|ΐ|ῖ|ῗ|ΐ)', 'ι'),
		('(ὀ|ὁ|ὂ|ὃ|ὄ|ὅ|ό|ὸ)', 'ο'),
		('(ὐ|ὑ|ὒ|ὓ|ὔ|ὕ|ὖ|ὗ|ϋ|ῠ|ῡ|ῢ|ΰ|ῦ|ῧ|ύ|ὺ)', 'υ'),
		('(ὠ|ὡ|ὢ|ὣ|ὤ|ὥ|ὦ|ὧ|ᾠ|ᾡ|ᾢ|ᾣ|ᾤ|ᾥ|ᾦ|ᾧ|ῲ|ῳ|ῴ|ῶ|ῷ|ώ|ὼ)', 'ω'),
		# similar problems with acute eta
		# (u'\u1f75','η'),
		('(ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|ή|ἠ|ἡ|ἦ|ἧ)', 'η'),
		('(ᾨ|ᾩ|ᾪ|ᾫ|ᾬ|ᾭ|ᾮ|ᾯ|Ὠ|Ὡ|Ὢ|Ὣ|Ὤ|Ὥ|Ὦ|Ὧ|Ω)', 'ω'),
		('(Ὀ|Ὁ|Ὂ|Ὃ|Ὄ|Ὅ|Ο)', 'ο'),
		('(ᾈ|ᾉ|ᾊ|ᾋ|ᾌ|ᾍ|ᾎ|ᾏ|Ἀ|Ἁ|Ἂ|Ἃ|Ἄ|Ἅ|Ἆ|Ἇ|Α)', 'α'),
		('(Ἐ|Ἑ|Ἒ|Ἓ|Ἔ|Ἕ|Ε)', 'ε'),
		('(Ἰ|Ἱ|Ἲ|Ἳ|Ἴ|Ἵ|Ἶ|Ἷ|Ι)', 'ι'),
		('(Ὑ|Ὓ|Ὕ|Ὗ|Υ)', 'υ'),
		('(ᾘ|ᾙ|ᾚ|ᾛ|ᾜ|ᾝ|ᾞ|ᾟ|Ἠ|Ἡ|Ἢ|Ἣ|Ἤ|Ἥ|Ἦ|Ἧ|Η)', 'η'),
		('Β', 'β'),
		('Ψ', 'ψ'),
		('Δ', 'δ'),
		('Φ', 'φ'),
		('Γ', 'γ'),
		('Ξ', 'ξ'),
		('Κ', 'κ'),
		('Λ', 'λ'),
		('Μ', 'μ'),
		('Ν', 'ν'),
		('Π', 'π'),
		('Ϙ', 'ϙ'),
		('Ρ', 'ρ'),
		('Ϲ', 'ϲ'),
		('Τ', 'τ'),
		('Θ', 'θ'),
		('Ζ', 'ζ')
	)
	
	for swap in range(0, len(substitutes)):
		texttostrip = re.sub(substitutes[swap][0], substitutes[swap][1], texttostrip)
	
	return texttostrip


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

	tags = [
		{'volumename': ['', '<br />']},
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
		if re.search(seek, pubinfo) is not None:
			found = re.search(seek, pubinfo)
			foundinfo = avoidlonglines(found.group(1), 120, '<br />', [])
			publicationhtml += '<span class="pub' + tag + '">' + val[0] + foundinfo + val[1] + '</span>'
	
	return publicationhtml


def bcedating():
	"""
	return the English equivalents for session['earliestdate'] and session['latestdate']
	:return:
	"""
	
	dmax = session['latestdate']
	dmin = session['earliestdate']
	if dmax[0] == '-':
		dmax = dmax[1:] + ' B.C.E.'
	else:
		dmax = dmax + ' C.E.'
	
	if dmin[0] == '-':
		dmin = dmin[1:] + ' B.C.E.'
	else:
		dmin = dmin + 'C.E.'
		
	return dmin, dmax


def htmlifysearchfinds(listoffinds):
	"""
	it is too painful to let JS turn this information into HTML
	the Flask template used to do this work, now this does it

	send me a list of FormattedSearchResult objects

	:param listoffinds:
	:return:
	"""

	resultsashtml = []
	listofurls = []

	for find in listoffinds:
		htmlforthefind = ''
		lines = find.formattedlines

		listofurls.append(find.clickurl)

		htmlforthefind += '<locus>\n'
		htmlforthefind += '\t<span class="findnumber">[' + str(find.hitnumber) + ']</span>&nbsp;&nbsp;'
		htmlforthefind += '<span class="foundauthor">' + find.author + '</span>,&nbsp;'
		htmlforthefind += '<span class="foundwork">' + find.work + '</span>:\n'
		htmlforthefind += '\t<browser id="' + find.clickurl + '">'
		htmlforthefind += '<span class="foundlocus">' + find.citationstring + '</span><br />'
		htmlforthefind += '</browser>\n</locus>\n'

		for ln in lines:
			if hipparchia.config['DEBUGMODE'] == 'no':
				htmlforthefind += '<span class="locus">' + ln.locus() + '</span>&nbsp;\n'
			else:
				htmlforthefind += '<code>'+ln.universalid+'</code>&nbsp;<span class="locus">' + ln.locus() + '</span>&nbsp;\n'
			htmlforthefind += '<span class="foundtext">' + ln.accented + '</span><br />\n'

		resultsashtml.append(htmlforthefind)

	htmlandjs = {}
	htmlandjs['hits'] = resultsashtml

	if len(listoffinds) > 0:
		htmlandjs['hitsjs'] = injectbrowserjavascript(listofurls)
	else:
		htmlandjs['hitsjs'] = ''

	return htmlandjs


def injectbrowserjavascript(listofurls):
	"""
	the clickable urls don't work without inserting new js into the page to catch the clicks
	need to match the what we used to get via the flask template
	:return:
	"""
	
	jsoutput = ''
	
	for url in listofurls:
		jsoutput += '\n\tdocument.getElementById("'+url+'").onclick = openbrowserfromclick;'
	
	return jsoutput


def insertcrossreferencerow(lineobject):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""
	linehtml = ''

	if re.search(r'documentnumber',lineobject.annotations) is None:
		columna = ''
		columnb = '<span class="crossreference">' + lineobject.annotations + '</span>'

		linehtml = '<tr class="browser"><td class="crossreference">' + columnb + '</td>'
		linehtml += '<td class="crossreference">' + columna + '</td></tr>\n'
	
	return linehtml


def insertdatarow(label, css, founddate):
	"""
	inscriptions and papyri have relevant bibliographic information that needs to be displayed
	:param lineobject:
	:return:
	"""
	
	linehtml = ''
		
	columna = ''
	columnb = '<span class="textdate">'+label+':&nbsp;' + founddate + '</span>'
	
	linehtml = '<tr class="browser"><td class="'+css+'">' + columnb + '</td>'
	linehtml += '<td class="crossreference">' + columna + '</td></tr>\n'
	
	return linehtml


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

