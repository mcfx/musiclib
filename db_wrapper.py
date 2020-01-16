import db
from copy import copy, deepcopy

def get_albums(sql_add, sql_param):
	all = db.select("select * from albums " + sql_add, sql_param)
	res = []
	for at in all:
		t = {
			'id': at[0],
			'title': at[1],
			'release_date': at[2],
			'artist': at[3],
			'format': at[4],
			'quality': at[5],
			'quality_details': at[6],
			'source': at[7],
			'file_source': at[8],
			'trusted': at[9],
			'log_files': at[10].split(',') if len(at[10]) else [],
			'cover_files': at[11].split(',') if len(at[11]) else [],
			'comments': at[12],
		}
		res.append(t)
	return res

def update_album(id, data):
	data = copy(data)
	data['id'] = id
	sql = "update albums set title = %(title)s, release_date = %(release_date)s, artist = %(artist)s, source = %(source)s, file_source = %(file_source)s, comments = %(comments)s, trusted = %(trusted)s "\
		"where id = %(id)s"
	db.execute(sql, data)

def get_songs(sql_add, sql_param):
	all = db.select("select * from songs " + sql_add, sql_param)
	res = []
	for at in all:
		t = {
			'id': at[0],
			'album_id': at[1],
			'track': at[2],
			'title': at[3],
			'artist': at[4],
			'duration': at[5],
			'format': at[6],
			'quality': at[7],
			'quality_details': at[8],
			'file': at[9],
			'file_flac': at[10],
		}
		res.append(t)
	return res

def update_song(id, data):
	data = copy(data)
	data['id'] = id
	sql = "update songs set track = %(track)s, title = %(title)s, artist = %(artist)s where id = %(id)s"
	db.execute(sql, data)