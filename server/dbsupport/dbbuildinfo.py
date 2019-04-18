# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import psycopg2

from server.hipparchiaobjects.connectionobject import ConnectionObject


def buildoptionchecking() -> dict:
	"""

	check what build options were set

	hipparchiaDB=# SELECT corpusname, buildoptions FROM builderversion;
	 corpusname |                                              buildoptions
	------------+---------------------------------------------------------------------------------------------------------
	 lt         | hideknownblemishes: y, htmlifydatabase: n, simplifybrackets: y, simplifyquotes: y, smartsinglequotes: y

	:return:
	"""
	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	q = 'SELECT corpusname, buildoptions FROM builderversion'
	try:
		dbcursor.execute(q)
		results = dbcursor.fetchall()
	except:
		# psycopg2.errors.UndefinedColumn; but Windows will tell you that there is no 'errors' module...
		results = None
	dbconnection.connectioncleanup()

	optiondict = dict()
	if results:
		for r in results:
			optiondict[r[0]] = r[1]
		for o in optiondict:
			optiondict[o] = optiondict[o].split(', ')
			# turn {'simplifyquotes: y', 'simplifybrackets: y', 'hideknownblemishes: y', 'smartsinglequotes: y', 'htmlifydatabase: n'}
			# into {'hideknownblemishes': 'y', 'htmlifydatabase': 'n', 'simplifybrackets': 'y', 'simplifyquotes': 'y', 'smartsinglequotes': 'y'}
			optiondict[o] = {a.split(': ')[0]: a.split(': ')[1] for a in optiondict[o]}
	return optiondict


def versionchecking(activedbs: list, expectedsqltemplateversion: str) -> str:
	"""

	send a warning if the corpora were built from a different template than the one active on the server

	:param activedbs:
	:param expectedsqltemplateversion:
	:return:
	"""

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	activedbs += ['lx', 'lm']
	labeldecoder = {
		'lt': 'The corpus of Latin authors',
		'gr': 'The corpus of Greek authors',
		'in': 'The corpus of classical inscriptions',
		'dp': 'The corpus of papyri',
		'ch': 'The corpus of Christian era inscriptions',
		'lx': 'The lexical database',
		'lm': 'The parsing database'
	}

	q = 'SELECT corpusname, templateversion, corpusbuilddate FROM builderversion'
	cursor.execute(q)
	results = cursor.fetchall()

	corpora = {r[0]: (r[1], r[2]) for r in results}

	for db in activedbs:
		if db in corpora:
			if int(corpora[db][0]) != expectedsqltemplateversion:
				t = """
				WARNING: VERSION MISMATCH
				{d} has a builder template version of {v}
				(and was compiled {t})
				But the server expects the template version to be {e}.
				EXPECT THE WORST IF YOU TRY TO EXECUTE ANY SEARCHES
				"""
				print(t.format(d=labeldecoder[db], v=corpora[db][0], t=corpora[db][1], e=expectedsqltemplateversion))

	buildinfo = ['\t{corpus}: {date} [{prolix}]'.format(corpus=c, date=corpora[c][1], prolix=labeldecoder[c])
				for c in sorted(corpora.keys())]
	buildinfo = '\n'.join(buildinfo)

	dbconnection.connectioncleanup()

	return buildinfo
