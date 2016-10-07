import re
import pickle
from bs4 import BeautifulSoup


def grabsenses(fullentry):
	
	sensing = re.compile(r'<sense.*?/sense>')
	senses = re.findall(sensing, fullentry)
	leveler = re.compile(r'<sense\s.*?level="(.*?)".*?>')
	nummer = re.compile(r'<sense.*?\sn="(.*?)".*?>')
	numbered = []
	i = 0
	
	for sense in senses:
		i += 1
		lvl = re.search(leveler,sense)
		num = re.search(nummer,sense)
		try:
			rewritten = '<span class="level'+lvl.group(1)+'">'+num.group(1)+'</span>&nbsp;'+sense
		except:
			print('exception in grabsenses at sense number:',i)
			rewritten = ''
		numbered.append(rewritten)

	return numbered


def entrysummary(fullentry,lang, translationlabel):
	"""
	returns a collection of lists: all authors, senses, and quotes to be found in an entry
	:param fullentry:
	:return:
	"""
	
	soup = BeautifulSoup(fullentry, 'html.parser')
	a = soup.find_all('author')
	a = list(set(a))
	# the list is composed of objj. that are <class 'bs4.element.Tag'>
	a[:] = [value.string for value in a]
	notin = ['id.', 'ib.', 'Id.']
	a[:] = [value for value in a if value not in notin]
	a.sort()
	newa = []
	for au in a:
		newa.append(deabbreviateauthors(au, lang))
	a = newa

	s = soup.find_all(translationlabel)
	notin = ['ab','de', 'ex','ut', 'nihil', 'quam', 'quid']
	s[:] = [value.string for value in s]
	s[:] = [value for value in s if '.' not in value]
	s[:] = [value for value in s if value not in notin]
	s = list(set(s))

	q = soup.find_all('quote')
	q[:] = [value.string for value in q]

	summary = (a,s,q)

	return summary


def grabheadmaterial(fullentry):
	heading = re.compile(r'(.*?)\<sense')
	head = re.search(heading,fullentry)
	try:
		return head.group(0)
	except:
		print('failed to find head.group(0) in grabheadmaterial')
		return ''


def deabbreviateauthors(authorabbr, lang):
	
	if lang == 'latin':
		decoder = { 'Caes.':'Caesar',
		        'Cat.':'Catullus',
	            'Cic.':'Cicero',
	            'Enn.': 'Ennius',
	            'Fest.':'Festus',
	            'Gell.': 'Gellius',
	            'Hor.':'Horace',
	            'Juv.': 'Juvenal',
	            'Lact.':'Lactantius',
	            'Liv.':'Livy',
	            'Lucr.':'Lucretius',
	            'Macr.':'Macrobius',
	            'Mart.':'Martial',
	            'Nep.': 'Nepos',
	            'Non.':'Nonius',
	            'Ov.':'Ovid',
	            'Pall.':'Palladius',
	            'Pers.':'Persius',
	            'Petr.':'Petronius',
	            'Phaed.':'Phaedrus',
	            'Plaut.':'Plautus',
	            'Plin.':'Pliny',
	            'Prop.':'Propertius',
	            'Quint.':'Quintilian',
	            'Sall.':'Sallust',
	            'Sen.':'Seneca',
	            'Stat.':'Statius',
	            'Suet.':'Suetonius',
	            'Tac.':'Tacitus',
	            'Ter.':'Terence',
	            'Varr.':'Varro',
	            'Vell.':'Velleius',
	            'Verg.':'Vergil',
		        'Vitr.':'Vitruvius'

	            }
	elif lang == 'greek':
		decoder = { 'A.': 'Aeschylus',
		            'Aeschin.': 'Aeschines',
		            'And.': 'Andocides',
		            'Antiph.': 'Antiphon',
					'Ar.': 'Aristophanes',
		            'Arist.': 'Aristotle',
		            'Ath.': 'Athenaeus',
		            'B.': 'Bacchylides',
		            'Call.': 'Callimachus',
		            'D.': 'Demosthenes',
		            'D.C.': 'Dio Cassius',
		            'D.H.': 'Dionysius of Halicarnassus',
		            'D.L.': 'Diogenes Laertius',
		            'E.': 'Euripides',
		            'Gal.': 'Galen',
		            'Hdt.': 'Herodotus',
		            'Hes.': 'Hesiod',
		            'Hom.': 'Homer',
		            'Hp.': 'Hippocrates',
		            'Il.': 'Homer (Iliad)',
		            'Is.': 'Isaeus',
		            'Isoc.': 'Isocrates',
		            'J.': 'Josephus',
		            'Jul.': 'Julian',
		            'Luc.': 'Lucian',
		            'LXX': 'Septuagint',
		            'Lycurg.': 'Lycurgus',
		            'Lys.': 'Lysias',
		            'Men.': 'Menander',
		            'Od.': 'Homer (Odyssey)',
		            'Paus.': 'Pausanias',
		            'Pi.':'Pindar',
		            'Pl.':'Plato',
		            'Plb.':'Polybius',
		            'Plot.': 'Plotinus',
		            'Plu.':'Plutarch',
		            'S.':'Sophocles',
		            'Sosith.': 'Sositheus',
		            'Th.': 'Thucydides',
		            'Theoc.': 'Theocritus',
		            'Thgn.': 'Theognis',
		            'Tim.': 'Timaeus',
		            'X.': 'Xenophon',
		            'Xenoph.': 'Xenophanes'
		            }
	else:
		decoder = {}

	if authorabbr in decoder:
		author = decoder[authorabbr]
	else:
		author = authorabbr
	return author


def formatdictionarysummary(authors,senses,quotes):
	summary = ''
	if len(authors) > 0:
		summary += '<br \>\n<div class="authorsummary"><span class="highlight">Used by:</span><br \>\n'
		for a in authors:
			summary += '<span class="author">'+a+'</span><br \>\n'
	if len(senses) > 0:
		summary += '</div>\n<br \><div class="sensesummary"><span class="highlight">Senses:</span><br \>\n'
		for s in senses:
			summary += '<span class="sense">' + s + '</span><br \>\n'
	if len(quotes) > 0:
		summary += '</div>\n<br \><div class="quotesummary"><span class="highlight">Phrases:</span><br \>\n'
		for q in quotes:
			summary += '<span class="quote">' + q + '</span><br \>\n'
	summary += '</div><br \><br \>\n<span class="highlight">Full entry:</span><br \>'

	return summary


def parsemorphologyentry(entrydata):
	"""
	send me hit from findbyform() in the results browser

	possible = re.compile(r'(<possibility_(\d{1,2})>)(.*?)<xref_value>(.*?)</xref_value>(.*?)</possibility_\d{1,2}>')
	1 = #, 2 = word, 4 = body, 3 = xref

	this will look like: '<possibility_1>ἔπαλξιϲ<xref_value>39591208</xref_value><transl>means of defence</transl><analysis>fem nom/voc pl (attic epic)</analysis></possibility_1>\n<possibility_2>ἔπαλξιϲ<xref_value>39591208</xref_value><transl>means of defence</transl><analysis>fem nom/acc pl (attic)</analysis></possibility_2>\n'
	I will break it up into its components

	:param entrydata:
	:return:
	"""

	analysis = '<p class="obsv">('+entrydata[1]+')&nbsp;<span class="dictionaryform" id="' + entrydata[2] + '">' + entrydata[2] + '</span>'
	analysis +=	'<br /><possibility id="possibility_' + entrydata[1] + '">'+ entrydata[4]+'<br /></possibility></p>\n'
	# looks kinda icky, buy you should fix this in the db entries themselves to get rid of all the lexica via tabs

	return analysis


def formatgloss(entrybody):
	"""
	glosses don't work the same as standard dictionary entries. deal with them
	:param entrybody:
	:return:
	"""
	glosshtml = ''
	
	soup = BeautifulSoup(entrybody, 'html.parser')
	senses = soup.find_all('foreign')
	sources = soup.find_all('author')
	
	senses[:] = [value.string for value in senses]
	sources[:] = [value.string for value in sources]
	
	glosshtml += '<span class="highlight">Reported by:</span><br />\n'
	for s in sources:
		glosshtml += s + ', '
	glosshtml = glosshtml[:-2]
	
	glosshtml += '<br /><br />\n<span class="highlight">Senses:</span><br />'
	for s in senses:
		glosshtml += s + '<br />'
	
	return glosshtml

def formatmicroentry(entrybody):
	"""
	some entries work like glosses but are not labeled as glosses: no quote, authors, etc. just a synonym or synonyms listed
	deal with it
	:param entrybody:
	:return:
	"""
	entryhtml = ''
	
	soup = BeautifulSoup(entrybody, 'html.parser')
	senses = soup.find_all('foreign')
	senses[:] = [value.string for value in senses]
	
	entryhtml += '<span class="highlight">Senses:</span><br />'
	for s in senses:
		entryhtml += s + '<br />'
		
	entryhtml = entrybody
	
	return entryhtml