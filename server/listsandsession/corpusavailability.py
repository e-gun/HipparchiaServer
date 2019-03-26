# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
from flask import session

from server import hipparchia
from server.startup import listmapper


def corpusselectionsasavalue(thesession=None) -> int:
	"""

	represent the active corpora as a pseudo-binary value: '10101' for ON/OFF/ON/OFF/ON

		l g i p c
		1 2 3 4 5

	:return: 24, etc
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	binarystring = '0b'

	for s in ['latincorpus', 'greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus']:
		if thesession[s]:
			binarystring += '1'
		else:
			binarystring += '0'

	binaryvalue = int(binarystring, 2)

	return binaryvalue


def corpusselectionsaspseudobinarystring(thesession=None) -> str:
	"""

	represent the active corpora as a pseudo-binary value: '10101' for ON/OFF/ON/OFF/ON

		l g i p c
		1 2 3 4 5

	:return: '11100', etc
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	binarystring = ''

	for s in ['latincorpus', 'greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'christiancorpus']:
		if thesession[s]:
			binarystring += '1'
		else:
			binarystring += '0'

	return binarystring


def justlatin(thesession=None) -> bool:
	"""

	probe the session to see if we are working in a latin-only environment: '10000' = 16

	:return: True or False
	"""
	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	if corpusselectionsasavalue(thesession) == 16:
		return True
	else:
		return False


def justtlg(thesession=None) -> bool:
	"""

	probe the session to see if we are working in a tlg authors only environment: '01000' = 8

	:return: True or False
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	if corpusselectionsasavalue(thesession) == 8:
		return True
	else:
		return False


def justinscriptions(thesession=None) -> bool:
	"""

	probe the session to see if we are working in a inscriptions-only environment: '00100' = 2
	useful in as much as the inscriptions data leaves certain columns empty every time

	:return: True or False
	"""
	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	if corpusselectionsasavalue(thesession) == 4:
		return True
	else:
		return False


def justpapyri(thesession=None) -> bool:
	"""

	probe the session to see if we are working in a papyrus-only environment: '00010' = 2
	useful in as much as the papyrus data leaves certain columns empty every time

	:return: True or False
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	if corpusselectionsasavalue(thesession) == 2:
		return True
	else:
		return False


def justlit(thesession=None) -> bool:
	"""

	probe the session to see if we are working in a TLG + LAT environment: '11000' = 24

	:return: True or False
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	if corpusselectionsasavalue(thesession) == 24:
		return True
	else:
		return False


def justdoc(thesession=None) -> bool:
	"""

	probe the session to see if we are working in a DDP + INS environment: '00110' = 6

	:return: True or False
	"""

	try:
		thesession['latincorpus']
	except TypeError:
		# you did not pass a (frozen)session: 'NoneType' object is not subscriptable
		thesession = session

	if corpusselectionsasavalue(thesession) == 6:
		return True
	else:
		return False


def corpusisonandavailable(corpusname):
	"""

	a rare situation:
		you set Greek as available by default but you have no Greek data
		you will see a Ⓖ forever

	this only happens to a 'naive' new installer who has an incomplete dataset

	:param corpusname:
	:return:
	"""

	options = {
		'christiancorpus': ('DEFAULTCHRISTIANCORPUSVALUE', 'ch'),
		'greekcorpus': ('DEFAULTGREEKCORPUSVALUE', 'gr'),
		'inscriptioncorpus': ('DEFAULTINSCRIPTIONCORPUSVALUE', 'in'),
		'latincorpus': ('DEFAULTLATINCORPUSVALUE', 'lt'),
		'papyruscorpus': ('DEFAULTPAPYRUSCORPUSVALUE', 'dp'),
	}

	assert corpusname in options, 'corpusisonandavailable() was sent a corpus not in known corpora'

	optiontuple = options[corpusname]

	setting = hipparchia.config[optiontuple[0]]
	available = len(listmapper[optiontuple[1]]['a'])

	if available > 0:
		return setting
	else:
		return 'no'
