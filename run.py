# -*- coding: utf-8 -*-
#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

terminaltext = """
{project} / Copyright (C) {year} / {fullname}
{mail}

This program comes with ABSOLUTELY NO WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

This is free software, and you are welcome to redistribute it and/or modify
it under the terms of the GNU General Public License version 3.

"""

print(terminaltext.format(project='HipparchiaServer', year='2016-17', fullname='E. Gunderson',
                          mail='Department of Classics, 125 Queen’s Park, Toronto, ON M5S 2C7 Canada'))

from server import hipparchia

if __name__ == '__main__':

	hipparchia.run(threaded=True, host="0.0.0.0")