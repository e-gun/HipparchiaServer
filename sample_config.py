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
WORKERS = 4