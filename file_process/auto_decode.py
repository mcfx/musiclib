import chardet

def decode(s):
	encoding = chardet.detect(s)['encoding']
	if encoding == 'GB2312' or encoding == 'Windows-1252':
		encoding = 'GBK'
	return s.decode(encoding, 'ignore')