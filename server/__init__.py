# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import multiprocessing

from flask import Flask

hipparchia = Flask(__name__)

"""
https://docs.python.org/3.8/library/multiprocessing.html

spawn
The parent process starts a fresh python interpreter process. The child process will only inherit those resources necessary to run the process objects run() method. In particular, unnecessary file descriptors and handles from the parent process will not be inherited. Starting a process using this method is rather slow compared to using fork or forkserver.

Available on Unix and Windows. The default on Windows and macOS.

Changed in version 3.8: On macOS, the spawn start method is now the default. The fork start method should be considered unsafe as it can lead to crashes of the subprocess. See bpo-33725.

[but we never had problems with 'fork' in macos AND spawn is a lot slower...]

the 'loading dispatcher' step takes significantly too long as does 'executing the search' if you are 'spawining'; 
'forkserver' has basically the same cost?

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
   22    3.584    0.163    3.584    0.163 {built-in method posix.waitpid}
  706    2.981    0.004    2.981    0.004 {built-in method posix.read}

"""

mpmethod = str()
try:
	# mpmethod = 'forkserver'
	# this will get you into trouble with the vectorbot
	# TypeError: can't pickle psycopg2.extensions.connection objects
	mpmethod = 'fork'
	multiprocessing.set_start_method(mpmethod)
except RuntimeError:
	#   File "/usr/local/Cellar/python/3.7.6_1/Frameworks/Python.framework/Versions/3.7/lib/python3.7/multiprocessing/context.py", line 242, in set_start_method
	#     raise RuntimeError('context has already been set')
	# RuntimeError: context has already been set
	pass
except:
	mpmethod = 'spawn'
	multiprocessing.set_start_method(mpmethod)

from server import configureatstartup
from server import startup
from server.routes import browseroute, frontpage, getterroutes, hintroutes, debuggingroutes, lexicalroutes, searchroute, \
	selectionroutes, textandindexroutes, resetroutes, cssroutes, vectorroutes, authenticationroutes

if hipparchia.config['AUTOVECTORIZE']:
	from server.threading import vectordbautopilot

# put this here and not in 'run.py': otherwise gunicorn will not see it
hipparchia.config.update(SESSION_COOKIE_SECURE=False, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')

