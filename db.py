import pymysql
import config

def getdb():
	return pymysql.connect(config.SQL_ADDR,config.SQL_USER,config.SQL_PASSWORD,config.SQL_DATABASE)

db = getdb()

def execute(s, args = None, tdb = db):
	try:
		cur = tdb.cursor()
		cur.execute(s, args)
	except pymysql.err.IntegrityError:
		pass
	return cur

def select(s, args = None, tdb = db):
	cur = tdb.cursor()
	cur.execute(s, args)
	return cur

def select_first(s, args = None, tdb = db):
	for i in select(s, args, tdb):
		return i
	return None

def count(s, args = None, tdb = db):
	cur = tdb.cursor()
	cur.execute(s, args)
	for i in cur:
		return i[0]

def renew():
	global db
	db.close()
	db = getdb()