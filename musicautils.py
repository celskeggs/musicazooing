import os
import re

def sanitize(ytid):
	print("given", ytid)
	return re.sub("[^-a-zA-Z0-9_:]", "?", ytid)

def path_for(ytid):
	return os.path.join(os.getenv("MZ_DATA_DIR"), sanitize(ytid) + ".mp4")

