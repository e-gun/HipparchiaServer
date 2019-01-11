# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import session

from server import hipparchia
from server.formatting.bibliographicformatting import avoidlonglines
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.wordformatting import avoidsmallvariants


class BrowserOutputObject(object):
	"""

	basically a dict to help hold and format the html output of a browsed passage

	browserdata.keys() dict_keys(['browseforwards', 'browseback', 'authornumber',
	'workid', 'authorboxcontents', 'workboxcontents', 'browserhtml'])

	"""

	def __init__(self, authorobject, workobject, locusindexvalue):
		self.ao = authorobject
		self.wo = workobject
		self.authornumber = authorobject.universalid
		self.workid = workobject.universalid
		self.authorboxcontents = '{n} [{uid}]'.format(n=authorobject.cleanname, uid=authorobject.universalid)
		self.workboxcontents = '{t} ({wkid})'.format(t=workobject.title, wkid=workobject.universalid[-4:])
		self.linesofcontext = int(session['browsercontext'])

		if locusindexvalue:
			self.psgends = locusindexvalue + self.linesofcontext
			self.psgstarts = locusindexvalue - self.linesofcontext
		else:
			self.psgends = workobject.ends
			self.psgstarts = workobject.starts

		if self.psgends > workobject.ends:
			self.psgends = workobject.ends
		if self.psgstarts < workobject.starts:
			self.psgstarts = workobject.starts

		self.browseforwards = 'linenumber/{w}/{e}'.format(w=self.workid, e=self.psgends)
		self.browseback = 'linenumber/{w}/{s}'.format(w=self.workid, s=self.psgstarts)

		# defaults that will change later
		self.browserhtml = '[nothing found]'

	def generateoutput(self):
		outputdict = dict()
		requiredkeys = ['browseforwards', 'browseback', 'authornumber', 'workid',
		                'authorboxcontents', 'workboxcontents', 'browserhtml']
		for item in requiredkeys:
			outputdict[item] = getattr(self, item)

		return outputdict


class BrowserPassageObject(object):
	"""

	the lines of a browser passage

	"""

	def __init__(self, authorobject, workobject, dblinenumber, resultmessage='success'):
		self.authorobject = authorobject
		self.workobject = workobject
		self.index = dblinenumber
		self.resultmessage = resultmessage

		# to be calculated on initialization
		if self.workobject.isliterary():
			self.name = authorobject.shortname
		else:
			self.name = authorobject.idxname
		self.name = avoidsmallvariants(self.name)
		self.title = avoidsmallvariants(workobject.title)
		try:
			if int(workobject.converted_date) < 1500:
				self.date = int(workobject.converted_date)
			else:
				self.date = None
		except:
			self.date = None
		self.linetemplate = self.getlinetemplate()

		# to be populated later, mostly by generatepassageheader()
		self.browsedlines = list()
		self.focusline = None
		self.biblio = ''
		self.citation = ''
		self.header = ''
		self.authorandwork = ''

	def generatepassageheader(self):
		template = '<span class="currentlyviewingauthor">{n}</span>, <span class="currentlyviewingwork">{t}</span><br />'
		self.authorandwork = template.format(n=self.name, t=self.title)
		viewing = list()
		viewing.append(avoidlonglines(self.authorandwork, 100, '<br />\n', list()))
		viewing.append('<span class="currentlyviewingcitation">{c}</span>'.format(c=self.citation))
		if self.date:
			if self.date > 1:
				viewing.append('<br /><span class="assigneddate">(Assigned date of {d} CE)</span>'.format(d=self.date))
			else:
				viewing.append('<br /><span class="assigneddate">(Assigned date of {d} BCE)</span>'.format(d=str(self.date)[1:]))
		viewing = '\n'.join(viewing)
		header = '<p class="currentlyviewing">{c}\n<br />\n{b}\n</p>'.format(c=viewing, b=self.biblio)
		return header

	def getlinetemplate(self, shownotes=True):
		if session['simpletextoutput'] == 'yes':
			linetemplate = """
			<p class="browsedline">
				{l}
				&nbsp;
				<span class="browsercite">{c}</span>
			</p>
			
			"""
			return linetemplate

		if shownotes:
			linetemplate = """
			<tr class="browser">
				<td class="browserembeddedannotations">{n}</td>
				<td class="browsedline">{l}</td>
				<td class="browsercite">{c}</td>
			</tr>
			"""
		else:
			linetemplate = """
			<tr class="browser">
				<td class="browsedline">{l}</td>
				<td class="browsercite">{c}</td>
			</tr>
			"""
		return linetemplate

	def generatepassagetable(self):
		outputtable = list()
		outputtable.append('<table>')
		try:
			spacer = ''.join(['&nbsp;' for _ in range(0, hipparchia.config['MINIMUMBROWSERWIDTH'])])
			outputtable.append('<tr class="spacing">{sp}</tr>'.format(sp=spacer))
		except:
			pass

		outputtable = outputtable + self.browsedlines

		if session['debughtml'] == 'yes':
			outputtable.append('</table>\n<span class="emph">(NB: click-to-parse is off if HTMLDEBUGMODE is set)</span>')
		else:
			outputtable.append('</table>')

		tablehtml = '\n'.join(outputtable)

		return tablehtml

	def generatepassagehtml(self):
		html = self.generatepassageheader() + self.generatepassagetable()
		if hipparchia.config['INSISTUPONSTANDARDANGLEBRACKETS'] == 'yes':
			html = gtltsubstitutes(html)
		return html
