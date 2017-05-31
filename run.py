#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia

if __name__ == '__main__':

	# debug=True is considered to be a serious security hazard in a networked environment
	# if you are working on Hipparchia's code, you might be interested in this; otherwise there
	# are only bad reasons to set this to 'True'

	hipparchia.run(threaded=True, debug=False, host=hipparchia.config['LISTENINGADDRESS'], port=hipparchia.config['FLASKSERVEDFROMPORT'])