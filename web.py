import re, json, random, traceback
from copy import deepcopy
from datetime import timedelta

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy.types as types
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema, auto_field
from marshmallow import pre_load, fields

import config

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQL_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

with app.app_context():
	from file_utils import get_ext
	from file_process import auto_decode
	import files

class CompactArray(types.TypeDecorator):
	impl = types.TEXT
	
	def process_bind_param(self, value, dialect):
		return ','.join(value)
	
	def process_result_value(self, value, dialect):
		if len(value) == 0: return []
		return value.split(',')

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

class Scan(db.Model):
	__tablename__ = 'scans'
	id = db.Column(db.Integer, primary_key = True, autoincrement = True)
	name = db.Column(db.String)
	album_id = db.Column(db.Integer)
	files = db.Column(db.String)

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
	#return app.send_static_file('index.html')
	return open('static/index.html').read().replace('app.js', 'app.js?' + str(random.random())).replace('app.css', 'app.css?' + str(random.random()))

@app.route('/api/album/<id>/info')
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
	return jsonify({'status': True, 'data': res})

@app.route('/api/album/<id>/update', methods=['POST'])
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

@app.route('/api/album/<id>/scans')
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

@app.route('/api/song/<id>/link')
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

@app.route('/api/log/<id>')
def get_log(id):
	if re.match(r'^[a-zA-Z0-9\._]+$', id) is None:
		return jsonify({'status': False})
	log = auto_decode.decode(files.get_content(id))
	return jsonify({'status': True, 'data': log})

@app.route('/api/log/<id>/download')
def get_log_download(id):
	if re.match(r'^[a-zA-Z0-9\._]+$', id) is None:
		return jsonify({'status': False})
	return jsonify({'status': True, 'data': files.get_link(id, 'album.log')})

app.run(host = '127.0.0.1', port = 1928, debug = True)