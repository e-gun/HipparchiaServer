# -*- coding: utf-8 -*-
#!../bin/python
from server import hipparchia

if __name__ == '__main__':

	hipparchia.run(threaded=True, host="0.0.0.0")