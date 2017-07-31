# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
def gtltsubstitutes(text):
	"""
		&lt; for ⟨
		&gt; for ⟩
	"""

	text = re.sub(r'⟨', r'&lt;', text)
	text = re.sub(r'⟩', r'&gt;', text)

	return text