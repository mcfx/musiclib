from functools import wraps
from flask import request, jsonify
import traceback
import config

def auth_required(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		token = request.cookies.get('token')
		if token != config.ACCESS_TOKEN:
			return jsonify({'status': False, 'auth_req' : True})
		return func(*args, **kwargs)
	return wrapper

def skip_error(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except:
			traceback.print_exc()
			return jsonify({'status': False})
	return wrapper

def skip_error_and_auth(func):
	return skip_error(auth_required(func))