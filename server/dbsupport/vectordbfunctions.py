# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import pickle
from datetime import datetime

import psycopg2

from server import hipparchia
from server.dbsupport.dblinefunctions import bulklinegrabber
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.searching.proximitysearching import grableadingandlagging
from server.semanticvectors.vectorhelpers import determinesettings, readgitdata


def createvectorstable():
	"""

	zap and reconstitute the storedvectors table

	:return:
	"""

	print('resetting the stored vectors table')

	dbconnection = ConnectionObject(ctype='rw')
	dbcursor = dbconnection.cursor()

	query = """
	DROP TABLE IF EXISTS public.storedvectors;

	CREATE TABLE public.storedvectors
	(
		ts timestamp without time zone,
		versionstamp character varying(6) COLLATE pg_catalog."default",
		instance character varying (512) COLLATE pg_catalog."default",
		uidlist text[] COLLATE pg_catalog."default",
		vectortype character varying(10) COLLATE pg_catalog."default",
		calculatedvectorspace bytea
	)
	WITH (
		OIDS = FALSE
	)
	TABLESPACE pg_default;
	
	ALTER TABLE public.storedvectors
		OWNER to hippa_wr;
	
	GRANT SELECT ON TABLE public.storedvectors TO {reader};
	
	GRANT ALL ON TABLE public.storedvectors TO {writer};
	"""

	query = query.format(reader=hipparchia.config['DBUSER'], writer=hipparchia.config['DBWRITEUSER'])

	dbcursor.execute(query)

	dbconnection.connectioncleanup()

	return


def createstoredimagestable():
	"""

	zap and reconstitute the storedimages table

	:return:
	"""

	print('resetting the stored images table')

	dbconnection = ConnectionObject(ctype='rw')
	dbcursor = dbconnection.cursor()

	query = """
	DROP TABLE IF EXISTS public.storedvectorimages;
	
	CREATE TABLE public.storedvectorimages
	(
		imagename character varying(12),
		imagedata bytea
	)
	WITH (
		OIDS = FALSE
	)
	TABLESPACE pg_default;
	
	ALTER TABLE public.storedvectorimages
		OWNER to hippa_wr;
	
	GRANT SELECT ON TABLE public.storedvectorimages TO {reader};
	
	GRANT ALL ON TABLE public.storedvectorimages TO {writer};
	"""

	query = query.format(reader=hipparchia.config['DBUSER'], writer=hipparchia.config['DBWRITEUSER'])

	dbcursor.execute(query)

	dbconnection.connectioncleanup()

	return


def storevectorindatabase(searchobject, vectortype, vectorspace):
	"""

	you have just calculated a new vectorpace, store it so you do not need to recalculate it
	later

	:param vectorspace:
	:param uidlist:
	:param vectortype:
	:return:
	"""

	if searchobject.wholecorporasearched():
		uidlist = searchobject.wholecorporasearched()
	else:
		uidlist = sorted(searchobject.searchlist)

	dbconnection = ConnectionObject(ctype='rw')
	dbcursor = dbconnection.cursor()

	q = 'DELETE FROM public.storedvectors WHERE (uidlist = %s and vectortype = %s)'
	d = (uidlist, vectortype)
	dbcursor.execute(q, d)

	q = """
	INSERT INTO public.storedvectors 
		(ts, versionstamp, instance, uidlist, vectortype, calculatedvectorspace)
		VALUES (%s, %s, %s, %s, %s, %s)
	"""

	pickledvectors = pickle.dumps(vectorspace)
	settings = determinesettings()
	ts = datetime.now().strftime("%Y-%m-%d %H:%M")
	versionstamp = readgitdata()[:6]

	d = (ts, versionstamp, settings, uidlist, vectortype, pickledvectors)
	dbcursor.execute(q, d)

	# print('stored {u} in vector table (type={t})'.format(u=uidlist, t=vectortype))

	dbconnection.connectioncleanup()

	return


def checkforstoredvector(searchobject, vectortype, careabout='instance'):
	"""

	the stored vector might not reflect the current math rules

	return False if you are 'outdated'

	hipparchiaDB=# select ts,versionstamp,uidlist from storedvectors;
	        ts          | versionstamp |   uidlist
	---------------------+--------------+--------------
	2018-02-14 20:49:00 | 7e1c1b       | {lt0474w011}
	2018-02-14 20:50:00 | 7e1c1b       | {lt0474w057}
	(2 rows)

	:param uidlist:
	:return:
	"""

	if searchobject.wholecorporasearched():
		uidlist = searchobject.wholecorporasearched()
	else:
		uidlist = sorted(searchobject.searchlist)

	version = readgitdata()

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	q = """
	SELECT {crit}, calculatedvectorspace 
		FROM public.storedvectors 
		WHERE uidlist=%s AND vectortype=%s
	"""
	d = (uidlist, vectortype)

	try:
		cursor.execute(q.format(crit=careabout), d)
		result = cursor.fetchone()
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "public.storedvectors" does not exist
		createvectorstable()
		result = False

	if not result:
		return False

	if careabout == 'versionstamp':
		outdated = (version[:6] != result[0])
	elif careabout == 'instance':
		current = determinesettings()
		outdated = (current != result[0])
	else:
		outdated = True

	# print('checkforstoredvector()', uidlist, result[0], 'outdated=', outdated)

	if outdated:
		returnval = False
	else:
		returnval = pickle.loads(result[1])

	dbconnection.connectioncleanup()

	return returnval


def fetchverctorenvirons(hitdict, searchobject):
	"""

	grab the stuff around the term you were looking for and return that as the environs

	:param hitdict:
	:param searchobject:
	:return:
	"""

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	so = searchobject

	if so.lemma:
		supplement = so.lemma.dictionaryentry
	else:
		supplement = so.termone

	environs = list()
	if so.session['searchscope'] == 'W':
		for h in hitdict:
			leadandlag = grableadingandlagging(hitdict[h], searchobject, cursor)
			environs.append('{a} {b} {c}'.format(a=leadandlag['lead'], b=supplement, c=leadandlag['lag']))

	else:
		# there is a double-count issue if you get a word 2x in 2 lines and then grab the surrounding lines

		distance = int(so.proximity)
		# note that you can slowly iterate through it all or more quickly grab just what you need at one gulp...
		tables = dict()
		for h in hitdict:
			if hitdict[h].authorid not in tables:
				tables[hitdict[h].authorid] = list()
			if hitdict[h].index not in tables[hitdict[h].authorid]:
				tables[hitdict[h].authorid] += list(range(hitdict[h].index-distance, hitdict[h].index+distance))

		tables = {t: set(tables[t]) for t in tables}
		# print('tables', tables)

		# grab all of the lines from all of the tables
		linesdict = dict()
		for t in tables:
			linesdict[t] = bulklinegrabber(t, so.usecolumn, 'index', tables[t], cursor)

		# generate the environs
		dropdupes = set()

		for h in hitdict:
			need = ['{t}@{i}'.format(t=hitdict[h].authorid, i=i) for i in range(hitdict[h].index-distance, hitdict[h].index+distance)]
			for n in need:
				if n not in dropdupes:
					dropdupes.add(n)
					try:
						environs.append(linesdict[hitdict[h].authorid][n])
					except KeyError:
						pass

	dbconnection.connectioncleanup()

	return environs
