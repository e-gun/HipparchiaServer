# -*- coding: utf-8 -*-
from multiprocessing import Value
from server.hipparchiaclasses import MPCounter

def initializeglobals():
	"""
	mp aware variables that can be used at the polling station
	:return:
	"""
	global pdactive
	global pdremaining
	global pdpoolofwork
	global pdsearchid
	global pdstatusmessage
	global pdhits
	
	pdactive = False
	pdremaining = Value('i',-1)
	pdpoolofwork = Value('i',-1)
	pdsearchid = Value('L',-1)
	pdstatusmessage = ''
	
	pdhits = MPCounter()
	pdhits.increment(-1)

