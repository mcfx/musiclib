import time, requests
import acoustid
import config

MB_API_BASE = 'https://musicbrainz.org/ws/2/'

last_api_call = 0
def mb_get(path, params):
	global last_api_call
	tm = time.time()
	if tm - last_api_call < 1:
		time.sleep(1 - tm + last_api_call)
	last_api_call = tm
	return requests.get(MB_API_BASE + path, params = params).json()

def mb_get_release(id):
	return mb_get('release/' + id, {'inc': 'artist-credits recordings', 'fmt': 'json'})

def mb_get_recording(id):
	return mb_get('recording/' + id, {'inc': 'artist-credits releases', 'fmt': 'json'})

def match_albums(files):
	print(files)
	res = []
	rel_all = None
	for f in files:
		t = acoustid.match(config.ACOUSTID_APIKEY, f, 'recordingids', parse = False)
		cur = []
		cur_rels = set()
		for i in t['results']:
			if 'recordings' in i:
				for j in i['recordings']:
					if 'id' in j:
						cur.append(mb_get_recording(j['id']))
		for i in cur:
			for j in i['releases']:
				cur_rels.add(j['id'])
		res.append(cur)
		if rel_all is None:
			rel_all = cur_rels
		else:
			rel_all &= cur_rels
	resa = []
	for i in rel_all:
		resa.append(mb_get_release(i))
	return resa, res