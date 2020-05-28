import os, io, json, time, shutil, hashlib, datetime, traceback
import subprocess
from copy import deepcopy

from werkzeug.utils import secure_filename

from threading import Thread, RLock
from file_process.album_init import get_album_info, get_album_images, get_album_logs, convert_album_to_flac, tstr_to_time
from file_process.ffmpeg import probe
from file_process.scans import get_converted_images
from file_process.flac import gen_flac
from file_process.musicbrainz import match_albums, mb_get_release
from file_process import cuetools
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
		return False, None
	full_single = True
	for track in album['tracks']:
		if tstr_to_time(track['start_time'], 0) != 0 or track['end_time'] != '':
			full_lossy_single = False
	no_flac = album['quality'] in ['DSD', 'lossy']
	no_flac = no_flac or '32 bit' in album['quality_details']
	if full_single and no_flac:
		for track in album['tracks']:
			track['filename'] = fo + track['filename']
	else:
		dstfo = config.TEMP_PATH
		if dstfo[-1] != '/':
			dstfo += '/'
		dstfo += '/album_init/'
		clear_cache(dstfo)
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
	return True, albumid

def add_scans(fo, packname, album_id):
	if packname == '':
		packname = fo.rstrip('/').rsplit('/', 1)[1]
	dstfo = config.TEMP_PATH
	if dstfo[-1] != '/':
		dstfo += '/'
	dstfo += '/scans/'
	clear_cache(dstfo)
	imgs = get_converted_images(fo, dstfo)
	img_files = []
	for fn, src, thb in imgs:
		srcf = files.add_file(src)
		thbf = files.add_file(thb)
		img_files.append([fn, thbf, srcf])
	imgfs = json.dumps(img_files)
	db.execute("insert into scans(name, album_id, files) values (%(name)s, %(album_id)s, %(files)s)", {'name': packname, 'album_id': album_id, 'files': imgfs})
	return True

def gen_final_flac(album):
	dstfo = config.TEMP_PATH
	if dstfo[-1] != '/':
		dstfo += '/'
	dstfo += '/gen_flac/'
	clear_cache(dstfo)
	_files = []
	for i in range(len(album.tracks)):
		track = album.tracks[i]
		if track.file_flac:
			files.del_file(track.file_flac)
		fn = dstfo + str(i) + '.flac'
		open(fn, 'wb').write(files.get_content(track.file))
		_files.append(fn)
	if len(album.cover_files):
		cover = files.get_content(album.cover_files[0])
	else:
		cover = None
	gen_flac(album, _files, cover)
	for i in range(len(album.tracks)):
		fn = dstfo + str(i) + '.flac'
		tf = files.add_file(fn)
		db.execute("update songs set file_flac = %(fn)s where id = %(id)s", {'id': album.tracks[i].id, 'fn': tf})

def update_extra(table, id, key, value):
	old = db.select_first("select extra_data from " + table + " where id = %(id)s", {'id': id})[0]
	cur = json.loads(old)
	cur[key] = value
	cur = json.dumps(cur, separators = (',', ':'))
	db.execute("update " + table + " set extra_data = %(ed)s where id = %(id)s", {'id': id, 'ed': cur})

def match_acoustid(album):
	paths = []
	for i in range(len(album.tracks)):
		track = album.tracks[i]
		paths.append(files.get_path(track.file))
	resa, res = match_albums(paths)
	update_extra('albums', album.id, 'musicbrainz', resa)
	for i in range(len(album.tracks)):
		track = album.tracks[i]
		update_extra('songs', track.id, 'musicbrainz', res[i])

def cuetools_verify(album):
	paths = []
	ids = []
	for i in range(len(album.tracks)):
		track = album.tracks[i]
		if track.file_flac:
			paths.append(files.get_path(track.file_flac))
		else:
			paths.append(files.get_path(track.file))
			ids.append(track.track)
	if ids == []:
		ids = None
	res = cuetools.verify(paths, ids)
	update_extra('albums', album.id, 'cuetools', res)

ft_lock = RLock()
ft_queue = []
ft_queue_ext = []
ft_done = []
ft_current_task = None

def add_file_task(task, task_ext = None):
	ft_lock.acquire()
	ft_queue.append(task)
	ft_queue_ext.append(task_ext)
	ft_lock.release()

def get_file_queue():
	ft_lock.acquire()
	res = deepcopy(ft_queue)
	resd = ft_done[::-1]
	ft_lock.release()
	return {'queue': res, 'done': resd, 'current_task': ft_current_task}

def decompress(archive_path, decompress_path, password = None):
	cmd = ['7z', 'x', archive_path, '-o' + decompress_path]
	if password is not None:
		cmd.append('-p' + password)
	res = []
	p = subprocess.Popen(cmd, stderr = subprocess.PIPE, stdout = subprocess.PIPE)
	def work():
		stdout, stderr = p.communicate()
		res.append((p.returncode, stdout, stderr))
	thread = Thread(target = work)
	thread.start()
	thread.join(600) # enough to decompress most files (60s too short for some files)
	if thread.is_alive():
		p.terminate()
		return False, b'Timeout while running 7z'
	return res[0][0] == 0, res[0][2].decode('utf-8', 'ignore')

def guess_pw(path):
	tmp = path.rsplit('.', 1)[0]
	if 'pw_' not in tmp:
		return None
	return tmp.rsplit('pw_', 1)[1]

def detect_path(path):
	t = os.listdir(path)
	if len(t) == 1 and os.path.isdir(path + '/' + t[0]):
		return path + '/' + t[0]
	return path

def try_decompress(archive_path):
	depath = config.TEMP_PATH
	if depath[-1] != '/':
		depath += '/'
	depath += 'decompress'
	clear_cache(depath, True)
	res, err = decompress(archive_path, depath, '') # None pw causes infinite running
	if res: return True, err, detect_path(depath)
	pw = guess_pw(archive_path)
	if pw is None: return res, err, ''
	clear_cache(depath, True)
	res2, err2 = decompress(archive_path, depath, pw)
	if res2: return True, err2, detect_path(depath)
	return res, err, ''

def backup_album_file(path, album_id, filename):
	cur_date = datetime.datetime.now().strftime('%Y%m%d')
	npath = cur_date + '/' + secure_filename(path.rsplit('/', 1)[1])
	fo = config.BACKUP_PATH.rstrip('\\').rstrip('/') + '/' + cur_date
	if not os.path.exists(fo):
		os.mkdir(fo)
	shutil.move(path, config.BACKUP_PATH.rstrip('\\').rstrip('/') + '/' + npath)
	db.execute("insert into albums_files(album_id, name, file) values(%(album_id)s, %(name)s, %(file)s)", {'album_id': album_id, 'name': filename, 'file': npath})

def file_process_thread():
	global ft_queue, ft_current_task, ft_done
	while True:
		ft_lock.acquire()
		if len(ft_queue):
			task = ft_queue[0]
			task_ext = ft_queue_ext[0]
			ft_queue.pop(0)
			ft_queue_ext.pop(0)
		else:
			task = None
		ft_current_task = deepcopy(task)
		tm = int(time.time())
		nd = []
		for i in ft_done:
			if tm - i['done_time'] < config.TASK_CLEAR_TIME:
				nd.append(i)
		ft_done = nd
		ft_lock.release()
		if task is None:
			time.sleep(0.5)
			continue
		try:
			db.renew()
			if task['type'] in ['album_scan', 'album_log', 'album_other', 'album_cover']:
				path = task['path']
				task_result = None
				if task['type'] == 'album_log':
					log_files = db.select_first("select log_files from albums where id = %(id)s", {'id': task['album_id']})[0]
					log_new = files.add_file(path)
					log_files = (log_files + ',' + log_new).strip(',')
					db.execute("update albums set log_files = %(lf)s where id = %(id)s", {'id': task['album_id'], 'lf': log_files})
				elif task['type'] == 'album_scan':
					res, err, depath = try_decompress(path)
					if res == False:
						task_result = {'status': False, 'error': err}
					else:
						add_scans(depath, '', task['album_id'])
						task_result = {'status': True}
				elif task['type'] == 'album_cover':
					cover_files = db.select_first("select cover_files from albums where id = %(id)s", {'id': task['album_id']})[0]
					cover_new = files.add_file(path)
					cover_files = (cover_files + ',' + cover_new).strip(',')
					db.execute("update albums set cover_files = %(cf)s where id = %(id)s", {'id': task['album_id'], 'cf': cover_files})
					task_result = {'status': True}
				else:
					task_result = {'status': True}
				backup_album_file(path, task['album_id'], task['filename'])
				ft_lock.acquire()
				ft_done.append({'task': task, 'result': task_result, 'done_time': int(time.time())})
				ft_lock.release()
			elif task['type'] == 'new_album':
				path = task['path']
				task_result = None
				res, err, depath = try_decompress(path)
				if res == False:
					task_result = {'status': False, 'error': err}
				else:
					res, albumid = album_init(depath)
					if res:
						task_result = {'status': True}
						backup_album_file(path, albumid, task['filename'])
					else:
						task_result = {'status': False, 'error': 'Failed to get album info'}
				ft_lock.acquire()
				ft_done.append({'task': task, 'result': task_result, 'done_time': int(time.time())})
				ft_lock.release()
			elif task['type'] == 'album_gen_flac':
				gen_final_flac(task_ext)
				ft_lock.acquire()
				ft_done.append({'task': task, 'result': {'status': True}, 'done_time': int(time.time())})
				ft_lock.release()
			elif task['type'] == 'album_acoustid':
				match_acoustid(task_ext)
				ft_lock.acquire()
				ft_done.append({'task': task, 'result': {'status': True}, 'done_time': int(time.time())})
				ft_lock.release()
			elif task['type'] == 'album_musicbrainz_id':
				update_extra('albums', task['album_id'], 'musicbrainz', [mb_get_release(task['mid'])])
				ft_lock.acquire()
				ft_done.append({'task': task, 'result': {'status': True}, 'done_time': int(time.time())})
				ft_lock.release()
			elif task['type'] == 'album_cuetools':
				cuetools_verify(task_ext)
				ft_lock.acquire()
				ft_done.append({'task': task, 'result': {'status': True}, 'done_time': int(time.time())})
				ft_lock.release()
		except:
			err = traceback.format_exc()
			ft_lock.acquire()
			ft_done.append({'task': task, 'result': {'status': False, 'error': err}, 'done_time': int(time.time())})
			ft_lock.release()

def start_process_thread(app):
	def run():
		with app.app_context():
			file_process_thread()
	fo = config.TEMP_PATH
	if fo[-1] != '/':
		fo += '/'
	def md(s):
		if not os.path.exists(fo + s):
			os.mkdir(fo + s)
	md('album_init')
	md('decompress')
	md('gen_flac')
	md('scans')
	md('upload')
	md('verify')
	ft = Thread(target = run)
	ft.setDaemon(True)
	ft.start()
