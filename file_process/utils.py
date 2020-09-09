import os, shutil


def get_ext(s, _def=''):
	p = s.rfind('.')
	if p >= len(s) - 5:
		return s[p + 1:]
	return _def


def clear_cache(fo, clear_folders=False):
	if fo[-1] != '/':
		fo += '/'
	for i in os.listdir(fo):
		if os.path.isfile(fo + i):
			os.remove(fo + i)
		elif clear_folders:
			shutil.rmtree(fo + i)


def purify_filename(s):
	r = ''
	for i in s:
		if ord(i) >= 32 and i not in '<>/\\:*?"|':
			r += i
	return r
