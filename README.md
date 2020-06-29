# musiclib
Personal music library.

## Features
- Import various formats (mp3, aac, wav, flac, alac, tta, tak, ape, dsd, and etc., it's easy to add other formats that FFmpeg supports), cue sheets are also supported. Lossless PCM files will be split (if it's cue + full disc), and then converted into flac to storage.
- Upload scanned booklets in the CD, check them online. Also, you can attach other files to an album (like EAC logs, or any other file).
- Playlists.
- Verify CDs with CUETools and AccurateRip (using ArCueDotNet from CUETools).
- Find music on MusicBrainz by AcoustID, and fill tags automatically.

## Install
First install the following softwares: `python3 python3-pip python3-dev ffmpeg shntool p7zip-full flac`. It you are Debian or Ubuntu user, just add 'apt install` in front of the list.

Then install the following python packages using pip: `pip3 install mutagen flask flask-sqlalchemy marshmallow-sqlalchemy pymysql mysql-connector chardet pillow pyacoustid`.

Create a database in your MySQL server, initialize the database with [musiclib.sql](musiclib.sql). Fill the information in config.py (rename from config_sample.py).

If you want the AcoustID feature, download fpcalc from https://acoustid.org/chromaprint, and put it info $PATH.

Finally, you can run `web.py`. (Or you can configure uwsgi if you want)

## Known issues
- Some tak files are not supported by FFmpeg. You may convert them info flac before uploading.

## Todo
- Batch import
- Share albums, songs, playlists with others