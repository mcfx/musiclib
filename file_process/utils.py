import os

def get_ext(s, _def):
	p = s.rfind('.')
	if p >= len(s) - 5:
		return s[p + 1:]
	return _def

def clear_cache(fo):
	if fo[-1] != '/':
		fo += '/'
	for i in os.listdir(fo):
		os.remove(fo + i)