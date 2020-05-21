import os, hashlib, binascii, shutil, time
from threading import RLock

from flask import Flask, request, current_app, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy

from file_utils import get_ext
from flask_wrappers import skip_error
import config

app = None
try:
	app = current_app
	str(app)
except:
	app = Flask(__name__)
	app.config['SQLALCHEMY_DATABASE_URI'] = config.SQL_URI
	app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)

class File(db.Model):
	__tablename__ = 'files'
	sha512 = db.Column(db.LargeBinary(64), primary_key = True)
	count = db.Column(db.Integer)

def add_bytes(s, ext = ''):
	sha512 = hashlib.sha512(s).digest()
	hexhs = binascii.hexlify(sha512).decode()
	file = File.query.filter(File.sha512 == sha512).first()
	if file is None:
		db.session.add(File(sha512 = sha512, count = 1))
		db.session.commit()
		fo = config.STORAGE_PATH + '/' + hexhs[:2]
		fn = fo + '/' + hexhs[2:]
		if not os.path.exists(fo):
			os.mkdir(fo)
		open(fn, 'wb').write(s)
	else:
		file.count += 1
		db.session.commit()
	return hexhs + '.' + ext

db_lock = RLock()

def add_file(tmp_path):
	hs = hashlib.sha512()
	with open(tmp_path, 'rb') as f:
		while True:
			t = f.read(131072)
			if t == b'': break
			hs.update(t)
	sha512 = hs.digest()
	hexhs = binascii.hexlify(sha512).decode()
	db_lock.acquire()
	file = File.query.filter(File.sha512 == sha512).first()
	if file is None:
		db.session.add(File(sha512 = sha512, count = 1))
		db.session.commit()
		db_lock.release()
		fo = config.STORAGE_PATH + '/' + hexhs[:2]
		fn = fo + '/' + hexhs[2:]
		if not os.path.exists(fo):
			os.mkdir(fo)
		shutil.copy(tmp_path, fn)
	else:
		file.count += 1
		db.session.commit()
		db_lock.release()
	return hexhs + '.' + get_ext(tmp_path, '')

def del_file(hash):
	hash = purify_hash(hash)
	sha512 = binascii.unhexlify(hash)
	db_lock.acquire()
	file = File.query.filter(File.sha512 == sha512).one()
	file.count -= 1
	if file.count == 0:
		fo = config.STORAGE_PATH + '/' + hash[:2]
		fn = fo + '/' + hash[2:]
		os.remove(fn)
		db.session.delete(file)
	db.session.commit()
	db_lock.release()

def purify_hash(s):
	if '.' not in s:
		return s
	p = s.rfind('.')
	if p >= len(s) - 5:
		return s[:p]
	return s

def get_content(hash):
	hash = purify_hash(hash)
	fo = config.STORAGE_PATH + '/' + hash[:2]
	fn = fo + '/' + hash[2:]
	if os.path.exists(fn):
		return open(fn, 'rb').read()
	return None

def sign(hash, expire):
	return hashlib.md5(config.STORAGE_SALT + str(expire).encode() + binascii.unhexlify(hash) + config.STORAGE_SALT).hexdigest()

def get_link(hash, dlname = 'file', expire = 3600):
	hash = purify_hash(hash)
	dlname = dlname.replace('/', '／')
	expire += int(time.time())
	sig = sign(hash, expire)
	return '/file/%s/%s?expire=%d&sign=%s' % (hash, dlname, expire, sig)

@app.route('/file/<hash>/<dlname>')
@skip_error
def get_file(hash, dlname):
	expire = request.values.get('expire')
	sig = request.values.get('sign')
	if expire is None or sig is None:
		return ''
	if sign(hash, expire) != sig:
		return ''
	try:
		hash = binascii.unhexlify(hash)
	except:
		return ''
	file = File.query.filter(File.sha512 == hash).first()
	if file is None:
		return ''
	hash = binascii.hexlify(hash).decode()
	fo = config.STORAGE_PATH + '/' + hash[:2]
	fn = hash[2:]
	return send_from_directory(fo, fn, as_attachment = True, attachment_filename = dlname)

@app.route('/filebk/<date>/<name>')
@skip_error
def get_file_backup(date, name):
	date = str(int(date))
	name = secure_filename(name)
	dlname = request.values.get('dlname')
	fo = config.BACKUP_PATH.rstrip('\\').rstrip('/') + '/' + date
	fn = name
	if fn == '' or not os.path.exists(fo + '/' + fn):
		return ''
	return send_from_directory(fo, fn, as_attachment = True, attachment_filename = dlname)
