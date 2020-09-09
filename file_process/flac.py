from copy import deepcopy
from mutagen.flac import FLAC, Picture
from subprocess import Popen, PIPE


def parse_meta(src, meta):
	if meta:  # song
		meta['ARTIST'] = src.artist
		meta['TITLE'] = src.title
		meta['TRACKNUMBER'] = src.track
		return meta
	res = {  # album
		'ALBUM': src.title,
		'ALBUMARTIST': src.artist,
		'TRACKTOTAL': len(src.tracks),
	}
	if src.release_date is not None:
		res['YEAR'] = str(src.release_date.year)
	return res


def write_tags(f, meta, cov):
	audio = FLAC(f)
	for tag, value in meta.items():
		if value:
			audio[tag] = str(value)
	if cov:
		image = Picture()
		image.type = 3
		image.mime = "image/jpeg"
		image.data = cov
		audio.add_picture(image)
	audio.save()


def process_meta(album, files, covd):
	meta = parse_meta(album, None)
	for i in range(len(files)):
		tmeta = parse_meta(album.tracks[i], deepcopy(meta))
		write_tags(files[i], tmeta, covd)


def remove_padding(src):
	p = Popen(['metaflac', '--dont-use-padding', '--remove-all', src], stdout=PIPE, stderr=PIPE)
	so, er = p.communicate()


def convert(src):
	cmd = ['flac', '-8', '-f', src]
	p = Popen(cmd, stdout=PIPE, stderr=PIPE)
	so, er = p.communicate()


def gen_flac(album, files, covd):
	for i in files:
		remove_padding(i)
	process_meta(album, files, covd)
	for i in files:
		convert(i)
