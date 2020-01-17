import os
import re

DATA_DIR = os.getenv("MZ_DATA_DIR")

def sanitize(ytid):
	return re.sub("[^-a-zA-Z0-9_:]", "?", ytid)

def path_for(ytid):
	return os.path.join(DATA_DIR, sanitize(ytid) + ".mp4")

