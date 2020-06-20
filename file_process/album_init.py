import os, re, shutil
from subprocess import Popen, PIPE
from . import ffmpeg
from . import cuereader
from . import shntool
from . import auto_decode
from .utils import get_ext

AUDIO_EXTS = ['wav', 'flac', 'alac', 'm4a', 'mp3', 'tak', 'tta', 'ape']

def safe_get(_dict, _key, _default = ''):
	if type(_dict) is dict and _key in _dict:
		return _dict[_key]
	return _default

def process_format(s):
	s = s[7:]
	re_hz = re.compile(r'\d+ Hz')
	re_kbs = re.compile(r'\d+ kb/s')
	#print(s)
	res = None
	if s[:3] == 'mp3':
		res = {'format': 'mp3', 'quality': 'lossy', 'quality_details': re_hz.findall(s)[0] + ' / ' + re_kbs.findall(s)[0].replace('/','p')}
	elif s[:3] == 'aac':
		res = {'format': 'aac', 'quality': 'lossy', 'quality_details': re_hz.findall(s)[0] + ' / ' + re_kbs.findall(s)[0].replace('/','p')}
	elif s[:3] == 'pcm' or s[:4] == 'flac' or s[:4] == 'alac' or s[:3] == 'tta' or s[:3] == 'tak' or s[:3] == 'ape':
		hz = re_hz.findall(s)[0]
		bit = 0
		if 's16' in s:
			bit = 16
		elif 's32 (24 bit)' in s:
			bit = 24
		elif 's32p (24 bit)' in s:
			bit = 24
		elif 's32' in s:
			bit = 32
		if s[:3] == 'pcm':
			ft = 'wav'
		elif s[:4] == 'flac':
			ft = 'flac'
		elif s[:4] == 'alac':
			ft = 'alac'
		elif s[:3] == 'tta':
			ft = 'tta'
		elif s[:3] == 'tak':
			ft = 'tak'
		elif s[:3] == 'ape':
			ft = 'ape'
		res = {'format': ft, 'quality': 'CD' if hz == '44100 Hz' and bit == 16 else 'Hi-Res', 'quality_details': hz + ' / ' + str(bit) + ' bit'}
	elif s[:3] == 'dsd':
		res = {'format': 'dsd', 'quality': 'DSD', 'quality_details': re_hz.findall(s)[0]}
	else:
		#raise Exception('Unsupported format: ' + s)
		res = {'format': '', 'quality': '', 'quality_details': ''}
	return res

def remove_ext(s):
	p = s.rfind('.')
	if p >= len(s) - 5:
		return s[:p]
	return s

def get_album_images(fo):
	if fo[-1] != '/':
		fo += '/'
	images = set()
	for i in os.listdir(fo):
		tf = ffmpeg.extract_image(fo + i)
		if tf is not None:
			images.add(tf)
	return list(images)

def get_album_info_separated(fo):
	if fo[-1] != '/':
		fo += '/'
	audios = []
	re_digitst = re.compile(r'^\d+(.|-| )')
	re_digit = re.compile(r'\d+')
	for i in os.listdir(fo):
		si = ffmpeg.probe(fo + i)
		if si is None: #not valid
			continue
		ts = {}
		if '/' in safe_get(si['metadata'], 'track'):
			t = si['metadata']['track'].split('/')
			ts['track'] = int(t[0])
			ts['tracktotal'] = int(t[1])
		else:
			ts['track'] = int(safe_get(si['metadata'], 'track', -1))
			ts['tracktotal'] = int(safe_get(si['metadata'], 'tracktotal', -1))
		ts['title'] = safe_get(si['metadata'], 'title')
		ts['artist'] = safe_get(si['metadata'], 'artist')
		ts['album'] = safe_get(si['metadata'], 'album')
		ts['filename'] = i
		if ts['title'] == '':
			if re_digitst.match(i) is None:
				ts['title'] = remove_ext(ts['filename']).strip()
			else:
				tmp = remove_ext(ts['filename'])
				ts['title'] = tmp[re_digitst.match(tmp).span()[1]:].strip()
		if ts['track'] == -1 and re_digitst.match(i) is not None:
			ts['track'] = int(re_digit.match(re_digitst.match(i).group()).group())
		is_audio = False
		for stream in si['streams']:
			if stream['type'][:5] == 'Audio':
				ft = process_format(stream['type'])
				is_audio = True
				ts.update(ft)
		ts['possible_eac'] = 'ExactAudioCopy' in str(si)
		#print(si)
		#print(ts)
		if is_audio:
			audios.append(ts)
	album = None
	if len(audios):
		album = {}
		for key in ['album', 'artist', 'format', 'quality', 'quality_details', 'tracktotal']:
			album[key] = audios[0][key] if all(audios[0][key] == i[key] for i in audios) else ''
		album['title'] = album['album']
		if album['tracktotal'] == '':
			album['tracktotal'] = -1
		album['possible_eac'] = all(i['possible_eac'] for i in audios)
		album['tracks'] = audios
		#print(album)
	return album

def get_album_info_fulldisc(fo, fn):
	if fo[-1] != '/':
		fo += '/'
	s = cuereader.read_cue(open(fn, 'rb').read())
	#print(s)
	file_format = {}
	res_tracks = []
	trackid = []
	for i in s['tracks']:
		trackid.append(i)
	trackid.sort()
	for i in trackid:
		si = s['tracks'][i].copy()
		si['track'] = i
		si['artist'] = safe_get(si, 'performer')
		si['filename'] = si['file'][0]
		ft = fo + si['file'][0]
		if ft not in file_format:
			if os.path.exists(ft):
				ftx = ft
			else:
				ftx = None
				ftt = remove_ext(si['file'][0])
				exts = AUDIO_EXTS
				for ftx_ in os.listdir(fo):
					for ext in exts:
						if ftx_.lower() == (ftt + '.' + ext).lower():
							ftx = ftx_
				if ftx is None:
					return None
				ftx = fo + ftx
			fp = ffmpeg.probe(ftx)
			if fp is None:
				#file_format[ft] = {}
				return None
			else:
				for stream in fp['streams']:
					if stream['type'][:5] == 'Audio':
						file_format[ft] = process_format(stream['type'])
				if ft not in file_format:
					return None
		si.update(file_format[ft])
		res_tracks.append(si)
	if len(res_tracks) == 0:
		return None
	res = {'title': safe_get(s, 'title'), 'artist': safe_get(s, 'performer')}
	for key in ['format', 'quality', 'quality_details']:
		res[key] = res_tracks[0][key] if all(res_tracks[0][key] == i[key] for i in res_tracks) else ''
	#print(res)
	#print(res_tracks)
	res['tracks'] = res_tracks
	res['possible_eac'] = 'ExactAudioCopy' in str(res)
	return res

def get_album_info(fo):
	if fo[-1] != '/':
		fo += '/'
	tres = None
	for i in os.listdir(fo):
		if i[-3:].lower() == 'cue':
			tres = get_album_info_fulldisc(fo, fo + i)
			if tres is not None:
				break
	if tres is None:
		tres = get_album_info_separated(fo)
	if tres is None:
		return None
	#print(tres)
	res = {}
	res_tracks = []
	for key in ['title', 'artist', 'format', 'quality', 'quality_details', 'possible_eac']:
		res[key] = safe_get(tres, key)
	for track in tres['tracks']:
		nt = {}
		for key in ['track', 'title', 'artist', 'format', 'quality', 'quality_details', 'filename', 'start_time', 'end_time']:
			nt[key] = safe_get(track, key, -1 if key == 'track' else '')
		res_tracks.append(nt)
	#print(res)
	#print(res_tracks)
	res['tracks'] = res_tracks
	return res

def get_album_logs(fo):
	if fo[-1] != '/':
		fo += '/'
	res = []
	for i in os.listdir(fo):
		if i[-3:].lower() == 'log':
			fs = open(fo + i, 'rb').read()
			if fs[:3] == b'EAC' or b'Exact Audio Copy' in fs or 'Exact Audio Copy' in auto_decode.decode(fs):
				res.append(fs)
	return res

def tstr_to_time(s, _def = 0):
	if s == '': return _def
	s = list(map(int, s.split(':')))
	re = 0
	for i in range(len(s) - 1):
		re = re * 60 + s[i]
	re = re * 75 + s[-1]
	return re

def time_to_tstr(s):
	a = s % 75; s //= 75
	b = s % 60; s //= 60
	return '%02d:%02d:%02d' % (s, b, a)

def convert_album_to_flac(album, fo, dstfo):
	if fo[-1] != '/':
		fo += '/'
	if dstfo[-1] != '/':
		dstfo += '/'
	#print(album)
	file_occur = {}
	file_format = {}
	INF = 10 ** 10
	for tid in range(len(album['tracks'])):
		track = album['tracks'][tid]
		if track['filename'] not in file_occur:
			file_occur[track['filename']] = []
			file_format[track['filename']] = track['format']
		t = (tid, tstr_to_time(track['start_time']), tstr_to_time(track['end_time'], INF))
		file_occur[track['filename']].append(t)
	#print(file_occur)
	for fr in file_occur:
		fp = file_occur[fr]
		fp.sort(key = lambda x: x[1])
		if os.path.exists(fo + fr):
			f = fr
		else:
			f = None
			for fu in os.listdir(fo):
				if remove_ext(fu) == remove_ext(fr) and get_ext(fu) in AUDIO_EXTS: # fix for weird cue that filename is xxx.wav but not the real one
					f = fu
					break
		if file_format[fr] == 'flac' and len(fp) == 1 and fp[0][1] == 0 and fp[0][2] == INF:
			shutil.copyfile(fo + f, dstfo + '%d.flac' % fp[0][0])
			continue
		if len(fp) == 1 and fp[0][1] == 0 and fp[0][2] == INF:
			ffmpeg.convert(fo + f, dstfo + '%d.flac' % fp[0][0])
			p = Popen(['metaflac', '--dont-use-padding', '--remove-all', dstfo + '%d.flac' % fp[0][0]], stdout = PIPE, stderr = PIPE)
			so, er = p.communicate()
			continue
		if file_format[fr] == 'flac' or file_format[fr] == 'wav':
			rfn = fo + f
		else:
			rfn = dstfo + remove_ext(f) + '.wav'
			ffmpeg.convert(fo + f, rfn)
		while len(fp):
			fpc = []
			fpn = []
			lst = 0
			for i in fp:
				if i[1] >= lst:
					fpc.append(i)
					lst = i[2]
				else:
					fpn.append(i)
			fp = fpn
			#print(fpc)
			cue_data = 'FILE "%s" WAVE\n' % rfn.replace('"', '\\"')
			cnt = 0
			tcnt = 0
			lst = 0
			for i in fpc:
				if lst != i[1]:
					cnt += 1
					tcnt += 1
					cue_data += 'TRACK %02d AUDIO\nTITLE throw_%d\nINDEX 01 %s\n' % (cnt, tcnt, time_to_tstr(lst))
				cnt += 1
				cue_data += 'TRACK %02d AUDIO\nTITLE %d\nINDEX 01 %s\n' % (cnt, i[0], time_to_tstr(i[1]))
				lst = i[2]
			if lst != INF:
				cnt += 1
				tcnt += 1
				cue_data += 'TRACK %02d AUDIO\nTITLE throw_%d\nINDEX 01 %s\n' % (cnt, tcnt, time_to_tstr(lst))
			#print(cue_data)
			open(dstfo + 'test.cue', 'w', encoding = 'utf-8').write(cue_data)
			shntool.split_cue(dstfo + 'test.cue', rfn, dstfo)
	re_flac = re.compile(r'^\d+.flac')
	for i in os.listdir(dstfo):
		if re_flac.match(i) is None:
			os.remove(dstfo + i)
