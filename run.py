#!../bin/python
from server import hipparchia

if __name__ == '__main__':
	#hipparchia.run(debug=True)
	# hipparchia.run(threaded=True, host="0.0.0.0")
	
	# see notes on dbauthormakersubroutine(): threads mean we can get ahead of ourselves
	hipparchia.run(threaded=False, host="0.0.0.0")