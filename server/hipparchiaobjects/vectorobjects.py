# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import session


class VectorValues(object):
	def __init__(self, frozensession=None):
		if not frozensession:
			s = session
		else:
			s = frozensession

		self.dimensions = s['vdim']
		self.window = s['vwindow']
		self.trainingiterations = s['viterat']
		self.minimumpresence = s['vminpres']
		self.downsample = s['vdsamp']/100
		self.localcutoffdistance = s['vcutloc']/100
		self.nearestneighborcutoffdistance = s['vcutneighb']/100
		self.lemmapaircutoffdistance = s['vcutlem']/100
		self.neighborscap = s['vnncap']
		self.sentencesperdocument = s['vsentperdoc']
		self.ldamaxfeatures = s['ldamaxfeatures']
		self.ldacomponents = s['ldacomponents']
		self.ldamaxfreq = s['ldamaxfreq']/100
		self.ldaminfreq = s['ldaminfreq']
		self.ldaiterations = s['ldaiterations']
		self.ldamustbelongerthan = s['ldamustbelongerthan']

	def __eq__(self, other):
		sd = self.__dict__
		od = other.__dict__
		assert isinstance(other, VectorValues), 'VectorValues can only be compared with VectorValues'
		# cc = [(sd[k], od[k]) for k in sd.keys()]
		# print('VectorValues cc', cc)

		comp = [sd[k] == od[k] for k in sd.keys()]
		if set(comp) == {True}:
			return True
		else:
			return False
