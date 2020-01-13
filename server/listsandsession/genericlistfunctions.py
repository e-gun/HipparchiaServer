# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re

from server.formatting.wordformatting import buildhipparchiatranstable, stripaccents


def dictitemstartswith(originaldict: dict, element: str, muststartwith: str) -> dict:
	"""

	trim a dict via a criterion: muststartwith must begin the item to survive the check

	:param originaldict:
	:param element:
	:param muststartwith:
	:return:
	"""

	newdict = {x: originaldict[x] for x in originaldict
	           if getattr(originaldict[x], element)[0:2] == muststartwith}

	return newdict


def findspecificdate(authorandworklist, authorobjectdict, workobjectdict, specificdate) -> list:
		"""

		tell me which items on the authorandworklist have unknown dates

			incerta = 2500
			varia = 2000
			[failedtoparse = 9999]

		this profiles as fairly slow when called on a large search list (.5s):
		it might be better to build a list of these up front
		when loading HipparchiaServer since this is both static and repetitive

		:param authorandworklist:
		:param authorobjectdict:
		:param worksdict:
		:return:
		"""
		datematches = list()

		for aw in authorandworklist:
			w = workobjectdict[aw]
			try:
				# does the work have a date? if not, we will throw an exception
				cd = int(w.converted_date)
				if cd == specificdate:
					datematches.append(aw)
			except TypeError:
				# no work date? then we will look inside the author for the date
				aid = aw[0:6]
				try:
					cd = int(authorobjectdict[aid].converted_date)
					if cd == specificdate:
						datematches.append(aw)
				except TypeError:
					# the author can't tell you his date; i guess it is incerta by definition
					datematches.append(aw)

		return datematches


def tidyuplist(untidylist: list) -> list:
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
		tidylist = list()

	return tidylist


def dropdupes(checklist: list, matchlist: list) -> list:
	"""

	clean up a list
	drop anything that already has something else like it chosen

	:param checklist:
	:param matchlist:
	:return:
	"""

	c = set(checklist)
	m = set(matchlist)

	c = list(c-m)

	return c


def polytonicsort(unsortedwords: list) -> list:
	"""
	sort() looks at your numeric value, but α and ά and ᾶ need not have neighboring numerical values
	stripping diacriticals can help this, but then you get words that collide
	gotta jump through some extra hoops

		[a] build an unaccented copy of the word in front of the word
		[b] substitute sigmas for lunate sigmas (because lunate comes after omega...)
			θαλαττησ-snip-θαλάττηϲ
		[c] sort the augmented words (where ά and ᾶ only matter very late in the game)
		[d] remove the augment
		[e] return

	:param unsortedwords:
	:return:
	"""

	transtable = buildhipparchiatranstable()

	stripped = [re.sub(r'ϲ', r'σ', stripaccents(word, transtable)) + '-snip-' + word for word in unsortedwords if word]

	stripped = sorted(stripped)

	snipper = re.compile(r'(.*?)(-snip-)(.*?)')

	sortedversion = [re.sub(snipper, r'\3', word) for word in stripped]

	return sortedversion


def foundindict(searchdict: dict, element: str, mustbein: str, exactmatch=True) -> list:
	"""

	search for an element in a dict
	return a list of universalids

	searchdict:
		{ ... 'gr2625': <server.hipparchiaclasses.dbAuthor object at 0x1096e9cf8>, 'gr1890': <server.hipparchiaclasses.dbAuthor object at 0x1096e9d68>,
		'gr0045': <server.hipparchiaclasses.dbAuthor object at 0x1096e9dd8>, 'gr2194': <server.hipparchiaclasses.dbAuthor object at 0x1096e9e48>}
	element:
		genres
	mustbein:
		Astrologici

	:param searchdict:
	:param element:
	:param mustbein:
	:param exactmatch:
	:return:
	"""

	if exactmatch:
		finds = [searchdict[x].universalid for x in searchdict
		         if getattr(searchdict[x], element) and getattr(searchdict[x], element) == mustbein]
	else:
		finds = [searchdict[x].universalid for x in searchdict
		         if getattr(searchdict[x], element) and re.search(mustbein, getattr(searchdict[x], element))]

	return finds
