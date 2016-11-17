DEBUG=False
SECRET_KEY = 'yourkeyhere'

# a read-only db user is highly recommended
DBUSER = 'hippa_rd'
DBHOST = '127.0.0.1'
DBPORT = 5432
DBNAME = 'hipparchiaDB'
DBPASS = 'yourpasshere'
LDICT = 'latin_dictionary'
GDICT = 'greek_dictionary'
# pick a number based on your cpu cores: on an 8 core machine diminishing returns kick in between 3 and 4 as the bottleneck shifts elsewhere
# on a one-core virtual machine extra workers don't do much good and tend to just get in the way of one another: '1' seems to be best
# a high number on a fast machine risks lockout from the db as too many requests come too fast: will need to recalibrate the default commit count if you go over 5
# your mileage will indeed vary
WORKERS = 3


DEFAULTEARLIESTDATE = '-850'
DEFAULTLATESTDATE = '1500'
DEFAULTCORPUS = 'G'
DEFAULTSORTORDER = 'shortname'