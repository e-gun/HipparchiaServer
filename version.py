#!../bin/python
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from sys import argv
from os import path


stable = False
release = False

hipparchiaserverversion = '1.6.11'
plus = '+'
supplement = '[DEVEL]'

if not release:
	hipparchiaserverversion = hipparchiaserverversion + plus

if not stable:
	hipparchiaserverversion = hipparchiaserverversion + supplement


def readgitdata() -> str:
	"""

	find the most recent commit value

	a sample lastline:

		'3b0c66079f7337928b02df429f4a024dafc80586 63e01ae988d2d720b65c1bf7db54236b7ad6efa7 EG <egun@antisigma> 1510756108 -0500\tcommit: variable name changes; code tidy-ups\n'

	:return:
	"""

	if 'run.py' in argv[0]:
		here = path.dirname(argv[0])
		gitfile = path.join(here, '.git/logs/HEAD')
	else:
		# gunicorn: '/home/hipparchia/hipparchia_venv/bin/gunicorn'
		here = path.split(path.dirname(argv[0]))[0]  # '/home/hipparchia/hipparchia_venv'
		gitfile = path.join(here, 'HipparchiaServer/.git/logs/HEAD')

	if path.exists(gitfile):
		with open(gitfile) as fh:
			for line in fh:
				pass
			lastline = line

		gitdata = lastline.split(' ')
		commit = gitdata[1]
	else:
		commit = 'N/A'

	return commit
