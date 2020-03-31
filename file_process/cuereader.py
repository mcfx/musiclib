from . import auto_decode

def unescape(s):
	if s[0] == '"':
		return s[1:-1]
	return s

def read_cue(s):
	s = auto_decode.decode(s)
	#print(s)
	s = list(filter(len, s.replace('\r', '').split('\n')))
	g_vars = {}
	cur_file = ('', '')
	tracks = {}
	cur = g_vars
	lst = g_vars
	for _si in s:
		so, sa = _si.strip().split(' ', 1)
		if so == 'REM':
			x, y = sa.split(' ', 1)
			cur[x.lower()] = unescape(y)
		elif so == 'PERFORMER':
			cur['performer'] = unescape(sa)
		elif so == 'SONGWRITER':
			cur['songwriter'] = unescape(sa)
		elif so == 'TITLE':
			cur['title'] = unescape(sa)
		elif so == 'ISRC':
			cur['isrc'] = unescape(sa)
		elif so == 'CATALOG':
			cur['catalog'] = unescape(sa)
		elif so == 'FILE':
			p = sa.rfind(' ')
			if p == -1 or '"' in sa[p:]:
				cur_file = (unescape(p), '')
			else:
				cur_file = (unescape(sa[:p]), unescape(sa[p + 1:]))
		elif so == 'TRACK':
			sa = sa.split(' ')
			lst = cur
			cur = {'file': cur_file}
			tracks[int(sa[0])] = cur
			if len(sa) > 1:
				cur['type'] = sa[1].lower()
		elif so == 'INDEX':
			x, y = sa.split(' ')
			if y == '00:00:00':
				pass
			elif int(x) == 0:
				#lst['end_time'] = y
				pass #not compatible with exists software
			elif int(x) == 1:
				cur['start_time'] = y
				if 'end_time' not in lst:
					lst['end_time'] = y
		elif so == 'FLAGS':
			pass
		else:
			pass
	g_vars['tracks'] = tracks
	return g_vars
