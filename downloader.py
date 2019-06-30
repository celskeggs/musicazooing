import redis
import re
import traceback
import json
import os
import subprocess

from musicautils import *

YOUTUBE_DL = os.path.join(os.getenv("HOME"), ".local/bin/youtube-dl")

DATA_DIR = os.getenv("MZ_DATA_DIR")

if not os.path.isdir(DATA_DIR):
	os.mkdir(DATA_DIR)

redis = redis.Redis()

# refresh the loading queue

while redis.lpop("musicaload") is not None:
	pass

for ent in redis.lrange("musicaqueue", 0, -1):
	redis.rpush("musicaload", json.loads(ent.decode())["ytid"])

def gen_cmdline(ytid, for_title=False):
	return [YOUTUBE_DL, "--no-playlist", "--id", "--no-progress", "--format", "mp4"] + (["--get-title"] if for_title else []) + ["--", sanitize(ytid)]

def get_title(ytid):
	return subprocess.check_output(gen_cmdline(ytid, for_title=True))

# "mplayer -fs"

while True:
	_, to_load = redis.blpop("musicaload")
	try:
		to_load = to_load.decode()
		if redis.get("musicatitle." + to_load) is None:
			redis.set("musicatitle." + to_load, get_title(to_load).strip())
		if not os.path.exists(path_for(to_load)):
			if subprocess.call(gen_cmdline(to_load), cwd=DATA_DIR) != 0:
				redis.set("musicatitle." + to_load, ("Could not load video %s" % (to_load,)).encode())
				continue
			subprocess.check_call(gen_cmdline(to_load), cwd=DATA_DIR)
			assert os.path.exists(path_for(to_load))
	except:
		print("Failed to load.")
		traceback.print_exc()
