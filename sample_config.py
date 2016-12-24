DEBUG=False
SECRET_KEY = 'yourkeyhereitshouldbelongandlooklikecryptographicgobbledygook'

# a read-only db user is highly recommended; write access means inviting a world of hurt
DBUSER = 'hippa_rd'
DBHOST = '127.0.0.1'
DBPORT = 5432
DBNAME = 'hipparchiaDB'
DBPASS = 'yourpassheretrytomakeitstrongplease'
LDICT = 'latin_dictionary'
GDICT = 'greek_dictionary'

# pick a number based on your cpu cores: on an 8 core machine diminishing returns kick in between 3 and 4 as the bottleneck shifts elsewhere
# on a one-core virtual machine extra workers don't do much good and tend to just get in the way of one another: '1' seems to be best
# a high number on a fast machine risks lockout from the db as too many requests come too fast: will need to recalibrate the default commit count if you go over 5
# your mileage will indeed vary, but N > cores*(.5) is probably not going to do much good.
WORKERS = 3

DEFAULTEARLIESTDATE = '-850'
DEFAULTLATESTDATE = '1500'
DEFAULTSORTORDER = 'shortname'
DEFAULTGREEKCORPUSVALUE = 'yes'
DEFAULTLATINCORPUSVALUE = 'no'
DEFAULTINSCRIPTIONCORPUSVALUE = 'no'
DEFAULTPAPYRUSCORPUSVALUE = 'no'