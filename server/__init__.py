from flask import Flask

hipparchia = Flask(__name__)
hipparchia.config.from_object('config')

from server import views
