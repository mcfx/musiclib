TEMP_PATH = '/dev/shm'

SQL_ADDR = ''
SQL_USER = ''
SQL_PASSWORD = ''
SQL_DATABASE = ''

SQL_URI = 'mysql+mysqlconnector://%s:%s@%s/%s'%(SQL_USER, SQL_PASSWORD, SQL_ADDR, SQL_DATABASE)

ACCESS_TOKEN = ''

STORAGE_PATH = ''
STORAGE_SALT = b''

BACKUP_PATH = ''

TRUSTED_EXTENSIONS = ['zip', 'rar', '7z', 'log', 'txt', 'jpg']

RESULTS_PER_PAGE = 50
PAGE_MAX = 1000000

TASK_CLEAR_TIME = 7200 # 2 hours

ACOUSTID_APIKEY = '' # get your own one on https://acoustid.org/
PROXY = '' # if archive.org is blocked, set this to http://xxx, socks5://xxx, etc. (socks proxy requires requests[socks])

ARCUEDOTNET_COMMAND = [''] # path of ArCueDotNet.exe, maybe ['wine', 'path'] or ['mono', 'path'] (can be omitted if you don't want this feature)
CONVERT_TO_WAV_BEFORE_VERIFY = False # if you use mono, set this to True

DEBUG = True
