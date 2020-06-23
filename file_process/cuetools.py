import os
from shutil import copyfile
from subprocess import Popen, PIPE
from mutagen.flac import FLAC, Picture
from . import ffmpeg
from . import utils
import config

def verify(files, trackids):
	path = config.TEMP_PATH
	if path[-1] != '/':
		path += '/'
	path += 'verify/'
	tmp_files = []
	if trackids is None:
		if config.CONVERT_TO_WAV_BEFORE_VERIFY:
			for i in range(len(files)):
				fn = path + str(i) + '.wav'
				ffmpeg.convert(files[i], fn)
				tmp_files.append(fn)
		else:
			for i in range(len(files)):
				fn = path + str(i) + '.flac'
				copyfile(files[i], fn)
				tmp_files.append(fn)
	else:
		for i in range(len(files)):
			fn = path + str(i) + '.flac'
			copyfile(files[i], fn)
			audio = FLAC(fn)
			audio['TRACKNUMBER'] = str(trackids[i])
			audio['TITLE'] = 'test_album'
			audio.save()
			if config.CONVERT_TO_WAV_BEFORE_VERIFY:
				fn2 = path + str(i) + '.wav'
				ffmpeg.convert(fn, fn2)
				tmp_files.append(fn2)
				os.remove(fn)
			else:
				tmp_files.append(fn)
	cmd = config.ARCUEDOTNET_COMMAND + [tmp_files[0]]
	p = Popen(cmd, stdout = PIPE, stderr = PIPE)
	so, er = p.communicate()
	return so.decode()