import os
import re

DATA_DIR = os.path.join(os.getenv("HOME"), "musicazoo_videos")

def sanitize(ytid):
	print("given", ytid)
	return re.sub("[^-a-zA-Z0-9_:]", "?", ytid)

def path_for(ytid):
	return os.path.join(DATA_DIR, sanitize(ytid) + ".mp4")

