TEMP_PATH = '/dev/shm'  # Path to storage temporary files. It's recommended to be 3 times large as one of your uploaded zip.

SQL_ADDR = ''  # MySQL address
SQL_USER = ''  # MySQL user
SQL_PASSWORD = ''  # MySQL password
SQL_DATABASE = ''  # MySQL database

SQL_URI = 'mysql+mysqlconnector://%s:%s@%s/%s' % (SQL_USER, SQL_PASSWORD, SQL_ADDR, SQL_DATABASE)

ACCESS_TOKEN = ''  # Token to access web service. It need to be in your cookie with token=xxx

STORAGE_PATH = ''  # Storage path. Audio, image, and log files will be store here. They will be renamed into their sha512.
STORAGE_SALT = b''  # Salt of file url generation. Just randomly type something here.

BACKUP_PATH = ''  # All files you uploaded (and processed correctly) will copied here. It's recommended to use (unlimited) Google Drive.

TRUSTED_EXTENSIONS = ['zip', 'rar', '7z', 'log', 'txt', 'jpg']  # Extension list for uploading

RESULTS_PER_PAGE = 50  # Frontend pagination
PAGE_MAX = 1000000

VUEROUTER_HISTORY_MODE = True  # See https://router.vuejs.org/guide/essentials/history-mode.html

TASK_CLEAR_TIME = 7200  # How long will finished tasks be cleared. In seconds

ACOUSTID_APIKEY = ''  # Get your own one on https://acoustid.org/
PROXY = ''  # If archive.org is blocked, set this to http://xxx, socks5://xxx, etc. (socks proxy requires requests[socks])

ARCUEDOTNET_COMMAND = ['']  # Path of ArCueDotNet.exe, maybe ['wine', 'path'] or ['mono', 'path'] (can be omitted if you don't want this feature)
CONVERT_TO_WAV_BEFORE_VERIFY = False  # If you are using mono, set this to True

DEBUG = True  # Flask mode
