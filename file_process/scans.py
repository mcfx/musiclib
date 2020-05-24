import os, traceback
from PIL import Image
from .utils import get_ext

Image.MAX_IMAGE_PIXELS = None

def get_converted_images(fo, dstfo):
	if fo[-1] != '/':
		fo += '/'
	if dstfo[-1] != '/':
		dstfo += '/'
	res = []
	def dfs_path(cur_path):
		for i in os.listdir(fo + cur_path):
			if os.path.isdir(fo + cur_path + i):
				dfs_path(cur_path + i + '/')
				continue
			try:
				with Image.open(fo + cur_path + i) as im:
					if get_ext(i, '') in ['png', 'jpg']:
						res.append([cur_path + i, fo + cur_path + i])
					else:
						im.save(dstfo + '/' + str(len(res)) + '.png')
						res.append([cur_path + i, dstfo + '/' + str(len(res)) + '.png'])
					L = 300
					if im.size[0] < im.size[1]:
						t = (im.size[0] - im.size[1]) // 2
						im2 = im.convert('RGBA').crop((t, 0, t + im.size[1], im.size[1]))
					else:
						t = (im.size[1] - im.size[0]) // 2
						im2 = im.convert('RGBA').crop((0, t, im.size[0], t + im.size[0]))
					im2 = im2.resize((L, L))
					im2.save(dstfo + '/' + str(len(res)) + 'l.png')
					res[-1].append(dstfo + '/' + str(len(res)) + 'l.png')
			except:
				#traceback.print_exc()
				pass
	dfs_path('')
	return res