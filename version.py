#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import sys
from os import path


devel = False

hipparchiaserverversion = '1.6.2'
supplement = '+ [DEVEL]'

if devel:
	hipparchiaserverversion = hipparchiaserverversion + supplement


def readgitdata() -> str:
	"""

	find the most recent commit value

	a sample lastline:

		'3b0c66079f7337928b02df429f4a024dafc80586 63e01ae988d2d720b65c1bf7db54236b7ad6efa7 EG <egun@antisigma> 1510756108 -0500\tcommit: variable name changes; code tidy-ups\n'

	:return:
	"""

	here = path.dirname(sys.argv[0])
	gitfile = here + '/.git/logs/HEAD'
	line = str()

	success = False

	if path.exists(gitfile):
		success = True

	if not success:
		# maybe you are doing the EXTERNALWSGI thing
		# unfortunately hipparchia.config is not yet available...
		gitfile = '/home/hipparchia/hipparchia_venv/HipparchiaServer/.git/logs/HEAD'
		if path.exists(gitfile):
			success = True

	if success:
		with open(gitfile) as fh:
			for line in fh:
				pass
			lastline = line

		gitdata = lastline.split(' ')
		commit = gitdata[1]
	else:
		commit = 'commit data not found'

	return commit
