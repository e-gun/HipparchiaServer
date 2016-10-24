# https://arusahni.net/blog/2014/03/flask-nocache.html
from flask import make_response
from functools import wraps, update_wrapper
from datetime import datetime


def nocache(view):
	@wraps(view)
	def no_cache(*args, **kwargs):
		response = make_response(view(*args, **kwargs))
		response.headers['Last-Modified'] = datetime.now()
		response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
		response.headers['Pragma'] = 'no-cache'
		response.headers['Expires'] = '-1'
		return response
	
	return update_wrapper(no_cache, view)


# @hipparchia.after_request
# def add_header(response):
# 	"""
# 	http://stackoverflow.com/questions/28627324/disable-cache-on-a-specific-page-using-flask#28627512
# 	https://arusahni.net/blog/2014/03/flask-nocache.html
# 	:param response:
# 	:return:
# 	"""
# 	response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
# 	if ('Cache-Control' not in response.headers):
# 		response.headers['Cache-Control'] = 'public, max-age=600'
# 	return response


# @hipparchia.route('/progress')
# @nocache
# def progressreport():
# 	pass