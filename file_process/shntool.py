from subprocess import Popen, PIPE
import os

def split_cue(cue_file, wave_file, dst):
	old_cwd = os.getcwd()
	os.chdir(dst)
	cmd = ['shntool', 'split', '-f', cue_file, '-t', '%t', '-o', 'flac', wave_file]
	p = Popen(cmd, stdout = PIPE, stderr = PIPE)
	so, er = p.communicate()
	if er != b'':
		raise Exception(er.decode())
	os.chdir(old_cwd)
