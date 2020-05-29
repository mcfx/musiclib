import re, json, time, random, traceback
from copy import deepcopy
from datetime import timedelta
from functools import reduce

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_
import sqlalchemy.types as types
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema, auto_field
from marshmallow import pre_load, fields

import config

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = config.SQL_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

with app.app_context():
	from file_utils import get_ext, purify_filename
	from file_process import auto_decode, musicbrainz
	from file_add import add_file_task, get_file_queue, start_process_thread
	from flask_wrappers import skip_error_and_auth
	import files
	
	start_process_thread(app)

class CompactArray(types.TypeDecorator):
	impl = types.TEXT
	
	def __init__(self, basetype = str):
		types.TypeDecorator.__init__(self)
		self.basetype = basetype
	
	def process_bind_param(self, value, dialect):
		return ','.join(map(str, value))
	
	def process_result_value(self, value, dialect):
		if len(value) == 0: return []
		return list(map(self.basetype, value.split(',')))

class JsonString(types.TypeDecorator): # do not use JSON of sqlalchemy for convenience
	impl = types.TEXT
	
	def process_bind_param(self, value, dialect):
		return json.dumps(value, separators = (',', ':'))
	
	def process_result_value(self, value, dialect):
		return json.loads(value)

class Album(db.Model):
	__tablename__ = 'albums'
	id = db.Column(db.Integer, primary_key = True, autoincrement = True)
	title = db.Column(db.String)
	release_date = db.Column(db.Date)
	artist = db.Column(db.String)
	format = db.Column(db.String(20))
	quality = db.Column(db.String(20))
	quality_details = db.Column(db.String(50))
	source = db.Column(db.String)
	file_source = db.Column(db.String)
	trusted = db.Column(db.Boolean)
	log_files = db.Column(CompactArray)
	cover_files = db.Column(CompactArray)
	comments = db.Column(db.String)
	extra_data = db.Column(JsonString)

class Song(db.Model):
	__tablename__ = 'songs'
	id = db.Column(db.Integer, primary_key = True, autoincrement = True)
	album_id = db.Column(db.Integer)
	track = db.Column(db.Integer)
	title = db.Column(db.String)
	artist = db.Column(db.String)
	duration = db.Column(db.String(8))
	format = db.Column(db.String(20))
	quality = db.Column(db.String(20))
	quality_details = db.Column(db.String(50))
	file = db.Column(db.String)
	file_flac = db.Column(db.String)
	extra_data = db.Column(JsonString)

class Scan(db.Model):
	__tablename__ = 'scans'
	id = db.Column(db.Integer, primary_key = True, autoincrement = True)
	name = db.Column(db.String)
	album_id = db.Column(db.Integer)
	files = db.Column(db.String)

class Playlist(db.Model):
	__tablename__ = 'playlists'
	id = db.Column(db.Integer, primary_key = True, autoincrement = True)
	title = db.Column(db.String)
	description = db.Column(db.String)
	tracklist = db.Column(CompactArray(int))
	last_update = db.Column(db.Integer)

class AlbumFile(db.Model):
	__tablename__ = 'albums_files'
	id = db.Column(db.Integer, primary_key = True, autoincrement = True)
	album_id = db.Column(db.Integer)
	name = db.Column(db.String)
	file = db.Column(db.String)

class KeepSameSerialization(fields.Field):
	def _serialize(self, value, attr, obj):
		return value
	def _deserialize(self, value, attr, obj):
		return value

class AlbumSchema(SQLAlchemySchema):
	class Meta:
		model = Album
		load_instance = True
	id = auto_field()
	title = auto_field()
	release_date = auto_field()
	artist = auto_field()
	format = auto_field()
	quality = auto_field()
	quality_details = auto_field()
	source = auto_field()
	file_source = auto_field()
	trusted = auto_field()
	log_files = KeepSameSerialization()
	cover_files = KeepSameSerialization()
	comments = auto_field()

class SongSchema(SQLAlchemySchema):
	class Meta:
		model = Song
		load_instance = True
	id = auto_field()
	album_id = auto_field()
	track = auto_field()
	title = auto_field()
	artist = auto_field()
	duration = auto_field()
	format = auto_field()
	quality = auto_field()
	quality_details = auto_field()

album_schema = AlbumSchema()
song_schema = SongSchema()

@app.route('/')
def send_index():
	if config.DEBUG:
		return open('static/index.html').read().replace('app.js', 'app.js?' + str(random.random())).replace('app.css', 'app.css?' + str(random.random())).replace('config.js', 'config.js?' + str(random.random()))
	return app.send_static_file('index.html') # should be handled by nginx

@app.route('/api/album/search')
@skip_error_and_auth
def search_album():
	query = request.values.get('query')
	page = int(request.values.get('page'))
	if page < 0 or page > config.PAGE_MAX:
		return jsonify({'status': False})
	reqs = [Album.title, Album.artist, Album.comments]
	req = reduce(or_, map(lambda y: reduce(and_, map(lambda x: y.like('%' + x + '%'), query.split()), True), reqs))
	count = Album.query.filter(req).count()
	albums = Album.query.filter(req).order_by(Album.id.desc()).all()[page * config.RESULTS_PER_PAGE: (page + 1) * config.RESULTS_PER_PAGE]
	res = []
	for album in albums:
		tmp = album_schema.dump(album)
		tmp.pop('cover_files')
		res.append(tmp)
	return jsonify({'status': True, 'data': {'count': count, 'albums': res}})

@app.route('/api/album/<id>/info')
@skip_error_and_auth
def get_album_info(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	res = album_schema.dump(album)
	res['cover_files'] = list(map(lambda x: files.get_link(x, 'cover.jpg'), res['cover_files']))
	songs = Song.query.filter(Song.album_id == id).order_by(Song.track).all()
	res['songs'] = []
	for i in songs:
		res['songs'].append(song_schema.dump(i))
		if request.values.get('extra_data') is not None:
			res['songs'][-1]['extra_data'] = i.extra_data
	if request.values.get('extra_data') is not None:
		res['extra_data'] = album.extra_data
	return jsonify({'status': True, 'data': res})

@app.route('/api/album/<id>/update', methods=['POST'])
@skip_error_and_auth
def update_album_info(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	s = request.json
	try:
		album.title = s['title']
		album.release_date = s['release_date']
		album.artist = s['artist']
		album.source = s['source']
		album.file_source = s['file_source']
		album.comments = s['comments']
		album.trusted = int(s['trusted'])
		for t in s['songs']:
			song = Song.query.filter(Song.id == t['id']).order_by(Song.track).one()
			song.track = t['track']
			song.title = t['title']
			song.artist = t['artist']
	except Exception as e:
		traceback.print_exc()
		return jsonify({'status': False})
	db.session.commit()
	return jsonify({'status': True})

@app.route('/api/album/<id>/update_covers', methods=['POST'])
@skip_error_and_auth
def update_album_covers(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	nc = list(map(lambda x: files.get_hash_by_link(x), request.json['covers']))
	if type(nc) is not list or sorted(nc) != sorted(album.cover_files):
		return jsonify({'status': False})
	album.cover_files = nc
	db.session.commit()
	return jsonify({'status': True})

@app.route('/api/album/<id>/scans')
@skip_error_and_auth
def get_album_scans(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	scans = Scan.query.filter(Scan.album_id == id).all()
	res = []
	for scan in scans:
		imgs = json.loads(scan.files)
		tmp = []
		for fn, thb, src in imgs:
			tmp.append([fn, files.get_link(thb, fn + '.thumb.png'), files.get_link(src, fn)])
		res.append({'id': scan.id, 'packname': scan.name, 'files': tmp})
	return jsonify({'status': True, 'data': res})

@app.route('/api/album/<id>/files')
@skip_error_and_auth
def get_album_files(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	fs = AlbumFile.query.filter(AlbumFile.album_id == id).order_by(AlbumFile.id).all()
	res = []
	for fl in fs:
		res.append({'id': fl.id, 'name': fl.name, 'file': fl.file})
	return jsonify({'status': True, 'data': res})

@app.route('/api/album/<id>/gen_flac', methods = ['POST'])
@skip_error_and_auth
def album_gen_flac(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	if album.format != 'flac':
		return jsonify({'status': False})
	songs = Song.query.filter(Song.album_id == id).order_by(Song.track).all()
	album.tracks = songs
	add_file_task({'type': 'album_gen_flac', 'album_id': id}, album)
	return jsonify({'status': True})

@app.route('/api/album/<id>/match_acoustid', methods = ['POST'])
@skip_error_and_auth
def album_match_acoustid(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	songs = Song.query.filter(Song.album_id == id).order_by(Song.track).all()
	album.tracks = songs
	add_file_task({'type': 'album_acoustid', 'album_id': id}, album)
	return jsonify({'status': True})

@app.route('/api/album/<id>/set_musicbrainz_id', methods = ['POST'])
@skip_error_and_auth
def album_set_musicbrainz_id(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	mid = request.json['mid']
	add_file_task({'type': 'album_musicbrainz_id', 'album_id': id, 'mid': mid})
	return jsonify({'status': True})

@app.route('/api/album/<id>/cuetools_verify', methods = ['POST'])
@skip_error_and_auth
def album_cuetools_verify(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	if album.format != 'flac':
		return jsonify({'status': False})
	songs = Song.query.filter(Song.album_id == id).order_by(Song.track).all()
	album.tracks = songs
	add_file_task({'type': 'album_cuetools', 'album_id': id}, album)
	return jsonify({'status': True})

@app.route('/api/album/<id>/apply_musicbrainz', methods = ['POST'])
@skip_error_and_auth
def apply_musicbrainz_to_album(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	mid = request.json['mid']
	mc = None
	for mc_ in album.extra_data['musicbrainz']:
		if mc_['id'] == mid:
			mc = mc_
			break
	if mc is None:
		return jsonify({'status': False})
	album.title = mc['title']
	album.release_date = mc['date']
	album.artist = musicbrainz.get_artist_name(mc['artist-credit'])
	songs = Song.query.filter(Song.album_id == id).order_by(Song.track).all()
	mt = mc['media'][0]['tracks']
	for i in range(min(len(songs), len(mt))):
		songs[i].title = mt[i]['title']
		songs[i].artist = musicbrainz.get_artist_name(mt[i]['artist-credit'])
	db.session.commit()
	return jsonify({'status': True})

@app.route('/api/album/<id>/apply_musicbrainz_cover', methods = ['POST'])
@skip_error_and_auth
def apply_musicbrainz_cover_to_album(id):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False})
	mid = request.json['mid']
	add_file_task({'type': 'album_musicbrainz_cover', 'album_id': id, 'mid': mid})
	return jsonify({'status': True})

@app.route('/api/album/<id>/upload/<tp>', methods = ['POST'])
@skip_error_and_auth
def album_upload_files(id, tp):
	id = int(id)
	album = Album.query.filter(Album.id == id).first()
	if album is None:
		return jsonify({'status': False, 'msg': 'Invalid album id'})
	if tp not in ['scan', 'log', 'other', 'cover']:
		return jsonify({'status': False, 'msg': 'Upload type error'})
	if 'file' not in request.files:
		return jsonify({'status': False, 'msg': 'File not found'})
	file = request.files['file']
	if file.filename == '':
		return jsonify({'status': False, 'msg': 'Filename cannot be empty'})
	if get_ext(file.filename) not in config.TRUSTED_EXTENSIONS:
		return jsonify({'status': False, 'msg': 'Invalid extension'})
	ofn = file.filename
	fn = str(int(time.time() * 1000)) + '%06x' % random.randint(0, 2 ** 24 - 1) + purify_filename(ofn)
	fp = config.TEMP_PATH.rstrip('\\').rstrip('/') + '/upload/' + fn
	file.save(fp)
	add_file_task({'type': 'album_' + tp, 'album_id': id, 'path': fp, 'filename': ofn})
	return jsonify({'status': True, 'msg': 'Added to queue'})

@app.route('/api/album/upload', methods = ['POST'])
@skip_error_and_auth
def album_upload():
	if 'file' not in request.files:
		return jsonify({'status': False, 'msg': 'File not found'})
	file = request.files['file']
	if file.filename == '':
		return jsonify({'status': False, 'msg': 'Filename cannot be empty'})
	if get_ext(file.filename) not in config.TRUSTED_EXTENSIONS:
		return jsonify({'status': False, 'msg': 'Invalid extension'})
	ofn = file.filename
	fn = str(int(time.time() * 1000)) + '%06x' % random.randint(0, 2 ** 24 - 1) + purify_filename(ofn)
	fp = config.TEMP_PATH.rstrip('\\').rstrip('/') + '/upload/' + fn
	file.save(fp)
	add_file_task({'type': 'new_album', 'path': fp, 'filename': ofn})
	return jsonify({'status': True, 'msg': 'Added to queue'})

@app.route('/api/song/search')
@skip_error_and_auth
def search_song():
	query = request.values.get('query')
	page = int(request.values.get('page'))
	if page < 0 or page > config.PAGE_MAX:
		return jsonify({'status': False})
	reqs = [Song.title, Song.artist]
	req = reduce(or_, map(lambda y: reduce(and_, map(lambda x: y.like('%' + x + '%'), query.split()), True), reqs))
	count = Song.query.filter(req).count()
	songs = Song.query.filter(req).order_by(Song.id.desc())[page * config.RESULTS_PER_PAGE: (page + 1) * config.RESULTS_PER_PAGE]
	res = []
	for song in songs:
		album = Album.query.filter(Album.id == song.album_id).one()
		tmp = song_schema.dump(song)
		tmp['album_title'] = album.title
		res.append(tmp)
	return jsonify({'status': True, 'data': {'count': count, 'songs': res}})

@app.route('/api/song/<id>/link')
@skip_error_and_auth
def get_song_link(id):
	id = int(id)
	song = Song.query.filter(Song.id == id).first()
	if song is None:
		return jsonify({'status': False})
	fn = song.artist + ' - ' + song.title
	data = {}
	for key in ['file', 'file_flac']:
		mfn = song.__dict__[key]
		data[key] = files.get_link(mfn, fn + '.' + get_ext(mfn, ''), 86400) if mfn else ''
	return jsonify({'status': True, 'data': data})

@app.route('/api/song/<id>/apply_musicbrainz', methods = ['POST'])
@skip_error_and_auth
def apply_musicbrainz_to_song(id):
	id = int(id)
	song = Song.query.filter(Song.id == id).first()
	if song is None:
		return jsonify({'status': False})
	mid = request.json['mid']
	for mc in song.extra_data['musicbrainz']:
		if mc['id'] == mid:
			song.title = mc['title']
			song.artist = musicbrainz.get_artist_name(mc['artist-credit'])
			db.session.commit()
			return jsonify({'status': True})
	return jsonify({'status': False})

@app.route('/api/songs/<ids>/play')
@skip_error_and_auth
def get_songs_play(ids, full = False):
	ids = list(map(int, ids.split(',')))
	res_files = []
	covers = []
	titles = []
	artists = []
	for id in ids:
		song = Song.query.filter(Song.id == id).first()
		if song is None:
			return jsonify({'status': False})
		fn = song.artist + ' - ' + song.title
		link = ''
		for key in ['file_flac', 'file']:
			mfn = song.__dict__[key]
			if mfn:
				link = files.get_link(mfn, fn + '.' + get_ext(mfn, ''), 86400)
				break
		res_files.append(link)
		album = Album.query.filter(Album.id == song.album_id).one()
		if len(album.cover_files):
			covers.append(files.get_link(album.cover_files[0], 'cover.jpg'))
		else:
			covers.append('')
		if full:
			titles.append(song.title)
			artists.append(song.artist)
	res = {'files': res_files, 'covers': covers}
	if full:
		res['titles'] = titles
		res['artists'] = artists
	return jsonify({'status': True, 'data': res})

@app.route('/api/songs/<ids>/play/full')
@skip_error_and_auth
def get_songs_play_full(ids):
	return get_songs_play(ids, True)

@app.route('/api/scan/<id>/update_name', methods = ['POST'])
@skip_error_and_auth
def update_scan_name(id):
	scan = Scan.query.filter(Scan.id == id).first()
	if scan is None:
		return jsonify({'status': False})
	scan.name = request.json['name']
	db.session.commit()
	return jsonify({'status': True})

@app.route('/api/log/<id>')
@skip_error_and_auth
def get_log(id):
	if re.match(r'^[a-zA-Z0-9\._]+$', id) is None:
		return jsonify({'status': False})
	log = auto_decode.decode(files.get_content(id))
	return jsonify({'status': True, 'data': log})

@app.route('/api/log/<id>/download')
@skip_error_and_auth
def get_log_download(id):
	if re.match(r'^[a-zA-Z0-9\._]+$', id) is None:
		return jsonify({'status': False})
	return jsonify({'status': True, 'data': files.get_link(id, 'album.log')})

@app.route('/api/playlist/search')
@skip_error_and_auth
def search_playlist():
	query = request.values.get('query')
	page = int(request.values.get('page'))
	if page < 0 or page > config.PAGE_MAX:
		return jsonify({'status': False})
	req_title = reduce(and_, map(lambda x: Playlist.title.like('%' + x + '%'), query.split()), True)
	req_description = reduce(and_, map(lambda x: Playlist.description.like('%' + x + '%'), query.split()), True)
	count = Playlist.query.filter(or_(req_title, req_description)).count()
	playlists = Playlist.query.filter(or_(req_title, req_description)).order_by(Playlist.last_update.desc())[page * config.RESULTS_PER_PAGE: (page + 1) * config.RESULTS_PER_PAGE]
	res = list(map(lambda x: {'id': x.id, 'title': x.title, 'description': x.description, 'len_tracks': len(x.tracklist)}, playlists))
	return jsonify({'status': True, 'data': {'count': count, 'playlists': res}})

@app.route('/api/playlist/<id>/info')
@skip_error_and_auth
def get_playlist_info(id, page = -1):
	id = int(id)
	playlist = Playlist.query.filter(Playlist.id == id).first()
	if playlist is None:
		return jsonify({'status': False})
	res = {'id': playlist.id, 'title': playlist.title, 'description': playlist.description, 'tracks': [], 'count_tracks': len(playlist.tracklist), 'full_tracklist': playlist.tracklist}
	if page >= 0:
		sp = playlist.tracklist[page * config.RESULTS_PER_PAGE: (page + 1) * config.RESULTS_PER_PAGE]
	else:
		sp = playlist.tracklist
	for i in sp:
		song = Song.query.filter(Song.id == i).first()
		if song is None:
			return jsonify({'status': False})
		album = Album.query.filter(Album.id == song.album_id).one()
		song = song_schema.dump(song)
		song['album_title'] = album.title
		res['tracks'].append(song)
	return jsonify({'status': True, 'data': res})

@app.route('/api/playlist/<id>/info/page/<page>')
@skip_error_and_auth
def get_playlist_info_page(id, page):
	page = int(page)
	if page < 0 or page > config.PAGE_MAX:
		return jsonify({'status': False})
	return get_playlist_info(id, page)

@app.route('/api/playlist/<id>/addtrack', methods = ['POST'])
@skip_error_and_auth
def playlist_addtrack(id):
	id = int(id)
	playlist = Playlist.query.filter(Playlist.id == id).first()
	if playlist is None:
		return jsonify({'status': False})
	s = request.json
	if 'song_id' not in s:
		return jsonify({'status': False})
	sid = s['song_id']
	if Song.query.filter(Song.id == sid).first() is None:
		return jsonify({'status': False})
	playlist.tracklist = playlist.tracklist + [sid]
	playlist.last_update = int(time.time())
	db.session.commit()
	return jsonify({'status': True})

@app.route('/api/playlist/<id>/update', methods = ['POST'])
@skip_error_and_auth
def update_playlist_info(id):
	id = int(id)
	playlist = Playlist.query.filter(Playlist.id == id).first()
	if playlist is None:
		return jsonify({'status': False})
	s = request.json
	try:
		playlist.title = s['title']
		playlist.description = s['description']
		tr = [] if s['tracks']=='' else list(map(int, s['tracks'].split(',')))
		for i in tr:
			song = Song.query.filter(Song.id == i).first()
			if song is None:
				return jsonify({'status': False})
		playlist.tracklist = tr
	except Exception as e:
		traceback.print_exc()
		return jsonify({'status': False})
	playlist.last_update = int(time.time())
	db.session.commit()
	return jsonify({'status': True})

@app.route('/api/playlist/create', methods = ['POST'])
@skip_error_and_auth
def create_playlist():
	s = request.json
	if 'title' not in s:
		return jsonify({'status': False})
	title = s['title']
	pl = Playlist(title = title, description = '', tracklist = '', last_update = 0)
	db.session.add(pl)
	db.session.commit()
	return jsonify({'status': True, 'id': pl.id})

@app.route('/api/queue')
@skip_error_and_auth
def get_queue_stat():
	return jsonify(get_file_queue())

if __name__ == '__main__':
	app.run(host = '127.0.0.1', port = 1928, debug = config.DEBUG)