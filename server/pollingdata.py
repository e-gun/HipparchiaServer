# -*- coding: utf-8 -*-
from multiprocessing import Value
from server.hipparchiaclasses import MPCounter

def initializeglobals():
	global pdactive
	global pdremaining
	global pdpoolofwork
	global pdstatusmessage
	
	pdactive = False
	pdremaining = Value('i',-1)
	pdpoolofwork = Value('i',-1)
	pdstatusmessage = ''
	
	# mp functions need lockable items
	
	global pdhits
	
	pdhits = MPCounter()
	pdhits.increment(-1)
