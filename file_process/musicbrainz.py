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
	res = requests.get(MB_API_BASE + path, params = params, timeout = 30).json()
	if 'error' in res:
		if res['error'] == 'Not Found':
			return None
		raise Exception('Error: ' + res['error'])
	return res

def mb_get_release(id):
	return mb_get('release/' + id, {'inc': 'artist-credits recordings', 'fmt': 'json'})

def mb_get_recording(id):
	return mb_get('recording/' + id, {'inc': 'artist-credits releases', 'fmt': 'json'})

def mb_get_cover(id):
	url = 'https://coverartarchive.org/release/' + id + '/front.jpg'
	r = requests.get(url, proxies = {'http': config.PROXY, 'https': config.PROXY}, timeout = 30)
	if r.status_code != 200:
		return None
	return r.content

def match_albums(files):
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
						tmp = mb_get_recording(j['id'])
						if tmp is not None:
							cur.append(tmp)
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
		tmp = mb_get_release(i)
		if tmp is not None:
			resa.append(tmp)
	return resa, res

def get_artist_name(s):
	return ''.join(map(lambda x: x['name'] + x['joinphrase'], s))
