import pymysql
import config


def getdb():
	return pymysql.connect(host=config.SQL_ADDR, user=config.SQL_USER, password=config.SQL_PASSWORD, db=config.SQL_DATABASE)


db = getdb()


def execute(s, args=None, tdb=None):
	if tdb is None:
		tdb = db
	try:
		cur = tdb.cursor()
		cur.execute(s, args)
	except pymysql.err.IntegrityError:
		pass
	return cur


def select(s, args=None, tdb=None):
	if tdb is None:
		tdb = db
	cur = tdb.cursor()
	cur.execute(s, args)
	return cur


def select_first(s, args=None, tdb=None):
	if tdb is None:
		tdb = db
	for i in select(s, args, tdb):
		return i
	return None


def count(s, args=None, tdb=None):
	if tdb is None:
		tdb = db
	cur = tdb.cursor()
	cur.execute(s, args)
	for i in cur:
		return i[0]


def renew():
	global db
	db.close()
	db = getdb()
