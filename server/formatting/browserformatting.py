# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque

from flask import session

from server.formatting.wordformatting import forcelunates
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.listsandsession.sessionfunctions import findactivebrackethighlighting


def insertparserids(lineobject: dbWorkLine, continuationdict: dict) -> str:
	"""
	set up the clickable thing for the browser by bracketing every word with something the JS can respond to:
		<observed id="ἐπειδὲ">ἐπειδὲ</observed>
		<observed id="δέ">δέ</observed>
		...
	this is tricky because there is html in here and you don't want to tag it
	also you need to handle hyphenated line-ends

	there is a lot of dancing around required to both mark up the brackets and to make
	the clickable observeds

	a lot of hoops to jump through for a humble problem: wrong whitespace position

	the main goal is to avoid 'ab[ <span>cd' when what you want is 'ab[<span>cd'
	the defect is that anything that is chopped up by bracketing markup will be
	'unobservable' and so unclickable: 'newline[-1] +=' removes you from consideration
	but if you turn off the highlighting the clicks come back

	this rewriting of the rewritten and marking up of the marked up explains the ugliness below: kludgy, but...

	Aeschylus, Fragmenta is a great place to give the parser a workout

	anything that works with Aeschylus should then be checked against a fragmentary INS and a fragmentary DDP

	in the course of debugging it is possible to produce versions that work with only some of those three types of passage

	:param lineobject:
	:param continuationdict:
	:return:
	"""

	theline = lineobject.markedup
	newline = [str()]
	whitespace = ' '

	brackettypes = findactivebrackethighlighting()
	if brackettypes:
		continuationdict = {e: continuationdict[e] for e in brackettypes}
		theline = lineobject.markeditorialinsersions(continuationdict)

	theline = re.sub(r'(<.*?>)', r'*snip*\1*snip*', theline)
	hyphenated = lineobject.hyphenated
	segments = deque([s for s in theline.split('*snip*') if s])

	# OK, you have your segments, but the following will have a spacing problem ('</observed><span...>' vs '</observed> <span...>':
	#	['ὁ μὲν ', '<span class="expanded">', 'Μυρμιδόϲιν·', '</span>']
	# you can fix the formatting issue by adding an item that is just a blank space: whitespace
	#	['ὁ μὲν ', whitespace, '<span class="expanded">', 'Μυρμιδόϲιν·', '</span>']
	# another place where you need space:
	#	['</span>', ' Κωπάιδων']

	properlyspacedsegments = list()
	while len(segments) > 1:
		if len(segments[0]) > 1 and re.search(r'\s$', segments[0]) and re.search(r'^<', segments[1]):
			# ['ὁ μὲν ', '<span class="expanded">', 'Μυρμιδόϲιν·', '</span>']
			properlyspacedsegments.append(segments.popleft())
			properlyspacedsegments.append(whitespace)
		elif re.search(r'>$', segments[0]) and re.search(r'^\s', segments[1]):
			# ['</span>', ' Κωπάιδων']
			properlyspacedsegments.append(segments.popleft())
			properlyspacedsegments.append(whitespace)
		else:
			properlyspacedsegments.append(segments.popleft())
	properlyspacedsegments.append(segments.popleft())

	for segment in properlyspacedsegments:
		# here come the spacing and joining games
		if segment[0] == '<':
			# this is markup don't 'observe' it
			newline[-1] += segment
		else:
			words = segment.split(whitespace)
			words = ['{wd} '.format(wd=w) for w in words if len(w) > 0]
			words = deque(words)

			# first and last words matter because only they can crash into markup
			# and, accordingly, only they can produce the clash between markup and brackets

			try:
				lastword = words.pop()
			except IndexError:
				lastword = None

			try:
				lastword = re.sub(r'\s$', str(), lastword)
			except TypeError:
				pass

			try:
				firstword = words.popleft()
			except IndexError:
				firstword = None

			if not firstword:
				firstword = lastword
				lastword = None

			if not firstword:
				newline[-1] += whitespace

			if firstword:
				if bracketcheck(firstword):
					newline[-1] += '{w}'.format(w=firstword)
				else:
					newline.append(addobservedtags(firstword, lastword, hyphenated))

			while words:
				word = words.popleft()
				newline.append(addobservedtags(word, lastword, hyphenated))

			if lastword:
				if bracketcheck(lastword):
					newline[-1] += '{w}'.format(w=lastword)
				else:
					newline.append(addobservedtags(lastword, lastword, hyphenated))

	newline = str().join(newline)
	cleaner = re.compile(r'<observed id=""></observed>')
	newline = re.sub(cleaner, str(), newline)

	return newline


def bracketcheck(word: str) -> bool:
	"""

	true if there are brackets in the word

	:param word:
	:return:
	"""

	brackets = re.compile(r'[\[({⟨\])}⟩]')

	if re.search(brackets, word):
		return True
	else:
		return False


def addobservedtags(word: str, lastword: str, hyphenated: str) -> str:
	"""

	take a word and sandwich it with a tag

	'<observed id="imperator">imperator</observed>'

	:param word:
	:param lastword:
	:param hyphenated:
	:return:
	"""

	nsp = re.compile(r'&nbsp;$')
	untaggedclosings = re.compile(r'[\])⟩},;.?!:·’′“”»†]$')
	neveropens = re.compile(r'^[‵„“«†]')

	if re.search(r'\s$', word):
		word = re.sub(r'\s$', str(), word)
		sp = ' '
	else:
		sp = str()

	try:
		word[-1]
	except IndexError:
		return str()

	if word[-1] == '-' and word == lastword:
		observed = '<observed id="{h}">{w}</observed>{sp}'.format(h=hyphenated, w=word, sp=sp)
	elif re.search(neveropens, word) and not re.search(untaggedclosings, word):
		observed = '{wa}<observed id="{wb}">{wb}</observed>{sp}'.format(wa=word[0], wb=word[1:], sp=sp)
	elif re.search(neveropens, word) and re.search(untaggedclosings, word) and not re.search(nsp, word):
		wa = word[0]
		wb = word[1:-1]
		wc = word[-1]
		observed = '{wa}<observed id="{wb}">{wb}</observed>{wc}{sp}'.format(wa=wa, wb=wb, wc=wc, sp=sp)
	elif not re.search(neveropens, word) and re.search(untaggedclosings, word) and not re.search(nsp, word):
		wa = word[0:-1]
		wb = word[-1]
		observed = '<observed id="{wa}">{wa}</observed>{wb}{sp}'.format(wa=wa, wb=wb, sp=sp)
	elif re.search(neveropens, word):
		observed = '{wa}<observed id="{wb}">{wb}</observed>{sp}'.format(wa=word[0], wb=word[1:], sp=sp)
	elif re.search(r'^&nbsp;', word):
		wb = re.sub(r'&nbsp;', str(), word)
		# if wb='*', you have a problem...
		wa = re.sub(re.escape(wb), str(), word)
		observed = '{wa}<observed id="{wb}">{wb}</observed>{sp}'.format(wa=wa, wb=wb, sp=sp)
	else:
		observed = '<observed id="{w}">{w}</observed>{sp}'.format(w=word, sp=sp)

	return observed
