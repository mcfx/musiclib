from subprocess import Popen, PIPE
from io import BytesIO
from PIL import Image

def get_space_cnt(s):
	t = 0
	while t < len(s) and s[t] == ' ':
		t += 1
	return (t, s[t:])

def probe(fn):
	p = Popen(['ffprobe', '-i', fn], stdout = PIPE, stderr = PIPE)
	so, er = p.communicate()
	s = er[er.find(b'Input #0'):]
	if len(s) <= 1:
		return None
	s = s.decode('utf-8').replace('\r', '').split('\n')
	s2 = []
	for i in s:
		if len(i.strip()):
			s2.append(get_space_cnt(i))
	assert s2[0][0] == 0
	assert s2[1][0] == 2
	res1 = {}
	i = 1
	if s2[i][1] == 'Metadata:':
		i += 1
		while i < len(s2) and s2[i][0] == 4:
			t = s2[i][1].split(':', 1)
			res1[t[0].strip().lower()] = t[1].strip()
			i += 1
			while i < len(s2) and s2[i][0] > 4: # throw cue sheet and all multi line metadata
				i += 1
	assert s2[i][0] == 2
	for j in s2[i][1].split(','):
		t = j.split(':', 1)
		res1[t[0].strip().lower()] = t[1].strip()
	i += 1
	lst = {}
	res_cap = []
	res_str = []
	while i < len(s2):
		if s2[i][1] != 'Metadata:':
			t = s2[i][1].split(':', 2)
			if len(t) < 3: t.append('') # fix for strange files
			if t[0] == 'Stream #0':
				res_str.append({'id': t[1], 'type': t[2].strip()})
				lst = res_str[-1]
			else:
				res_cap.append({'id': t[1], 'info': t[2].strip()})
				lst = res_cap[-1]
			i += 1
			continue
		lst['metadata'] = {}
		i += 1
		while i < len(s2) and s2[i][0] == 6:
			t = s2[i][1].split(':', 1)
			lst['metadata'][t[0].strip().lower()] = t[1].strip()
			i += 1
	res = {'metadata': res1, 'streams': res_str, 'chapters': res_cap}
	#print(res)
	return res

def extract_image(fn):
	# mjpeg singlejpeg
	p = Popen(['ffmpeg', '-i', fn, '-vcodec', 'copy', '-an', '-f', 'singlejpeg', '-'], stdout = PIPE, stderr = PIPE)
	so, er = p.communicate()
	if len(so):
		f = BytesIO(so)
		try:
			Image.open(f)
		except: # not a real image
			return None
		return so
	return None

def convert(src, dst):
	cmd = ['ffmpeg', '-y', '-i', src, dst]
	p = Popen(cmd, stdout = PIPE, stderr = PIPE)
	so, er = p.communicate()
	if er != b'':
		raise Exception(er.decode())
