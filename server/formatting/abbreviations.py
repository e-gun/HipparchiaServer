# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from typing import Dict


def deabbreviateauthors(authorabbr: str, lang: str) -> str:
	"""

	just hand this off to another function via language setting

	:param authorabbr:
	:param lang:
	:return:
	"""

	if lang == 'greek':
		authordict = deabrevviategreekauthors()
	elif lang == 'latin':
		authordict = deabrevviatelatinauthors()
	else:
		authordict = dict()

	if authorabbr in authordict:
		author = authordict[authorabbr]
	else:
		author = authorabbr

	return author


def deabrevviategreekauthors() -> Dict[str, str]:
	"""

	return a decoder dictionary

	copy the the appropriate segment at the top of of greek-lexicon_1999.04.0057.xml into a new file
	[lines 788 to 4767]

	then:

		grep "<item><hi rend=\"bold\">" tlg_authors_and_works.txt > tlg_authorlist.txt
		perl -pi -w -e 's/<\/hi>.*?\[/<\/hi>\[/g;' tlg_authorlist.txt
		perl -pi -w -e 's/<item><hi rend="bold">//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/hi>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<date>.*?<\/date>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<title>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/title>//g;' tlg_authorlist.txt
		perl -pi -w -e 's/<\/item>//g;' tlg_authorlist.txt

	what remains will look like:

		Aelius Dionysius[Ael.Dion.]

	then regex:
		^(.*?)\[(.*?)\]  ==> '\2': '\1',

	then all lines with single quotes and colons are good

		grep ":" tlg_authorlist.txt > tlg_authordict.txt

	there are some key collisions, but you are basically done after you whack those moles

	:param:
	:return: authordict
	"""
	authordict = {
		'Abyd.': 'Abydenus',
		'Acerat.': 'Aceratus',
		'Acesand.': 'Acesander',
		'Achae.': 'Achaeus',
		'Ach.Tat.': 'Achilles Tatius',
		'Acus.': 'Acusilaus',
		'Adam.': 'Adamantius',
		'Ael.': 'Aelianus',
		'Ael.Dion.': 'Aelius Dionysius',
		'Aemil.': 'Aemilianus',
		'Aen.Gaz.': 'Aeneas Gazaeus',
		'Aen.Tact.': 'Aeneas Tacticus',
		'Aesar.': 'Aesara',
		'Aeschin.': 'Aeschines',
		'Aeschin.Socr.': 'Aeschines Socraticus',
		'A.': 'Aeschylus',
		'Aesch.Alex.': 'Aeschylus Alexandrinus',
		'Aesop.': 'Aesopus',
		'Aët.': 'Aëtius',
		'Afric.': 'Africanus, Julius',
		'Agaclyt.': 'Agaclytus',
		'Agatharch.': 'Agatharchides',
		'Agathem.': 'Agathemerus',
		'Agath.': 'Agathias',
		'Agathin.': 'Agathinus',
		'Agathocl.': 'Agathocles',
		'Alb.': 'Albinus',
		'Alc.Com.': 'Alcaeus',
		'Alc.': 'Alcaeus',
		'Alc.Mess.': 'Alcaeus Messenius',
		'Alcid.': 'Alcidamas',
		'Alcin.': 'Alcinous',
		'Alciphr.': 'Alciphro',
		'Alcm.': 'Alcman',
		'Alexand.Com.': 'Alexander',
		'Alex.Aet.': 'Alexander Aetolus',
		'Alex.Aphr.': 'Alexander Aphrodisiensis',
		'Alex.Eph.': 'Alexander Ephesius',
		'Alex.Polyh.': 'Alexander Polyhistor',
		'Alex.Trall.': 'Alexander Trallianus',
		'Alex.': 'Alexis',
		'Alph.': 'Alpheus',
		'Alyp.': 'Alypius',
		'Amips.': 'Amipsias',
		'Ammian.': 'Ammianus',
		'Amm.Marc.': 'Ammianus Marcellinus',
		'Ammon.': 'Ammonius',
		'Anach.': 'Anacharsis',
		'Anacr.': 'Anacreon',
		'Anacreont.': 'Anacreontea',
		'Anan.': 'Ananius',
		'Anaxag.': 'Anaxagoras',
		'Anaxandr.': 'Anaxandrides',
		'Anaxandr.Hist.': 'Anaxandrides',
		'Anaxarch.': 'Anaxarchus',
		'Anaxil.': 'Anaxilas',
		'Anaximand.Hist.': 'Anaximander',
		'Anaximand.': 'Anaximander',
		'Anaximen.': 'Anaximenes',
		'Anaxipp.': 'Anaxippus',
		'And.': 'Andocides',
		'Androm.': 'Andromachus',
		'Andronic.': 'Andronicus',
		'Andronic.Rhod.': 'Andronicus Rhodius',
		'Androt.': 'Androtion',
		'AB': 'Anecdota Graeca',
		'Anecd.Stud.': 'Anecdota Graeca et Latina',
		'Anon.': 'Anonymus',
		'Anon.Lond.': 'Anonymus Londnensis',
		'Anon.Rhythm.': 'Anonymus Rhythmicus',
		'Anon.Vat.': 'Anonymus Vaticanus',
		'Antag.': 'Antagoras',
		'Anthem.': 'Anthemius',
		'Anticl.': 'Anticlides',
		'Antid.': 'Antidotus',
		'Antig.': 'Antigonus Carystius',
		'Antig.Nic.': 'Antigonus Nicaeanus',
		'Antim.': 'Antimachus Colophonius',
		'Antioch.Astr.': 'Antiochus Atheniensis',
		'Antioch.': 'Antiochus',
		'Antioch.Hist.': 'Antiochus',
		'Antip.Sid.': 'Antipater Sidonius',
		'Antip.Stoic.': 'Antipater Tarsensis',
		'Antip.Thess.': 'Antipater Thessalonicensis',
		'Antiph.': 'Antiphanes',
		'Antiphan.': 'Antiphanes Macedo',
		'Antiphil.': 'Antiphilus',
		'Antipho Soph.': 'Antipho Sophista',
		'Antipho Trag.': 'Antipho',
		'Antisth.': 'Antisthenes',
		'Antist.': 'Antistius',
		'Ant.Lib.': 'Antoninus Liberalis',
		'Anton.Arg.': 'Antonius Argivus',
		'Ant.Diog.': 'Antonius Diogenes',
		'Antyll.': 'Antyllus',
		'Anub.': 'Anubion',
		'Anyt.': 'Anyte',
		'Aphth.': 'Aphthonius',
		'Apollinar.': 'Apollinarius',
		'Apollod.Com.': 'Apollodorus',
		'Apollod.Car.': 'Apollodorus Carystius',
		'Apollod.Gel.': 'Apollodorus Gelous',
		'Apollod.': 'Apollodorus',
		'Apollod.Lyr.': 'Apollodorus',
		'Apollod.Stoic.': 'Apollodorus Seleuciensis',
		'Apollonid.': 'Apollonides',
		'Apollonid.Trag.': 'Apollonides',
		'Apollon.': 'Apollonius',
		'Apollon.Cit.': 'Apollonius Citiensis',
		'A.D.': 'Apollonius Dyscolus',
		'Apollon.Perg.': 'Apollonius Pergaeus',
		'A.R.': 'Apollonius Rhodius',
		'Ap.Ty.': 'Apollonius Tyanensis',
		'Apolloph.': 'Apollophanes',
		'Apolloph.Stoic.': 'Apollophanes',
		'Apostol.': 'Apostolius',
		'App.': 'Appianus',
		'Aps.': 'Apsines',
		'Apul.': 'Apuleius',
		'Aq.': 'Aquila',
		'Arab.': 'Arabius',
		'Arar.': 'Araros',
		'Arat.': 'Aratus',
		'Arc.': 'Arcadius',
		'Arcesil.': 'Arcesilaus',
		'Arched.': 'Archedicus',
		'Arched.Stoic.': 'Archedemus Tarsensis',
		'Archemach.': 'Archemachus',
		'Archestr.': 'Archestratus',
		'Arch.': 'Archias',
		'Arch.Jun.': 'Archias Junior',
		'Archig.': 'Archigenes',
		'Archil.': 'Archilochus',
		'Archim.': 'Archimedes',
		'Archimel.': 'Archimelus',
		'Archipp.': 'Archippus',
		'Archyt.Amph.': 'Archytas Amphissensis',
		'Archyt.': 'Archytas Tarentinus',
		'Aret.': 'Aretaeus',
		'Aristaenet.': 'Aristaenetus',
		'Aristag.': 'Aristagoras',
		'Aristag.Hist.': 'Aristagoras',
		'Aristarch.': 'Aristarchus',
		'Aristarch.Sam.': 'Aristarchus Samius',
		'Aristarch.Trag.': 'Aristarchus',
		'Aristeas Epic.': 'Aristeas',
		'Aristid.': 'Aristides',
		'Aristid.Mil.': 'Aristides Milesius',
		'Aristid.Quint.': 'Aristides Quintilianus',
		'Aristipp.': 'Aristippus',
		'AristoStoic.': 'Aristo Chius',
		'Aristobul.': 'Aristobulus',
		'Aristocl.': 'Aristocles',
		'Aristocl.Hist.': 'Aristocles',
		'Aristodem.': 'Aristodemus',
		'Aristodic.': 'Aristodicus',
		'Aristomen.': 'Aristomenes',
		'Aristonym.': 'Aristonymus',
		'Ar.': 'Aristophanes',
		'Aristoph.Boeot.': 'Aristophanes Boeotus',
		'Ar.Byz.': 'Aristophanes Byzantinus',
		'Arist.': 'Aristoteles',
		'Aristox.': 'Aristoxenus',
		'Ar.Did.': 'Arius Didymus',
		'Arr.': 'Arrianus',
		'Artem.': 'Artemidorus Daldianus',
		'Artemid.': 'Artemidorus Tarsensis',
		'Arus.Mess.': 'Arusianus Messius',
		'Ascens.Is.': 'Ascensio Isaiae',
		'Asclep.': 'Asclepiades',
		'Asclep.Jun.': 'Asclepiades Junior',
		'Asclep.Myrl.': 'Asclepiades Myrleanus',
		'Asclep.Tragil.': 'Asclepiades Tragilensis',
		'Ascl.': 'Asclepius',
		'Asp.': 'Aspasius',
		'Astramps.': 'Astrampsychus',
		'Astyd.': 'Astydamas',
		'Ath.': 'Athenaeus',
		'Ath.Mech.': 'Athenaeus',
		'Ath.Med.': 'Athenaeus',
		'Athenodor.Tars.': 'Athenodorus Tarsensis',
		'Atil.Fort.': 'Atilius Fortunatianus',
		'Attal.': 'Attalus',
		'Attic.': 'Atticus',
		'Aus.': 'Ausonius',
		'Autocr.': 'Autocrates',
		'Autol.': 'Autolycus',
		'Autom.': 'Automedon',
		'Axionic.': 'Axionicus',
		'Axiop.': 'Axiopistus',
		'Babr.': 'Babrius',
		'Bacch.': 'Bacchius',
		'B.': 'Bacchylides',
		'Balbill.': 'Balbilla',
		'Barb.': 'Barbucallos',
		'Bass.': 'Bassus, Lollius',
		'Bato Sinop.': 'Bato Sinopensis',
		'Batr.': 'Batrachomyomachia',
		'Beros.': 'Berosus',
		'Besant.': 'Besantinus',
		'Blaes.': 'Blaesus',
		'Boeth.': 'Boethus',
		'Boeth.Stoic.': 'Boethus Sidonius',
		'Brut.': 'Brutus',
		'Buther.': 'Butherus',
		'Cael.Aur.': 'Caelius Aurelianus',
		'Call.Com.': 'Callias',
		'Call.Hist.': 'Callias',
		'Callicrat.': 'Callicratidas',
		'Call.': 'Callimachus',
		'Callinic.Rh.': 'Callinicus',
		'Callin.': 'Callinus',
		'Callistr.Hist.': 'Callistratus',
		'Callistr.': 'Callistratus',
		'Callix.': 'Callixinus',
		'Canthar.': 'Cantharus',
		'Carc.': 'Carcinus',
		'Carm.Aur.': 'Carmen Aureum',
		'Carm.Pop.': 'Carmina Popularia',
		'Carneisc.': 'Carneiscus',
		'Carph.': 'Carphyllides',
		'Caryst.': 'Carystius',
		'Cass.': 'Cassius',
		'Cass.Fel.': 'Cassius Felix',
		'Cat.Cod.Astr.': 'Catalogus Codicum Astrologorum',
		'Ceb.': 'Cebes',
		'Cels.': 'Celsus',
		'Cephisod.': 'Cephisodorus',
		'Cerc.': 'Cercidas',
		'Cercop.': 'Cercopes',
		'Cereal.': 'Cerealius',
		'Certamen': 'Certamen Homeri et Hesiodi',
		'Chaerem.Hist.': 'Chaeremon',
		'Chaerem.': 'Chaeremon',
		'Chamael.': 'Chamaeleon',
		'Epist.Charact.': 'Characteres Epistolici',
		'Chares Iamb.': 'Chares',
		'Chares Trag.': 'Chares',
		'Chariclid.': 'Chariclides',
		'Charis.': 'Charisius',
		'Charixen.': 'Charixenes',
		'Charond.': 'Charondas',
		'Chionid.': 'Chionides',
		'Choeril.': 'Choerilus',
		'Choeril.Trag.': 'Choerilus',
		'Choerob.': 'Choeroboscus',
		'Chor.': 'Choricius',
		'Chrysipp.Stoic.': 'Chrysippus',
		'Chrysipp. Tyan.': 'Chrysippus Tyanensis',
		'Cic.': 'Cicero, M. Tullius',
		'Claudian.': 'Claudianus',
		'Claud.Iol.': 'Claudius Iolaus',
		'Cleaenet.': 'Cleaenetus',
		'Cleanth.Stoic.': 'Cleanthes',
		'Clearch.Com.': 'Clearchus',
		'Clearch.': 'Clearchus',
		'Clem.Al.': 'Clemens Alexandrinus',
		'Cleobul.': 'Cleobulus',
		'Cleom.': 'Cleomedes',
		'Cleon Sic.': 'Cleon Siculus',
		'Cleonid.': 'Cleonides',
		'Cleostrat.': 'Cleostratus',
		'Clidem. vel Clitodem.': 'Clidemus',
		'Clin.': 'Clinias',
		'Clitarch.': 'Clitarchus',
		'Clitom.': 'Clitomachus',
		'Cod.Just.': 'Codex Justinianus',
		'Cod.Theod.': 'Codex Theodosianus',
		'Colot.': 'Colotes',
		'Coluth.': 'Coluthus',
		'Com.Adesp.': 'Comica Adespota',
		'Corinn.': 'Corinna',
		'Corn.Long.': 'Cornelius Longus',
		'Corn.': 'Cornutus',
		'Corp.Herm.': 'Corpus Hermeticum',
		'Crater.': 'Craterus',
		'Crates Com.': 'Crates',
		'Crates Hist.': 'Crates',
		'Crates Theb.': 'Crates Thebanus',
		'Cratin.': 'Cratinus',
		'Cratin.Jun.': 'Cratinus Junior',
		'Cratipp.': 'Cratippus',
		'Crin.': 'Crinagoras',
		'Critias': 'Critias',
		'Crito Com.': 'Crito',
		'Crobyl.': 'Crobylus',
		'Ctes.': 'Ctesias',
		'Cyllen.': 'Cyllenius',
		'Cyran.': 'Cyranus',
		'Cypr.': 'Cypria',
		'Cyr.': 'Cyrilli Glossarium',
		'Cyrill.': 'Cyrillus',
		'Damag.': 'Damagetus',
		'Dam.': 'Damascius',
		'Damian.': 'Damianus',
		'Damoch.': 'Damocharis',
		'Damocr.': 'Damocrates',
		'Damocrit.': 'Damocritus',
		'Damostr.': 'Damostratus',
		'Damox.': 'Damoxenus',
		'Deioch.': 'Deiochus',
		'Demad.': 'Demades',
		'Demetr.': 'Demetrius',
		'Demetr.Com.Nov.': 'Demetrius',
		'Demetr.Com.Vet.': 'Demetrius',
		'Demetr.Apam.': 'Demetrius Apamensis',
		'Demetr.Lac.': 'Demetrius Lacon',
		'Dem.Phal.': 'Demetrius Phalereus',
		'Demetr.Troez.': 'Demetrius Troezenius',
		'Democh.': 'Demochares',
		'Democr.': 'Democritus',
		'Democr.Eph.': 'Democritus Ephesius',
		'Demod.': 'Demodocus',
		'Demonic.': 'Demonicus',
		'Demoph.': 'Demophilus',
		'D.': 'Demosthenes',
		'Dem.Bith.': 'Demosthenes Bithynus',
		'Dem.Ophth.': 'Demosthenes Ophthalmicus',
		'Dercyl.': 'Dercylus',
		'Dexipp.': 'Dexippus',
		'Diagor.': 'Diagoras',
		'Dialex.': 'Dialexeis',
		'Dicaearch.': 'Dicaearchus',
		'Dicaearch.Hist.': 'Dicaearchus',
		'Dicaeog.': 'Dicaeogenes',
		'Did.': 'Didymus',
		'Dieuch.': 'Dieuches',
		'Dieuchid.': 'Dieuchidas',
		'Dig.': 'Digesta',
		'Din.': 'Dinarchus',
		'Dinol.': 'Dinolochus',
		'D.C.': 'Dio Cassius',
		'D.Chr.': 'Dio Chrysostomus',
		'Diocl.': 'Diocles',
		'Diocl.Com.': 'Diocles',
		'Diocl.Fr.': 'Diocles',
		'Diod.Com.': 'Diodorus',
		'Diod.': 'Diodorus',
		'Diod.Rh.': 'Diodorus',
		'Diod.Ath.': 'Diodorus Atheniensis',
		'D.S.': 'Diodorus Siculus',
		'Diod.Tars.': 'Diodorus Tarsensis',
		'Diog.Apoll.': 'Diogenes Apolloniates',
		'Diog.Ath.': 'Diogenes Atheniensis',
		'Diog.Bab.Stoic.': 'Diogenes Babylonius',
		'Diog.': 'Diogenes Cynicus',
		'D.L.': 'Diogenes Laertius',
		'Diog.Oen.': 'Diogenes Oenoandensis',
		'Diog.Sinop.': 'Diogenes Sinopensis',
		'Diogenian.': 'Diogenianus',
		'Diogenian.Epicur.': 'Diogenianus Epicureus',
		'Diom.': 'Diomedes',
		'Dionys.Com.': 'Dionysius',
		'Dionys.': 'Dionysius',
		'Dionys.Trag.': 'Dionysius',
		'Dion.Byz.': 'Dionysius Byzantius',
		'Dion.Calliph.': 'Dionysius Calliphontis filius',
		'Dionys.Eleg.': 'Dionysius Chalcus',
		'D.H.': 'Dionysius Halicarnassensis',
		'Dionys.Stoic.': 'Dionysius Heracleota',
		'Dionys.Minor': 'Dionysius Minor',
		'D.P.': 'Dionysius Periegeta',
		'Dionys.Sam.': 'Dionysius Samius',
		'D.T.': 'Dionysius Thrax',
		'Diophan.': 'Diophanes',
		'Dioph.': 'Diophantus',
		'Diosc.': 'Dioscorides',
		'Diosc.Hist.': 'Dioscorides',
		'Dsc.': 'Dioscorides (Dioscurides)',
		'Diosc.Gloss.': 'Dioscorides Glossator',
		'Diotim.': 'Diotimus',
		'Diotog.': 'Diotogenes',
		'Diox.': 'Dioxippus',
		'Diph.': 'Diphilus',
		'Diph.Siph.': 'Diphilus Siphnius',
		'Diyll.': 'Diyllus',
		'Donat.': 'Donatus, Aelius',
		'Doroth.': 'Dorotheus',
		'Dosiad.': 'Dosiadas',
		'Dosiad.Hist.': 'Dosiades',
		'Dosith.': 'Dositheus',
		'Ecphantid.': 'Ecphantides',
		'Ecphant.': 'Ecphantus',
		'Eleg.Alex.Adesp.': 'Elegiaca Alexandrina Adespota',
		'Emp.': 'Empedocles',
		'1Enoch': 'Enoch',
		'Ephipp.': 'Ephippus',
		'Ephor.': 'Ephorus',
		'Epic.Alex.Adesp.': 'Epica Alexandrina Adespota',
		'Epich.': 'Epicharmus',
		'Epicr.': 'Epicrates',
		'Epict.': 'Epictetus',
		'Epicur.': 'Epicurus',
		'Epig.': 'Epigenes',
		'Epil.': 'Epilycus',
		'Epimenid.': 'Epimenides',
		'Epin.': 'Epinicus',
		'Erasistr.': 'Erasistratus',
		'Eratosth.': 'Eratosthenes',
		'Erinn.': 'Erinna',
		'Eriph.': 'Eriphus',
		'Erot.': 'Erotianus',
		'Eryc.': 'Erycius',
		'Etrusc.': 'Etruscus',
		'Et.Gen.': 'Etymologicum Genuinum',
		'Et.Gud.': 'Etymologicum Gudianum',
		'EM': 'Etymologicum Magnum',
		'Euang.': 'Euangelus',
		'Eubulid.': 'Eubulides',
		'Eub.': 'Eubulus',
		'Euc.': 'Euclides',
		'Eucrat.': 'Eucrates',
		'Eudem.': 'Eudemus',
		'Eudox.': 'Eudoxus',
		'Eudox.Com.': 'Eudoxus',
		'Eumel.': 'Eumelus',
		'Eun.': 'Eunapius',
		'Eunic.': 'Eunicus',
		'Euod.': 'Euodus',
		'Euph.': 'Euphorio',
		'Euphron.': 'Euphronius',
		'Eup.': 'Eupolis',
		'E.': 'Euripides',
		'Euryph.': 'Euryphamus',
		'Eus.Hist.': 'Eusebius',
		'Eus.': 'Eusebius Caesariensis',
		'Eus.Mynd.': 'Eusebius Myndius',
		'Eust.': 'Eustathius',
		'Eust.Epiph.': 'Eustathius Epiphaniensis',
		'Eustr.': 'Eustratius',
		'Euthycl.': 'Euthycles',
		'Eutoc.': 'Eutocius',
		'Eutolm.': 'Eutolmius',
		'Eutych.': 'Eutychianus',
		'Even.': 'Evenus',
		'Ezek.': 'Ezekiel',
		'Favorin.': 'Favorinus',
		'Fest.': 'Festus',
		'Firm.': 'Firmicus Maternus',
		'Fortunat.Rh.': 'Fortunatianus',
		'Gabriel.': 'Gabrielius',
		'Gaet.': 'Gaetulicus, Cn. Lentulus',
		'Gal.': 'Galenus',
		'Gaud.Harm.': 'Gaudentius',
		'Gell.': 'Gellius, Aulus',
		'Gem.': 'Geminus',
		'Gp.': 'Geoponica',
		'Germ.': 'Germanicus Caesar',
		'Glauc.': 'Glaucus',
		'Gloss.': 'Glossaria',
		'Gorg.': 'Gorgias',
		'Greg.Cor.': 'Gregorius Corinthius',
		'Greg.Cypr.': 'Gregorius Cyprius',
		'Hadr.Rh.': 'Hadrianus',
		'Hadr.': 'Hadrianus Imperator',
		'Harmod.': 'Harmodius',
		'Harp.': 'Harpocratio',
		'Harp.Astr.': 'Harpocratio',
		'Hecat.Abd.': 'Hecataeus Abderita',
		'Hecat.': 'Hecataeus Milesius',
		'Hedyl.': 'Hedylus',
		'Hegem.': 'Hegemon',
		'Hegesand.': 'Hegesander',
		'Hegesian.': 'Hegesianax',
		'Hegesipp.Com.': 'Hegesippus',
		'Hegesipp.': 'Hegesippus',
		'Hld.': 'Heliodorus',
		'Heliod.': 'Heliodorus',
		'Heliod.Hist.': 'Heliodorus',
		'Hellad.': 'Helladius',
		'Hellanic.': 'Hellanicus',
		'Hell.Oxy.': 'Hellenica Oxyrhynchia',
		'Hemerolog.Flor.': 'Hemerologium Florentinum',
		'Henioch.': 'Heniochus',
		'Heph.Astr.': 'Hephaestio',
		'Heph.': 'Hephaestio',
		'Heracl.': 'Heraclas',
		'Heraclid.Com.': 'Heraclides',
		'Heraclid.Cum.': 'Heraclides Cumaeus',
		'Heraclid.Lemb.': 'Heraclides Lembus',
		'Heraclid.Pont.': 'Heraclides Ponticus',
		'Heraclid.Sinop.': 'Heraclides Sinopensis',
		'Heraclid.': 'Heraclides Tarentinus',
		'Heraclit.': 'Heraclitus',
		'Herill.Stoic.': 'Herillus Carthaginiensis',
		'Herm.': 'Hermes Trismegistus',
		'Hermesian.': 'Hermesianax',
		'Herm.Hist.': 'Hermias',
		'Herm.Iamb.': 'Hermias',
		'Hermipp.': 'Hermippus',
		'Hermipp.Hist.': 'Hermippus',
		'Hermocl.': 'Hermocles',
		'Hermocr.': 'Hermocreon',
		'Hermod.': 'Hermodorus',
		'Hermog.': 'Hermogenes',
		'Herod.': 'Herodas',
		'Hdn.': 'Herodianus',
		'Herodor.': 'Herodorus',
		'Hdt.': 'Herodotus',
		'Herod.Med.': 'Herodotus',
		'Herophil.': 'Herophilus',
		'Hes.': 'Hesiodus',
		'Hsch.Mil.': 'Hesychius Milesius',
		'Hsch.': 'Hesychius',
		'Hices.': 'Hicesius',
		'Hierocl.': 'Hierocles',
		'Hierocl.Hist.': 'Hierocles',
		'Hieronym.Hist.': 'Hieronymus Cardianus',
		'Him.': 'Himerius',
		'Hipparch.': 'Hipparchus',
		'Hipparch.Com.': 'Hipparchus',
		'Hippias Erythr.': 'Hippias Erythraeus',
		'Hippiatr.': 'Hippiatrica',
		'Hp.': 'Hippocrates',
		'Hippod.': 'Hippodamus',
		'Hippol.': 'Hippolytus',
		'Hippon.': 'Hipponax',
		'Hist.Aug.': 'Historiae Augustae Scriptores',
		'Hom.': 'Homerus',
		'Honest.': 'Honestus',
		'Horap.': 'Horapollo',
		'h.Hom.': 'Hymni Homerici',
		'Hymn.Mag.': 'Hymni Magici',
		'Hymn.Id.Dact.': 'Hymnus ad Idaeos Dactylos',
		'Hymn.Is.': 'Hymnus ad Isim',
		'Hymn.Curet.': 'Hymnus Curetum',
		'Hyp.': 'Hyperides',
		'Hypsicl.': 'Hypsicles',
		'Iamb.': 'Iamblichus',
		'Iamb.Bab.': 'Iamblichus',
		'Ibyc.': 'Ibycus',
		'Il.': 'Ilias',
		'Il.Parv.': 'Ilias Parva',
		'Il.Pers.': 'Iliu Persis',
		'Iren.': 'Irenaeus',
		'Is.': 'Isaeus',
		'Isid.Trag.': 'Isidorus',
		'Isid.Aeg.': 'Isidorus Aegeates',
		'Isid.Char.': 'Isidorus Characenus',
		'Isid.': 'Isidorus Hispalensis',
		'Isig.': 'Isigonus',
		'Isoc.': 'Isocrates',
		'Isyll.': 'Isyllus',
		'Jo.Alex. vel Jo.Gramm.': 'Joannes Alexandrinus',
		'Jo.Diac.': 'Joannes Diaconus',
		'Jo.Gaz.': 'Joannes Gazaeus',
		'J.': 'Josephus',
		'Jul.': 'Julianus Imperator',
		'Jul. vel Jul.Aegypt.': 'Julianus Aegyptius',
		'Jul.Laod.': 'Julianus Laodicensis',
		'Junc.': 'Juncus',
		'Just.': 'Justinianus',
		'Juv.': 'Juvenalis, D. Junius',
		'Lamprocl.': 'Lamprocles',
		'Leo Phil.': 'Leo Philosophus',
		'Leon.': 'Leonidas',
		'Leonid.': 'Leonidas',
		'Leont.': 'Leontius',
		'Leont. in Arat.': 'Leontius',
		'Lesb.Gramm.': 'Lesbonax',
		'Lesb.Rh.': 'Lesbonax',
		'Leucipp.': 'Leucippus',
		'Lex.Mess.': 'Lexicon Messanense',
		'Lex.Rhet.': 'Lexicon Rhetoricum',
		'Lex.Rhet.Cant.': 'Lexicon Rhetoricum Cantabrigiense',
		'Lex.Sabb.': 'Lexicon Sabbaiticum',
		'Lex. de Spir.': 'Lexicon de Spiritu',
		'Lex.Vind.': 'Lexicon Vindobonense',
		'Lib.': 'Libanius',
		'Licymn.': 'Licymnius',
		'Limen.': 'Limenius',
		'Loll.': 'Lollius Bassus',
		'Longin.': 'Longinus',
		'Luc.': 'Lucianus',
		'Lucill.': 'Lucillius',
		'Lyc.': 'Lycophron',
		'Lycophronid.': 'Lycophronides',
		'Lycurg.': 'Lycurgus',
		'Lyd.': 'Lydus, Joannes Laurentius',
		'Lync.': 'Lynceus',
		'Lyr.Adesp.': 'Lyrica Adespota',
		'Lyr.Alex.Adesp.': 'Lyrica Alexandrina Adespota',
		'Lys.': 'Lysias',
		'Lysimachid.': 'Lysimachides',
		'Lysim.': 'Lysimachus',
		'Lysipp.': 'Lysippus',
		'Macar.': 'Macarius',
		'Maced.': 'Macedonius',
		'Macr.': 'Macrobius',
		'Maec.': 'Maecius',
		'Magn.': 'Magnes',
		'Magnus Hist.': 'Magnus',
		'Maiist.': 'Maiistas',
		'Malch.': 'Malchus',
		'Mamerc.': 'Mamercus',
		'Man.': 'Manetho',
		'Man.Hist.': 'Manetho',
		'Mantiss.Prov.': 'Mantissa Proverbiorum',
		'Marcellin.': 'Marcellinus',
		'Marc.Sid.': 'Marcellus Sidetes',
		'Marcian.': 'Marcianus',
		'M.Ant.': 'Marcus Antoninus',
		'Marc.Arg.': 'Marcus Argentarius',
		'Maria Alch.': 'Maria',
		'Marian.': 'Marianus',
		'Marin.': 'Marinus',
		'Mar.Vict.': 'Marius Victorinus',
		'Mart.': 'Martialis',
		'Mart.Cap.': 'Martianus Capella',
		'Max.': 'Maximus',
		'Max.Tyr.': 'Maximus Tyrius',
		'Megasth.': 'Megasthenes',
		'Melamp.': 'Melampus',
		'Melanipp.': 'Melanippides',
		'Melanth.Hist.': 'Melanthius',
		'Melanth.Trag.': 'Melanthius',
		'Mel.': 'Meleager',
		'Meliss.': 'Melissus',
		'Memn.': 'Memnon',
		'Menaechm.': 'Menaechmus',
		'Men.': 'Menander',
		'Men.Rh.': 'Menander',
		'Men.Eph.': 'Menander Ephesius',
		'Men.Prot.': 'Menander Protector',
		'Menecl.': 'Menecles Barcaeus',
		'Menecr.': 'Menecrates',
		'Menecr.Eph.': 'Menecrates Ephesius',
		'Menecr.Xanth.': 'Menecrates Xanthius',
		'Menemach.': 'Menemachus',
		'Menesth.': 'Menesthenes',
		'Menipp.': 'Menippus',
		'Menodot.': 'Menodotus Samius',
		'Mesom.': 'Mesomedes',
		'Metag.': 'Metagenes',
		'Metrod.': 'Metrodorus',
		'Metrod.Chius': 'Metrodorus Chius',
		'Metrod.Sceps.': 'Metrodorus Scepsius',
		'Mich.': 'Michael Ephesius',
		'Mimn.': 'Mimnermus',
		'Mimn.Trag.': 'Mimnermus',
		'Minuc.': 'Minucianus',
		'Mithr.': 'Mithradates',
		'Mnasalc.': 'Mnasalcas',
		'Mnesim.': 'Mnesimachus',
		'Mnesith.Ath.': 'Mnesitheus Atheniensis',
		'Mnesith.Cyz.': 'Mnesitheus Cyzicenus',
		'Moer.': 'Moeris',
		'MoschioTrag.': 'Moschio',
		'Mosch.': 'Moschus',
		'Muc.Scaev.': 'Mucius Scaevola',
		'Mund.': 'Mundus Munatius',
		'Musae.': 'Musaeus',
		'Music.': 'Musicius',
		'Muson.': 'Musonius',
		'Myrin.': 'Myrinus',
		'Myrsil.': 'Myrsilus',
		'Myrtil.': 'Myrtilus',
		'Naumach.': 'Naumachius',
		'Nausicr.': 'Nausicrates',
		'Nausiph.': 'Nausiphanes',
		'Neanth.': 'Neanthes',
		'Nearch.': 'Nearchus',
		'Nech.': 'Nechepso',
		'Neophr.': 'Neophron',
		'Neoptol.': 'Neoptolemus',
		'Nicaenet.': 'Nicaenetus',
		'Nic.': 'Nicander',
		'Nicarch.': 'Nicarchus',
		'Nicoch.': 'Nicochares',
		'Nicocl.': 'Nicocles',
		'Nicod.': 'Nicodemus',
		'Nicol.Com.': 'Nicolaus',
		'Nicol.': 'Nicolaus',
		'Nic.Dam.': 'Nicolaus Damascenus',
		'Nicom.Com.': 'Nicomachus',
		'Nicom.Trag.': 'Nicomachus',
		'Nicom.': 'Nicomachus Gerasenus',
		'Nicostr.Com.': 'Nicostratus',
		'Nicostr.': 'Nicostratus',
		'Nonn.': 'Nonnus',
		'Noss.': 'Nossis',
		'Numen.': 'Numenius Apamensis',
		'Nymphod.': 'Nymphodorus',
		'Ocell.': 'Ocellus Lucanus',
		'Od.': 'Odyssea',
		'Oenom.': 'Oenomaus',
		'Olymp.Alch.': 'Olympiodorus',
		'Olymp.Hist.': 'Olympiodorus',
		'Olymp.': 'Olympiodorus',
		'Onat.': 'Onatas',
		'Onos.': 'Onosander (Onasander)',
		'Ophel.': 'Ophelio',
		'Opp.': 'Oppianus',
		'Orac.Chald.': 'Oracula Chaldaica',
		'Orib.': 'Oribasius',
		'Orph.': 'Orphica',
		'Pae.Delph.': 'Paean Delphicus',
		'Pae.Erythr.': 'Paean Erythraeus',
		'Palaeph.': 'Palaephatus',
		'Palch.': 'Palchus',
		'Pall.': 'Palladas',
		'Pamphil.': 'Pamphilus',
		'Pancrat.': 'Pancrates',
		'Panyas.': 'Panyasis',
		'Papp.': 'Pappus',
		'Parm.': 'Parmenides',
		'Parmen.': 'Parmenio',
		'Parrhas.': 'Parrhasius',
		'Parth.': 'Parthenius',
		'Patrocl.': 'Patrocles Thurius',
		'Paul.Aeg.': 'Paulus Aegineta',
		'Paul.Al.': 'Paulus Alexandrinus',
		'Paul.Sil.': 'Paulus Silentiarius',
		'Paus.': 'Pausanias',
		'Paus.Dam.': 'Pausanias Damascenus',
		'Paus.Gr.': 'Pausanias Grammaticus',
		'Pediasim.': 'Pediasimus',
		'Pelag.Alch.': 'Pelagius',
		'Pempel.': 'Pempelus',
		'Perict.': 'Perictione',
		'Peripl.M.Rubr.': 'Periplus Maris Rubri',
		'Pers.Stoic.': 'Persaeus Citieus',
		'Pers.': 'Perses',
		'Petos.': 'Petosiris',
		'Petron.': 'Petronius',
		'Petr.Patr.': 'Petrus Patricius',
		'Phaedim.': 'Phaedimus',
		'Phaënn.': 'Phaënnus',
		'Phaest.': 'Phaestus',
		'Phal.': 'Phalaecus',
		'Phalar.': 'Phalaris',
		'Phan.': 'Phanias',
		'Phan.Hist.': 'Phanias',
		'Phanocl.': 'Phanocles',
		'Phanod.': 'Phanodemus',
		'Pherecr.': 'Pherecrates',
		'Pherecyd.': 'Pherecydes Lerius',
		'Pherecyd.Syr.': 'Pherecydes Syrius',
		'Philagr.': 'Philagrius',
		'Philem.': 'Philemo',
		'Philem.Jun.': 'Philemo Junior',
		'Philetaer.': 'Philetaerus',
		'Philet.': 'Philetas',
		'Philippid.': 'Philippides',
		'Philipp.Com.': 'Philippus',
		'Phil.': 'Philippus',
		'Philisc.Com.': 'Philiscus',
		'Philisc.Trag.': 'Philiscus',
		'Philist.': 'Philistus',
		'Ph.Epic.': 'Philo',
		'Ph.': 'Philo',
		'Ph.Bybl.': 'Philo Byblius',
		'Ph.Byz.': 'Philo Byzantius',
		'Ph.Tars.': 'Philo Tarsensis',
		'Philoch.': 'Philochorus',
		'Philocl.': 'Philocles',
		'Philod.Scarph.': 'Philodamus Scarpheus',
		'Phld.': 'Philodemus',
		'Philol.': 'Philolaus',
		'Philomnest.': 'Philomnestus',
		'Philonid.': 'Philonides',
		'Phlp.': 'Philoponus, Joannes',
		'Philosteph.Com.': 'Philostephanus',
		'Philosteph.Hist.': 'Philostephanus',
		'Philostr.': 'Philostratus',
		'Philostr.Jun.': 'Philostratus Junior',
		'Philox.': 'Philoxenus',
		'Philox.Gramm.': 'Philoxenus',
		'Philum.': 'Philumenus',
		'Philyll.': 'Philyllius',
		'Phint.': 'Phintys',
		'Phleg.': 'Phlegon Trallianus',
		'Phoc.': 'Phocylides',
		'Phoeb.': 'Phoebammon',
		'Phoenicid.': 'Phoenicides',
		'Phoen.': 'Phoenix',
		'Phot.': 'Photius',
		'Phryn.': 'Phrynichus',
		'Phryn.Com.': 'Phrynichus',
		'Phryn.Trag.': 'Phrynichus',
		'Phylarch.': 'Phylarchus',
		'Phylotim.': 'Phylotimus',
		'Pi.': 'Pindarus',
		'Pisand.': 'Pisander',
		'Pittac.': 'Pittacus',
		'Placit.': 'Placita Philosophorum',
		'Pl.Com.': 'Plato',
		'Pl.': 'Plato',
		'Pl.Jun.': 'Plato Junior',
		'Platon.': 'Platonius',
		'Plaut.': 'Plautus',
		'Plin.': 'Plinius',
		'Plot.': 'Plotinus',
		'Plu.': 'Plutarchus',
		'Poet. de herb.': 'Poeta',
		'Polem.Hist.': 'Polemo',
		'Polem.Phgn.': 'Polemo',
		'Polem.': 'Polemo Sophista',
		'Polioch.': 'Poliochus',
		'Poll.': 'Pollux',
		'Polyaen.': 'Polyaenus',
		'Plb.': 'Polybius',
		'Plb.Rh.': 'Polybius Sardianus',
		'Polycharm.': 'Polycharmus',
		'Polyclit.': 'Polyclitus',
		'Polycr.': 'Polycrates',
		'Polystr.': 'Polystratus',
		'Polyzel.': 'Polyzelus',
		'Pomp.': 'Pompeius',
		'Pomp.Mac.': 'Pompeius Macer',
		'Porph.': 'Porphyrius Tyrius',
		'Posidipp.': 'Posidippus',
		'Posidon.': 'Posidonius',
		'Pratin.': 'Pratinas',
		'Praxag.': 'Praxagoras',
		'Praxill.': 'Praxilla',
		'Priscian.': 'Priscianus',
		'Prisc.Lyd.': 'Priscianus Lydus',
		'Prisc.': 'Priscus',
		'Procl.': 'Proclus',
		'Procop.': 'Procopius Caesariensis',
		'Procop.Gaz.': 'Procopius Gazaeus',
		'Prodic.': 'Prodicus',
		'Promathid.': 'Promathidas',
		'Protag.': 'Protagoras',
		'Protagorid.': 'Protagoridas',
		'Proxen.': 'Proxenus',
		'Psalm.Solom.': 'Psalms of Solomon',
		'Ps.-Callisth.': 'Pseudo-Callisthenes',
		'Ps.-Phoc.': 'Pseudo-Phocylidea',
		'Ptol.': 'Ptolemaeus',
		'Ptol.Ascal.': 'Ptolemaeus Ascalonita',
		'Ptol.Chenn.': 'Ptolemaeus Chennos',
		'Ptol.Euerg.': 'Ptolemaeus Euergetes II',
		'Ptol.Megalop.': 'Ptolemaeus Megalopolitanus',
		'Pythaen.': 'Pythaenetus',
		'Pythag.': 'Pythagoras',
		'Pythag. Ep.': 'Pythagorae et Pythagoreorum Epistulae',
		'Pythocl.': 'Pythocles',
		'Quint.': 'Quintilianus',
		'Q.S.': 'Quintus Smyrnaeus',
		'Rh.': 'Rhetores Graeci',
		'Rhetor.': 'Rhetorius',
		'Rhian.': 'Rhianus',
		'Rhinth.': 'Rhinthon',
		'Rufin.': 'Rufinus',
		'Ruf.': 'Rufus',
		'Ruf.Rh.': 'Rufus',
		'Rutil.': 'Rutilius Lupus',
		'Tull.Sab.': 'Sabinus, Tullius',
		'Sacerd.': 'Sacerdos, Marius Plotius',
		'Sallust.': 'Sallustius',
		'Sannyr.': 'Sannyrio',
		'Sapph.': 'Sappho',
		'Satyr.': 'Satyrus',
		'Scol.': 'Scolia',
		'Scyl.': 'Scylax',
		'Scymn.': 'Scymnus',
		'Scythin.': 'Scythinus',
		'Secund.': 'Secundus',
		'Seleuc.': 'Seleucus',
		'Seleuc.Lyr.': 'Seleucus',
		'Semon.': 'Semonides',
		'Seren.': 'Serenus',
		'Serv.': 'Servius',
		'Sever.': 'Severus',
		'Sext.': 'Sextus',
		'S.E.': 'Sextus Empiricus',
		'Silen.': 'Silenus',
		'Simm.': 'Simmias',
		'Simon.': 'Simonides',
		'Simp.': 'Simplicius',
		'Simyl.': 'Simylus',
		'Socr.Arg.': 'Socrates Argivus',
		'Socr.Cous': 'Socrates Cous',
		'Socr.Rhod.': 'Socrates Rhodius',
		'Socr.': 'Socratis et Socraticorum Epistulae',
		'Sol.': 'Solon',
		'Sopat.': 'Sopater',
		'Sopat.Rh.': 'Sopater',
		'Sophil.': 'Sophilus',
		'S.': 'Sophocles',
		'Sophon': 'Sophonias',
		'Sophr.': 'Sophron',
		'Sor.': 'Soranus',
		'Sosib.': 'Sosibius',
		'Sosicr.': 'Sosicrates',
		'Sosicr.Hist.': 'Sosicrates',
		'Sosicr.Rhod.': 'Sosicrates Rhodius',
		'Sosip.': 'Sosipater',
		'Sosiph.': 'Sosiphanes',
		'Sosith.': 'Sositheus',
		'Sostrat.': 'Sostratus',
		'Sosyl.': 'Sosylus',
		'Sotad.Com.': 'Sotades',
		'Sotad.': 'Sotades',
		'Speus.': 'Speusippus',
		'Sphaer.Hist.': 'Sphaerus',
		'Sphaer.Stoic.': 'Sphaerus',
		'Stad.': 'Stadiasmus',
		'Staphyl.': 'Staphylus',
		'Stat.Flacc.': 'Statyllius Flaccus',
		'Steph.Com.': 'Stephanus',
		'Steph.': 'Stephanus',
		'St.Byz.': 'Stephanus Byzantius',
		'Stesich.': 'Stesichorus',
		'Stesimbr.': 'Stesimbrotus',
		'Sthenid.': 'Sthenidas',
		'Stob.': 'Stobaeus, Joannes',
		'Stoic.': 'Stoicorum Veterum Fragmenta',
		'Str.': 'Strabo',
		'Strato Com.': 'Strato',
		'Strat.': 'Strato',
		'Stratt.': 'Strattis',
		'Suet.': 'Suetonius',
		'Suid.': 'Suidas',
		'Sulp.Max.': 'Sulpicius Maximus',
		'Sus.': 'Susario',
		'Sm.': 'Symmachus',
		'Syn.Alch.': 'Synesius',
		'Syrian.': 'Syrianus',
		'Telecl.': 'Teleclides',
		'Telesill.': 'Telesilla',
		'Telest.': 'Telestes',
		'Ter.Maur.': 'Terentianus Maurus',
		'Ter.Scaur.': 'Terentius Scaurus',
		'Terp.': 'Terpander',
		'Thal.': 'Thales',
		'Theaet.': 'Theaetetus',
		'Theagen.': 'Theagenes',
		'Theag.': 'Theages',
		'Themiso Hist.': 'Themiso',
		'Them.': 'Themistius',
		'Themist.': 'Themistocles',
		'Theocl.': 'Theocles',
		'Theoc.': 'Theocritus',
		'Theodect.': 'Theodectes',
		'Theodorid.': 'Theodoridas',
		'Theod.': 'Theodorus',
		'Theodos.': 'Theodosius Alexandrinus',
		'Thd.': 'Theodotion',
		'Theognet.': 'Theognetus',
		'Thgn.': 'Theognis',
		'Thgn.Trag.': 'Theognis',
		'Thgn.Hist.': 'Theognis Rhodius',
		'Theognost.': 'Theognostus',
		'Theol.Ar.': 'Theologumena Arithmeticae',
		'Theolyt.': 'Theolytus',
		'Theon Gymn.': 'Theon Gymnasiarcha',
		'Theo Sm.': 'Theon Smyrnaeus',
		'Theoph.': 'Theophanes',
		'Theophil.': 'Theophilus',
		'Thphr.': 'Theophrastus',
		'Theopomp.Com.': 'Theopompus',
		'Theopomp.Hist.': 'Theopompus',
		'Theopomp.Coloph.': 'Theopompus Colophonius',
		'Thom.': 'Thomas',
		'Thom.Mag.': 'Thomas Magister',
		'Thrasym.': 'Thrasymachus',
		'Th.': 'Thucydides',
		'Thugen.': 'Thugenides',
		'Thyill.': 'Thyillus',
		'Thymocl.': 'Thymocles',
		'Tib.': 'Tiberius',
		'Tib.Ill.': 'Tiberius Illustrius',
		'Tim.': 'Timaeus',
		'Timae.': 'Timaeus',
		'Ti.Locr.': 'Timaeus Locrus',
		'Timag.': 'Timagenes',
		'Timocl.': 'Timocles',
		'Timocr.': 'Timocreon',
		'Timostr.': 'Timostratus',
		'Tim.Com.': 'Timotheus',
		'Tim.Gaz.': 'Timotheus Gazaeus',
		'Titanomach.': 'Titanomachia',
		'Trag.Adesp.': 'Tragica Adespota',
		'Trophil.': 'Trophilus',
		'Tryph.': 'Tryphiodorus',
		'Tull.Flacc.': 'Tullius Flaccus',
		'Tull.Gem.': 'Tullius Geminus',
		'Tull.Laur.': 'Tullius Laurea',
		'Tymn.': 'Tymnes',
		'Tyrt.': 'Tyrtaeus',
		'Tz.': 'Tzetzes, Joannes',
		'Ulp.': 'Ulpianus',
		'Uran.': 'Uranius',
		'Vel.Long.': 'Velius Longus',
		'Vett.Val.': 'Vettius Valens',
		'LXX': 'Vetus Testamentum Graece redditum',
		'Vit.Philonid.': 'Vita Philonidis Epicurei',
		'Vit.Hom.': 'Vitae Homeri',
		'Vitr.': 'Vitruvius',
		'Xanth.': 'Xanthus',
		'Xenag.': 'Xenagoras',
		'Xenarch.': 'Xenarchus',
		'Xenocl.': 'Xenocles',
		'Xenocr.': 'Xenocrates',
		'Xenoph.': 'Xenophanes',
		'X.': 'Xenophon',
		'X.Eph.': 'Xenophon Ephesius',
		'Zaleuc.': 'Zaleucus',
		'Zelot.': 'Zelotus',
		'ZenoStoic.': 'Zeno Citieus',
		'Zeno Eleat.': 'Zeno Eleaticus',
		'Zeno Tars.Stoic.': 'Zeno Tarsensis',
		'Zen.': 'Zenobius',
		'Zenod.': 'Zenodotus',
		'Zonae.': 'Zonaeus',
		'Zonar.': 'Zonaras',
		'Zon.': 'Zonas',
		'Zopyr.Hist.': 'Zopyrus',
		'Zopyr.': 'Zopyrus',
		'Zos.Alch.': 'Zosimus',
		'Zos.': 'Zosimus',
	}

	return authordict


def deabrevviatelatinauthors() -> Dict[str, str]:
	"""

	the latin dictionary xml does not help you to generate this dict

	:return:
	"""

	authordict = {
		'Amm.': 'Ammianus',
		'Anthol. Lat.': 'Latin Anthology',
		'App.': 'Apuleius',
		'Auct. Her.': 'Rhetorica ad Herennium',
		'Caes.': 'Caesar',
		'Cat.': 'Catullus',
		'Cassiod.': 'Cassiodorus',
		'Cels.': 'Celsus',
		'Charis.': 'Charisius',
		'Cic.': 'Cicero',
		'Col.': 'Columella',
		'Curt.': 'Quntus Curtius Rufus',
		'Dig.': 'Digest of Justinian',
		'Enn.': 'Ennius',
		'Eutr.': 'Eutropius',
		'Fest.': 'Festus',
		'Flor.': 'Florus',
		'Front.': 'Frontinus',
		'Gell.': 'Gellius',
		'Hirt.': 'Hirtius',
		'Hor.': 'Horace',
		'Hyg.': 'Hyginus',
		'Isid.': 'Isidore',
		'Just.': 'Justinian',
		'Juv.': 'Juvenal',
		'Lact.': 'Lactantius',
		'Liv.': 'Livy',
		'Luc.': 'Lucan',
		'Lucr.': 'Lucretius',
		'Macr.': 'Macrobius',
		'Mart.': 'Martial',
		'Nep.': 'Nepos',
		'Non.': 'Nonius',
		'Ov.': 'Ovid',
		'Pall.': 'Palladius',
		'Pers.': 'Persius',
		'Petr.': 'Petronius',
		'Phaedr.': 'Phaedrus',
		'Plaut.': 'Plautus',
		'Plin.': 'Pliny',
		'Prop.': 'Propertius',
		'Quint.': 'Quintilian',
		'Sall.': 'Sallust',
		'Sen.': 'Seneca',
		'Sil.': 'Silius Italicus',
		'Stat.': 'Statius',
		'Suet.': 'Suetonius',
		'Tac.': 'Tacitus',
		'Ter.': 'Terence',
		'Tert.': 'Tertullian',
		'Tib.': 'Tibullus',
		'Val. Fl.': 'Valerius Flaccus',
		'Val. Max.': 'Valerius Maxiumus',
		'Varr.': 'Varro',
		'Vell.': 'Velleius',
		'Verg.': 'Vergil',
		'Vitr.': 'Vitruvius',
		'Vulg.': 'Latin Vulgate Bible'
	}

	return authordict


def unpackcommonabbreviations(potentialabbreviaiton: str, furtherunpack: bool) -> str:
	"""
	turn an abbreviation into its headword: prid -> pridie

	it is important to avoid getting greedy in here: feed this via failed headword indices and the '•••unparsed•••'
	segment that follows

	a vector run has already turned 'm.' into Marcus via cleantext(), so it is safe to turn 'm' into 'mille'

	:param potentialabbreviaiton:
	:param furtherunpack:
	:return:
	"""

	abbreviations = {
		'sal': 'salutem',
		'prid': 'pridie',
		'kal': 'kalendae',
		'pl': 'plebis',
		'hs': 'sestertius',
		'sext': 'sextilis',
		'ian': 'ianuarius',
		'febr': 'februarius',
		'mart': 'martius',
		'apr': 'aprilis',
		'mai': 'maius',
		'quint': 'quintilis',
		'sept': 'september',
		'oct': 'october',
		'nou': 'nouembris',
		'dec': 'december',
		# 'iul': 'Julius',
		'imp': 'imperator',
		'design': 'designatus',
		'tr': 'tribunus',
		't': 'Titus',
		'cn': 'gnaeus',
		'gn': 'gnaeus',
		'q': 'quintus',
		's': 'sextus',
		'p': 'publius',
		'iii': 'tres',
		'iiii': 'quattor',
		'iu': 'quattor',
		'u': 'quinque',
		'ui': 'sex',
		'uii': 'septem',
		'uiii': 'octo',
		'uiiii': 'nouem',
		'ix': 'nouem',
		'x': 'decem',
		'xi': 'undecim',
		'xii': 'duodecim',
		'xiii': 'tredecim',
		'xiiii': 'quattuordecim',
		'xiu': 'quattuordecim',
		'xu': 'quindecim',
		'xui': 'sedecim',
		'xuii': 'septemdecim',
		'xuiii': 'dudeuiginti',
		'xix': 'unodeuiginti',
		'xx': 'uiginti',
		'xxx': 'triginta',
		'xl': 'quadraginta',
		# or is it 'lucius'...?
		# 'l': 'quinquaginta',
		'lx': 'sexaginta',
		'lxx': 'septuaginta',
		'lxxx': 'octoginta',
		'xc': 'nonaginta',
		'cc': 'ducenti',
		'ccc': 'trecenti',
		'cccc': 'quadrigenti',
		'cd': 'quadrigenti',
		'dc': 'sescenti',
		'dcc': 'septigenti',
		'dccc': 'octigenti',
		'cm': 'nongenti',
		'coss': 'consul',
		'cos': 'consul',
		'desig': 'designatus',
		'ser': 'seruius',
		'fab': 'fabius',
		'ap': 'appius',
		'sp': 'spurius',
		'leg': 'legatus',
		'ti': 'tiberius',
		'n.': 'numerius',
		'r': 'res',
		'f': 'filius',
		'mod': 'modius'
	}

	furtherabbreviations = {
		'm': 'mille',
		'c': 'centum',
		'l': 'quinquaginta',
	}

	# the following should be added to the db instead...
	morphsupplements = {
		# a candidate for addition to the dictionary...; cf. poëta
		'xuiri': 'decemuiri',
		'xuiros': 'decemviros',
		'xuiris': 'decemviris',
		# add to morph table... [index to galen helps you grab this]
		'τουτέϲτιν': 'τουτέϲτι',
		'κᾄν': 'ἄν',
		'κᾀν': 'ἄν',
		'κᾀπί': 'ἐπὶ',
		'κᾀκ': 'ἐκ',
		'κᾀξ': 'ἐκ',
		'κᾀνταῦθα': 'ἐνταῦθα',
		'κᾀπειδάν': 'ἐπειδάν',
		'κᾄπειθ': 'ἔπειτα',
		'κᾄπειτα': 'ἔπειτα',
		'κᾄπειτ': 'ἔπειτα',
		'κᾀγώ': 'ἐγώ',
	}

	abbreviations = {**abbreviations, **morphsupplements}

	if furtherunpack:
		abbreviations = {**abbreviations, **furtherabbreviations}

	try:
		word = abbreviations[potentialabbreviaiton]
	except KeyError:
		word = potentialabbreviaiton

	return word
