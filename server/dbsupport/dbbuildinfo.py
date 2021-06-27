# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

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
