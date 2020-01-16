from . import auto_decode

def unescape(s):
	if s[0] == '"':
		return s[1:-1]
	return s

def read_cue(s):
	s = auto_decode.decode(s)
	#print(s)
	s = list(filter(len, s.replace('\r', '').split('\n')))
	g_vars = {}
	cur_file = ('', '')
	tracks = {}
	cur = g_vars
	lst = g_vars
	for _si in s:
		so, sa = _si.strip().split(' ', 1)
		if so == 'REM':
			x, y = sa.split(' ', 1)
			cur[x.lower()] = unescape(y)
		elif so == 'PERFORMER':
			cur['performer'] = unescape(sa)
		elif so == 'SONGWRITER':
			cur['songwriter'] = unescape(sa)
		elif so == 'TITLE':
			cur['title'] = unescape(sa)
		elif so == 'ISRC':
			cur['isrc'] = unescape(sa)
		elif so == 'CATALOG':
			cur['catalog'] = unescape(sa)
		elif so == 'FILE':
			p = sa.rfind(' ')
			if p == -1 or '"' in sa[p:]:
				cur_file = (unescape(p), '')
			else:
				cur_file = (unescape(sa[:p]), unescape(sa[p + 1:]))
		elif so == 'TRACK':
			sa = sa.split(' ')
			lst = cur
			cur = {'file': cur_file}
			tracks[int(sa[0])] = cur
			if len(sa) > 1:
				cur['type'] = sa[1].lower()
		elif so == 'INDEX':
			x, y = sa.split(' ')
			if y == '00:00:00':
				pass
			elif int(x) == 0:
				#lst['end_time'] = y
				pass #not compatible with exists software
			elif int(x) == 1:
				cur['start_time'] = y
				if 'end_time' not in lst:
					lst['end_time'] = y
		elif so == 'FLAGS':
			pass
			#ignore subcode flags
		else:
			#raise Exception('Unsupported cue command: ' + so)
			pass
	#print(g_vars)
	#print(tracks)
	g_vars['tracks'] = tracks
	return g_vars

'''
test=[
r'D:\music\A Channel\BD1\ANZX-9872.cue',
r'D:\music\Gochuumon wa Usagi Desuka\[EAC] [190926] ご注文はうさぎですか？？~Sing For You~ イメージソング「しんがーそんぐぱやぽやメロディー」 (wav)\Petit Rabbit’s - しんがーそんぐぱやぽやメロディー.cue',
r'D:\music\Machikado Mazoku\まちカドまぞく ED＆OPテーマ「よいまちカンターレ／町かどタンジェント」／コーロまちカド（小原好美、鬼頭明里、高橋未奈美、高柳知葉）、shami momo（小原好美、鬼頭明里）\コーロまちカド（小原好美、鬼頭明里、高橋未奈美、高柳知葉）、shami momo（小原好美、鬼頭明里） - よいまちカンターレ,町かどタンジェント.cue',
r'D:\music\0_eac\kampfer s2\new\Various Artists - Choose my love! , 妄想少女A.cue',
r'D:\music\0_eac\さらざんまいのうた , カワウソイヤァ\矢逆一稀 (村瀬歩), 久慈悠 (内山昂輝), 陣内燕太 (堀江瞬), ケッピ (諏訪部順一) - さらざんまいのうた , カワウソイヤァ.cue',
r'D:\music\ISLAND\ISLAND オリジナルサウンドトラック\Vocal DISC\ISLAND オリジナルサウンドトラック Vocal DISC.cue',
r'D:\music\Chuunibyou demo Koi ga Shitai!\CDs\[EAC] [140129]「VOICE」[限定盤]／ZAQ(flac+jpg)\VOICE【初回限定盤】.cue',
r'D:\music\Saikin, Imouto no Yousu ga Chotto Okashiinda ga\小倉唯 - Charming Do!.cue',
r'D:\music\Jinrui wa Suitai Shimashita\ユメのなかノわたしのユメ\伊藤真澄 - ユメのなかノわたしのユメ.cue'
]
'''
#for i in test:
#	read_cue(i)
#read_cue(test[8])