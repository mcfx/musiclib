import os, io, json, hashlib
from file_process.album_init import get_album_info, get_album_images, get_album_logs, convert_album_to_flac, tstr_to_time
from file_process.ffmpeg import probe
from file_process.scans import get_converted_images
from file_utils import get_ext, clear_cache
import files
import db
import config

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
	if full_single and (album['quality'] in ['DSD', 'lossy']):
		for track in album['tracks']:
			track['filename'] = fo + track['filename']
	else:
		dstfo = config.TEMP_PATH
		if dstfo[-1] != '/':
			dstfo += '/'
		clear_cache(config.TEMP_PATH)
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
	covers_ids = []
	for cover in covers:
		covers_ids.append(files.add_bytes(cover, 'jpg'))
	logs_ids = []
	for log in logs:
		logs_ids.append(files.add_bytes(log, 'log'))
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
		fn = files.add_file(track['filename'])
		db.execute("update songs set file = %(fn)s where id = %(id)s", {'id': songid, 'fn': fn})
	return True

def add_scans(fo, packname, album_id):
	if packname == '':
		packname = fo[fo.rfind('/') + 1:]
	clear_cache(config.TEMP_PATH)
	imgs = get_converted_images(fo, config.TEMP_PATH)
	img_files = []
	for fn, src, thb in imgs:
		srcf = files.add_file(src)
		thbf = files.add_file(thb)
		img_files.append([fn, thbf, srcf])
	imgfs = json.dumps(img_files)
	db.execute("insert into scans(name, album_id, files) values (%(name)s, %(album_id)s, %(files)s)", {'name': packname, 'album_id': album_id, 'files': imgfs})
	return True
