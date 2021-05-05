# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import pickle
from datetime import datetime

import psycopg2

from server import hipparchia
from server.dbsupport.dblinefunctions import bulklinegrabber
from server.formatting.miscformatting import consolewarning
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.searchlistmanagement import calculatewholeauthorsearches, flagexclusions
from server.searching.searchhelperfunctions import grableadingandlagging
from server.startup import authordict


def createvectorstable():
	"""

	zap and reconstitute the storedvectors table

	:return:
	"""

	consolewarning('resetting the stored vectors table', color='green')

	dbconnection = ConnectionObject(ctype='rw')
	dbcursor = dbconnection.cursor()

	query = """
	DROP TABLE IF EXISTS public.storedvectors;

	CREATE TABLE public.storedvectors
	(
		ts timestamp without time zone,
		thumbprint bytea,
		uidlist text[] COLLATE pg_catalog."default",
		vectortype character varying(24) COLLATE pg_catalog."default",
		baggingmethod character varying(24) COLLATE pg_catalog."default",
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

	consolewarning('resetting the stored images table', color='green')

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


def storevectorindatabase(so: SearchObject, vectorspace):
	"""

	you have just calculated a new vectorpace, store it so you do not need to recalculate it
	later

	vectorspace will be something like '<class 'gensim.models.word2vec.Word2Vec'>'

	hipparchiaDB=# select ts,uidlist,vectortype,baggingmethod from storedvectors;
	         ts          | uidlist  | vectortype | baggingmethod
	---------------------+----------+------------+----------------
	 2020-03-20 14:21:00 | {lt1318} | nn         | flat
	 2020-03-20 14:25:00 | {lt1318} | nn         | winnertakesall
	 2020-03-20 14:25:00 | {lt1318} | nn         | alternates
	 2020-03-20 14:26:00 | {lt1318} | nn         | unlemmatized
	(4 rows)

	:param vectorspace:
	:param uidlist:
	:param vectortype:
	:return:
	"""

	vectortype = so.vectorquerytype
	if vectortype == 'analogies':
		vectortype = 'nearestneighborsquery'

	if hipparchia.config['DISABLEVECTORSTORAGE']:
		consolewarning('DISABLEVECTORSTORAGE = True; the vector space for {i} was not stored'.format(i=so.searchid), color='black')

	if so.wholecorporasearched():
		uidlist = so.wholecorporasearched()
	else:
		uidlist = sorted(so.searchlist)

	dbconnection = ConnectionObject(ctype='rw')
	dbcursor = dbconnection.cursor()

	q = """
	DELETE FROM public.storedvectors WHERE 
		(uidlist = %s AND vectortype = %s AND baggingmethod = %s)
	"""

	d = (uidlist, vectortype, so.session['baggingmethod'])
	dbcursor.execute(q, d)

	q = """
	INSERT INTO public.storedvectors 
		(ts, thumbprint, uidlist, vectortype, baggingmethod, calculatedvectorspace)
		VALUES (%s, %s, %s, %s, %s, %s)
	"""

	pickledvectors = pickle.dumps(vectorspace)
	ts = datetime.now().strftime("%Y-%m-%d %H:%M")
	thumbprint = pickle.dumps(so.vectorvalues)

	d = (ts, thumbprint, uidlist, vectortype, so.session['baggingmethod'], pickledvectors)
	dbcursor.execute(q, d)

	# print('stored {u} in vector table (type={t})'.format(u=uidlist, t=vectortype))

	dbconnection.connectioncleanup()

	return


def checkforstoredvector(so: SearchObject):
	"""

	the stored vector might not reflect the current math rules

	return False if you are 'outdated'

	hipparchiaDB=# select ts,thumbprint,uidlist from storedvectors;
	        ts          | thumbprint |   uidlist
	---------------------+--------------+--------------
	2018-02-14 20:49:00 | json       | {lt0474w011}
	2018-02-14 20:50:00 | json       | {lt0474w057}
	(2 rows)

	:param so:
	:param vectortype:
	:param careabout:
	:return:
	"""

	careabout = 'thumbprint'

	vectortype = so.vectorquerytype
	if vectortype == 'analogies':
		vectortype = 'nearestneighborsquery'

	full = wholecorpuscheck(so)
	if full:
		uidlist = full
	else:
		uidlist = sorted(so.searchlist)

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	q = """
	SELECT {crit}, calculatedvectorspace 
		FROM public.storedvectors 
		WHERE uidlist=%s AND vectortype=%s AND baggingmethod = %s
	"""
	d = (uidlist, vectortype, so.session['baggingmethod'])

	try:
		cursor.execute(q.format(crit=careabout), d)
		result = cursor.fetchone()
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "public.storedvectors" does not exist
		createvectorstable()
		result = False
	except psycopg2.errors.UndefinedTable:
		createvectorstable()
		result = False

	if not result:
		return False

	storedvectorvalues = pickle.loads(result[0])
	currentvectorvalues = so.vectorvalues

	if storedvectorvalues == currentvectorvalues:
		returnval = pickle.loads(result[1])
	else:
		# print('vv not a match')
		returnval = False

	dbconnection.connectioncleanup()

	return returnval


def fetchverctorenvirons(hitdict: dict, searchobject: SearchObject) -> list:
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


def wholecorpuscheck(so: SearchObject):
	""""

	this is kludgy because so.wholecorporasearched() fails for checkforstoredvector() ATM

	BUT the logic is correct if you execute()

	just lifting the logic from there...

	"""

	sl = flagexclusions(so.searchlist, so.session)
	sl = calculatewholeauthorsearches(sl, authordict)

	corpora = {
		'lt': 'Latin',
		'gr': 'Greek',
		'ch': 'Christian',
		'in': 'Inscriptional',
		'dp': 'Papyrus'
	}

	corporasizes = {
		'lt': 362,
		'gr': 1823,
		'ch': 291,
		'in': 463,
		'dp': 516
	}

	fullcorpora = list()

	for key in corpora:
		test = [x for x in sl if x[:2] == key and len(x) == 6]
		if len(test) == corporasizes[key]:
			fullcorpora.append(corpora[key])
		else:
			pass

	# print('fullcorpora', fullcorpora)

	return fullcorpora
