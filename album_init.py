import os, io, hashlib
from file_process.album_init import get_album_info, get_album_images, get_album_logs, convert_album_to_flac, tstr_to_time
from file_process.ffmpeg import probe
import minio_wrapper as mi
import db
import config

def get_ext(s, _def):
	p = s.rfind('.')
	if p >= len(s) - 5:
		return s[p + 1:]
	return _def

def get_duration(s):
	t = s['metadata']['duration']
	if '.' in t:
		t = t[:t.find('.')]
	if t[:3] == '00:':
		t = t[3:]
	return t

def album_init(fo):
	if fo[-1] != '/':
		fo += '/'
	album = get_album_info(fo)
	if album is None:
		return False
	full_single = True
	for track in album['tracks']:
		if tstr_to_time(track['start_time'], 0) != 0 or track['end_time'] != '':
			full_lossy_single = False
	#print(full_lossy_single)
	if full_single and (album['quality'] in ['DSD', 'lossy']):
		for track in album['tracks']:
			track['filename'] = fo + track['filename']
	else:
		dstfo = config.TEMP_PATH
		if dstfo[-1] != '/':
			dstfo += '/'
		for i in os.listdir(dstfo):
			os.remove(dstfo + i)
		convert_album_to_flac(album, fo, dstfo)
		for trackid in range(len(album['tracks'])):
			track = album['tracks'][trackid]
			track['filename'] = dstfo + str(trackid) + '.flac'
			track['format'] = 'flac'
		album['format'] = 'flac'
	covers = get_album_images(fo)
	logs = get_album_logs(fo)
	td = {}
	td['comments'] = "It's possibly from EAC" if album['possible_eac'] else ''
	for key in ['title', 'artist', 'format', 'quality', 'quality_details']:
		td[key] = album[key]
	sql = "insert into albums(title, artist, format, quality, quality_details, source, file_source, log_files, cover_files, comments) "\
		"values (%(title)s, %(artist)s, %(format)s, %(quality)s, %(quality_details)s, '', '', '', '', %(comments)s)"
	albumid = db.execute(sql, td).lastrowid
	#print(albumid)
	covers_ids = []
	for cover in covers:
		fn = str(albumid) + '_' + hashlib.md5(cover).hexdigest()[:10] + '.jpg'
		fc = io.BytesIO(cover)
		mi.put_object('covers/' + fn, fc, len(cover))
		covers_ids.append(fn)
	logs_ids = []
	for log in logs:
		fn = str(albumid) + '_' + hashlib.md5(log).hexdigest()[:10] + '.log'
		fc = io.BytesIO(log)
		mi.put_object('logs/' + fn, fc, len(log))
		logs_ids.append(fn)
	db.execute("update albums set log_files = %(lf)s, cover_files = %(cf)s where id = %(id)s", {'id': albumid, 'lf': ','.join(logs_ids), 'cf': ','.join(covers_ids)})
	for track in album['tracks']:
		sql = "insert into songs(album_id, track, title, artist, duration, format, quality, quality_details, file, file_flac) "\
			"values (%(album_id)s, %(track)s, %(title)s, %(artist)s, %(duration)s, %(format)s, %(quality)s, %(quality_details)s, '', '')"
		td = {}
		for key in ['track', 'title', 'artist', 'format', 'quality', 'quality_details']:
			td[key] = track[key]
		td['album_id'] = albumid
		td['duration'] = get_duration(probe(track['filename']))
		songid = db.execute(sql, td).lastrowid
		fn = str(songid) + '.' + get_ext(track['filename'], track['format'])
		mi.fput_object('songs/' + fn, track['filename'])
		db.execute("update songs set file = %(fn)s where id = %(id)s", {'id': songid, 'fn': fn})
	return True
