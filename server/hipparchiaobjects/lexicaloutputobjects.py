# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from flask import session

from server.dbsupport.lexicaldbfunctions import findparserxref, grablemmataobjectfor, \
	probedictionary, querytotalwordcounts
from server.formatting.lexicaformatting import formatdictionarysummary, formatparsinginformation, formatprevalencedata, \
	getobservedwordprevalencedata
from server.formatting.wordformatting import attemptsigmadifferentiation, setdictionarylanguage
from server.hipparchiaobjects.morphanalysisobjects import BaseFormMorphology


class multipleWordOutputObject(object):
	"""

	handle the formatting of a collection of dictionary entries

	NB: most collections will contain only one word

	"""

	def __init__(self, thisword: str, morphologyobject, flagauthorid: str):
		self.thisword = thisword
		self.mo = morphologyobject
		self.flagauthor = flagauthorid
		self.thisformprevalence = getobservedwordprevalencedata(self.thisword)
		self.usedictionary = setdictionarylanguage(thisword)
		self.distinctpossibilities = self._builddistinctpossibilitiesdict()
		self.entriestocheck = self._buildentriestocheckdict()
		self.observedformsummary = self._getobservedformsummary()
		self.entrywordobjects = self._buildentrywordobjectdict()
		self.collectedlexicalouputobjects = self._buildcollectedlexicalouputobjects()

	def _setdictionarylanguage(self) -> str:
		if re.search(r'[a-z]', self.thisword):
			usedictionary = 'latin'
		else:
			usedictionary = 'greek'
		return usedictionary

	def _builddistinctpossibilitiesdict(self) -> dict:
		distinct = dict()
		for p in self.mo.getpossible():
			distinct[p.xref] = p.getbaseform()
		return distinct

	def _buildentriestocheckdict(self) -> dict:
		# note that we are going to be using a sortable list of integer keys throughout this lexicalOutputObject()
		entriestocheck = dict()
		count = 0
		for d in self.distinctpossibilities:
			count += 1
			entriestocheck[count] = self.distinctpossibilities[d]
		return entriestocheck

	def _getobservedformsummary(self) -> str:
		possibilities = self.mo.getpossible()
		morphhtml = formatparsinginformation(possibilities)
		return morphhtml

	def _buildentrywordobjectdict(self) -> dict:
		# a dict whose values are a list of wordobjects
		blankcursor = None
		wordobjectdict = dict()
		for e in self.entriestocheck:
			seekingentry = self.entriestocheck[e]
			wordobjectdict[e] = probedictionary(self.usedictionary + '_dictionary', 'entry_name', seekingentry, '=', dbcursor=blankcursor, trialnumber=0)

		wordobjectdict = {idx: wordobjectdict[idx] for idx in wordobjectdict if wordobjectdict[idx]}

		for w in wordobjectdict:
			for i in wordobjectdict[w]:
				i.flagauthor = self.flagauthor

		return wordobjectdict

	def _buildcollectedlexicalouputobjects(self) -> dict:
		# a dict whose values are a list of lexicalOutputObjects
		# e.g., {1: [<server.hipparchiaobjects.lexicaloutputobjects.lexicalOutputObject object at 0x15285f6a0>]}

		lexobjects = dict()
		for e in self.entrywordobjects:
			lexobjects[e] = [lexicalOutputObject(o) for o in self.entrywordobjects[e]]
		return lexobjects

	def generateoutput(self) -> str:
		output = list()
		output.append(self.thisformprevalence)
		output.append(self.observedformsummary)

		if len(self.collectedlexicalouputobjects) == 1:
			usecounter = False
		else:
			usecounter = True

		topcount = 0
		dupeskipper = set()

		for lex in self.collectedlexicalouputobjects:
			topcount += 1
			# a dict whose values are a list of lexicalOutputObjects
			if len(self.collectedlexicalouputobjects[lex]) == 1:
				usesubcounter = False
			else:
				usesubcounter = True

			subcount = 0
			for oo in self.collectedlexicalouputobjects[lex]:
				if oo.id not in dupeskipper:
					dupeskipper.add(oo.id)
					subcount += 1
					if usesubcounter:
						countervalue = str(topcount) + chr(subcount + 96)
					else:
						countervalue = str(topcount)

					if usecounter:
						entry = oo.generatelexicaloutput(countervalue=countervalue)
					else:
						entry = oo.generatelexicaloutput()

					output.append(entry)

		output = [o for o in output if o]
		newhtml = '\n'.join(output)
		return newhtml


class lexicalOutputObject(object):
	"""

	handle the formatting of a generic dictionary entry

	"""

	def __init__(self, thiswordobject):
		self.thiswordobject = thiswordobject
		self.id = thiswordobject.id
		self.usedictionary = setdictionarylanguage(thiswordobject.entry)
		self.thisheadword = thiswordobject.entry
		self.headwordprevalence = getobservedwordprevalencedata(self.thisheadword)
		self.entryhead = self.thiswordobject.grabheadmaterial()
		self.entrysprincipleparts = self._buildprincipleparts()
		self.entrydistributions = self._builddistributiondict()
		self.fullenty = self._buildfullentry()
		# next needs previous to fullentry: regex search needs entry body rewrite
		self.authorentrysummary = self._buildauthorentrysummary()
		self.entrysummary = self._buildentrysummary()

	def _buildentrydistributionss(self) -> str:
		distributions = str()
		if session['showwordcounts']:
			countobject = querytotalwordcounts(self.thisheadword)
			if countobject:
				prev = formatprevalencedata(countobject)
				distributions = '<p class="wordcounts">Prevalence (all forms):\n{pr}\n</p>'.format(pr=prev)
		return distributions

	def _buildprincipleparts(self) -> str:
		morphabletemplate = """
		<formsummary parserxref="{px}" lexicalid="{lid}" headword="{w}" lang="{lg}">known forms in use: {f}</formsummary>
		<table class="morphtable">
			<tbody>
				<tr><th class="morphcell labelcell" rowspan="1" colspan="2">{head}</th></tr>	
				{trs}
			</tbody>
		</table>
		"""

		morphrowtemplate = """
		<tr>
			<td class="morphcell labelcell">[{ct}]</td>
			<td class="morphcell">{ppt}</td>
		</tr>
		"""

		pppts = str()
		w = self.thiswordobject
		if session['principleparts']:
			# fingerprints = {'v.', 'v. dep.', 'v. a.', 'v. n.'}
			# and, sadly, some entries do not have a POS: "select pos from latin_dictionary where entry_name='declaro';"
			# declaro: w.pos ['']
			# if (fingerprints & set(w.pos)) or w.pos == ['']:
			xref = findparserxref(w)
			morphanalysis = BaseFormMorphology(w.entry, xref, self.usedictionary, self.id, session)
			ppts = morphanalysis.getprincipleparts()
			if ppts and morphanalysis.iammostlyconjugated():
				trs = [morphrowtemplate.format(ct=p[0], ppt=p[1]) for p in ppts]
				pppts = morphabletemplate.format(f=morphanalysis.numberofknownforms, trs='\n'.join(trs), px=xref, w=w.entry, lid=self.id, lg=self.usedictionary, head='principle parts')
			elif morphanalysis.iamdeclined():
				trs = str()
				pppts = morphabletemplate.format(f=morphanalysis.numberofknownforms, trs=trs, px=xref, w=w.entry, lid=self.id, lg=self.usedictionary, head=str())

		return pppts

	def _buildentrysummary(self) -> str:
		blankcursor = None
		entryword = self.thiswordobject
		if not entryword.isagloss():
			lemmaobject = grablemmataobjectfor(self.usedictionary + '_lemmata', word=entryword.entry, dbcursor=blankcursor)
			entryword.authorlist = entryword.generateauthorsummary()
			entryword.senselist = entryword.generatesensessummary()
			entryword.quotelist = entryword.generatequotesummary(lemmaobject)
			entryword.flaggedsenselist = self.authorentrysummary
			# entryword.flaggedsenselist = entryword.generateflaggedsummary()
			# print('entryword.flaggedsenselist', entryword.flaggedsenselist)

		awq = entryword.authorlist + entryword.senselist + entryword.quotelist + entryword.flaggedsenselist
		zero = ['0 authors', '0 senses', '0 quotes', '0 flagged senses']
		for z in zero:
			try:
				awq.remove(z)
			except ValueError:
				pass

		if len(awq) > 0:
			summary = formatdictionarysummary(entryword)
		else:
			summary = str()
		return summary

	def _buildauthorentrysummary(self) -> List[str]:
		# this only semi-works; the unclean boundarie
		# note that wo.insertclickablelookups() needs to run before the regex here will work
		wo = self.thiswordobject
		flagged = wo.flagauthor
		if not flagged:
			return list(str())

		# transfinder = re.compile(r'<span class="dicttrans">(.*?)</span>')
		# note the sneaky regex...
		transbodyfinder = re.compile(r'rans">(.*?)</span>(.*?)(</sense>|span class="dictt)')
		senses = re.findall(transbodyfinder, wo.body)
		flaggedsenses = [s[0] for s in senses if re.search(flagged, s[1])]
		flaggedsenses.sort()
		print('flaggedsenses', flaggedsenses)
		return flaggedsenses

	def _builddistributiondict(self) -> str:
		distributions = str()
		if session['showwordcounts']:
			countobject = querytotalwordcounts(self.thisheadword)
			if countobject:
				prev = formatprevalencedata(countobject)
				distributions = '<p class="wordcounts">Prevalence (all forms):\n{pr}\n</p>'.format(pr=prev)
		return distributions

	def _buildfullentry(self) -> str:
		fullentrystring = '<br /><br />\n<span class="lexiconhighlight">Full entry:</span><br />'
		w = self.thiswordobject
		w.constructsensehierarchy()
		w.runbodyxrefsuite()
		w.insertclickablelookups()
		# next is optional, really: a good CSS file will parse what you have thus far
		# (HipparchiaServer v.1.1.2 has the old XML CSS)
		w.xmltohtmlconversions()
		segments = list()
		segments.append(w.grabheadmaterial())
		segments.append(fullentrystring)
		segments.append(w.grabnonheadmaterial())
		fullentry = '\n'.join(segments)
		return fullentry

	def generatelexicaloutput(self, countervalue=None) -> str:
		divtemplate = '<div id="{wd}_{idx}">\n{entry}\n</div>'
		if countervalue:
			headingstr = '<hr /><p class="dictionaryheading" id={wd}_{wordid}>({cv})&nbsp;{ent}'
		else:
			headingstr = '<hr /><p class="dictionaryheading" id={wd}_{wordid}>{ent}'
		metricsstr = '&nbsp;<span class="metrics">[{me}]</span>'
		codestr = '&nbsp;<code>[ID: {wordid}]</code>'
		xrefstr = '&nbsp;<code>[XREF: {xref}]</code>'

		navtemplate = """
		<table class="navtable">
		<tr>
			<td class="alignleft">
				<span class="label">Previous: </span>
				<dictionaryidsearch entryid="{pid}" language="{lg}">{p}</dictionaryidsearch>
			</td>
			<td>&nbsp;</td>
			<td class="alignright">
				<span class="label">Next: </span>
				<dictionaryidsearch entryid="{nid}" language="{lg}">{n}</dictionaryidsearch>
			</td>
		<tr>
		</table>
		"""

		w = self.thiswordobject
		if w.isgreek():
			language = 'greek'
		else:
			language = 'latin'

		outputlist = list()
		outputlist.append(headingstr.format(ent=w.entry, cv=countervalue, wordid=w.id, wd=self.thisheadword))

		if w.metricalentry != w.entry:
			outputlist.append(metricsstr.format(me=w.metricalentry))

		if session['debuglex']:
			outputlist.append(codestr.format(wordid=w.id))
			xref = findparserxref(w)
			outputlist.append(xrefstr.format(xref=xref))
		outputlist.append('</p>')

		outputlist.append(self.entrysprincipleparts)
		outputlist.append(self.entrydistributions)
		outputlist.append(self.entrysummary)
		outputlist.append(self.fullenty)

		outputlist.append(navtemplate.format(pid=w.preventryid, p=w.preventry, nid=w.nextentryid, n=w.nextentry, lg=language))

		fullentry = '\n'.join(outputlist)

		if session['zaplunates']:
			fullentry = attemptsigmadifferentiation(fullentry)

		fullentry = divtemplate.format(wd=self.thisheadword, idx=findparserxref(w), entry=fullentry)
		return fullentry
