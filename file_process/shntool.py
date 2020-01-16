from subprocess import Popen, PIPE
import os

def split_cue(cue_file, wave_file, dst):
	old_cwd = os.getcwd()
	os.chdir(dst)
	cmd = ['shntool', 'split', '-f', cue_file, '-t', '%t', '-o', 'flac', wave_file]
	p = Popen(cmd, stdout = PIPE, stderr = PIPE)
	so, er = p.communicate()
	#print(so)
	#print(er)
	os.chdir(old_cwd)


r'''
dir = r'C:\Users\i\Desktop\mu\tflac'
cue = dir + '\\' + r'test.cue'
wave = dir + '\\' + r'test.wav'

split_cue(cue, wave, r'C:\Users\i\Desktop\mu\tflac')
'''