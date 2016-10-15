# -*- coding: utf-8 -*-

from flask import session
from operator import itemgetter
import re



def tidyuplist(untidylist):
	"""
	sort and remove duplicates
	:param untidylist:
	:return:
	"""
	# not supposed to get 0 lists here, but...
	if len(untidylist) > 0:
		untidylist[:] = [x for x in untidylist if x]
		tidylist = list(set(untidylist))
		tidylist.sort()
	else:
		tidylist = []

	return tidylist


def dropdupes(checklist, matchlist):
	"""
	clean up a list
	drop anything that already has something else like it chosen
	:param uidlist:
	:return:
	"""
	
	for c in checklist:
		for m in matchlist:
			if c in m:
				checklist.remove(c)
	
	return checklist


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


def polytonicsort(unsortedwords):
	# sort() looks at your numeric value, but α and ά and ᾶ need not have neighboring numerical values
	# stripping diacriticals can help this, but then you get words that collide
	# gotta jump through some extra hoops
	
	stripped = []
	for word in unsortedwords:
		if len(word) > 0:
			strippedword = stripaccents(word)
			# one modification to stripaccents(): σ for ϲ in order to get the right values
			strippedword = re.sub(r'ϲ', r'σ', strippedword)
			stripped.append(strippedword + '-snip-' + word)
	stripped.sort()
	sorted = []
	for word in stripped:
		cleaned = re.sub(r'(.*?)(-snip-)(.*?)', r'\3', word)
		sorted.append(cleaned)
	
	return sorted


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
		('(ᾐ|ᾑ|ᾒ|ᾓ|ᾔ|ᾕ|ᾖ|ᾗ|ῂ|ῃ|ῄ|ῆ|ῇ|ἤ|ἢ|ἥ|ἣ|ὴ|\u1f75|ἠ|ἡ|ἦ|ἧ)', 'η'),
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


def aosortauthorandworklists(authorandworklist, authorsdict):
	"""
	send me a list of workuniversalids and i will resort it via the session sortorder
	:param authorandworklist:
	:param authorsdict:
	:return:
	"""
	sortby = session['sortorder']
	templist = []
	newlist = []
	
	if sortby != 'universalid':
		for a in authorandworklist:
			auid = a[0:6]
			crit = getattr(authorsdict[auid], sortby)
			name = authorsdict[auid].shortname
			if sortby == 'floruit':
				try:
					crit = float(crit)
				except:
					crit = 9999
			
			templist.append([crit, a, name])
		
		# http://stackoverflow.com/questions/5212870/sorting-a-python-list-by-two-criteria#17109098
		# sorted(list, key=lambda x: (x[0], -x[1]))
		
		templist = sorted(templist, key=lambda x: (x[0], x[2]))
		for t in templist:
			newlist.append(t[1])
	else:
		newlist = authorandworklist
	
	return newlist


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
	# tag: lead-in, exit
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
			publicationhtml += '<span class="pub' + tag + '">' + val[0] + found.group(1) + val[1] + '</span>'
	
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


def prunedict(originaldict, element, mustbein):
	"""
	trim a dict via a criterion
	:param originaldict:
	:param criterion:
	:param mustbe:
	:return:
	"""
	newdict = {}
	
	for item in originaldict:
		if re.search(mustbein, getattr(originaldict[item], element)) is not None:
			newdict[item] = originaldict[item]

	return newdict


def foundindict(dict, element, mustbein):
	"""
	search for an element in a dict
	return a list of universalids
	:param dict:
	:param element:
	:param mustbein:
	:return:
	"""
	
	finds = []
	for item in dict:
		if getattr(dict[item], element) is not None:
			if re.search(mustbein, getattr(dict[item], element)) is not None:
				finds.append(dict[item].universalid)
	
	return finds

# slated for removal

def sortauthorandworklists(authorandworklist, cursor):
	"""
	send me a list of workuniversalids and i will resort it via the session sortorder
	:param authorandworklist: (au, wk)
	:param cursor:
	:return:
	"""
	so = session['sortorder']
	templist = []
	newlist = []
	
	# because there is no need to query plutarch 100 times
	previous = ['', '']
	
	if so != 'universalid':
		for a in authorandworklist:
			if a[0:6] != previous[0]:
				query = 'SELECT ' + so + ' FROM authors WHERE universalid = %s'
				data = (a[0:6],)
				cursor.execute(query, data)
				found = cursor.fetchone()
				if so == 'floruit':
					try:
						f = float(found[0])
					except:
						f = 9999
				else:
					f = found[0]
			else:
				f = previous[1]
			
			templist.append([f, a])
			previous = [a[0:6], f]
		
		templist = sorted(templist, key=itemgetter(0))
		for t in templist:
			newlist.append(t[1])
	else:
		newlist = authorandworklist
	
	return newlist

