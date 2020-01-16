import re
from copy import deepcopy
from datetime import timedelta
from flask import Flask, request, jsonify
import minio_wrapper as mi
import db_wrapper as db
from album_init import get_ext
from file_process import auto_decode

app = Flask(__name__)

import random

@app.route('/')
def send_index():
	#return app.send_static_file('index.html')
	return open('static/index.html').read().replace('app.js', 'app.js?' + str(random.random())).replace('app.css', 'app.css?' + str(random.random()))

@app.route('/api/album/<id>/info')
def get_album_info(id):
	id = int(id)
	res = db.get_albums('where id = %s', id)
	if len(res) == 0:
		return jsonify({'status': False})
	res = res[0]
	res['release_date'] = res['release_date'].strftime('%Y-%m-%d') if res['release_date'] else None
	res['cover_files'] = list(map(lambda x: mi.presigned_get_object('covers/' + x, timedelta(hours = 24)), res['cover_files']))
	rso = db.get_songs('where album_id = %s order by track', id)
	for i in rso:
		i.pop('file')
		i.pop('file_flac')
	res['songs'] = rso
	return jsonify({'status': True, 'data': res})

@app.route('/api/album/<id>/update', methods=['POST'])
def update_album_info(id):
	id = int(id)
	s = request.json
	s['trusted'] = int(s['trusted'])
	try:
		so = s['songs']
		s.pop('songs')
		db.update_album(id, s)
		for t in so:
			db.update_song(t['id'], t)
	except Exception as e:
		print(e)
		return jsonify({'status': False})
	return jsonify({'status': True})

@app.route('/api/song/<id>/link')
def get_song_link(id):
	id = int(id)
	res = db.get_songs('where id = %s', id)
	if len(res) == 0:
		return jsonify({'status': False})
	fn = res[0]['artist'] + ' - ' + res[0]['title']
	data = {}
	for key in ['file', 'file_flac']:
		header = {'response-content-disposition': 'attachment; filename="%s.%s"' % (fn, get_ext(res[0][key], ''))}
		data[key] = mi.presigned_get_object('songs/' + res[0][key], timedelta(hours = 24), header) if res[0][key] else ''
	return jsonify({'status': True, 'data': data})

@app.route('/api/log/<id>')
def get_log(id):
	if re.match(r'^[a-zA-Z0-9\._]+$', id) is None:
		return jsonify({'status': False})
	log = auto_decode.decode(mi.get_object('logs/' + id))
	return jsonify({'status': True, 'data': log})

@app.route('/api/log/<id>/download')
def get_log_download(id):
	if re.match(r'^[a-zA-Z0-9\._]+$', id) is None:
		return jsonify({'status': False})
	header = {'response-content-disposition': 'attachment; filename=%s' % id}
	return jsonify({'status': True, 'data': mi.presigned_get_object('logs/' + id, timedelta(hours = 24), header)})

app.run(host = '127.0.0.1', port = 1928, debug = True)