import redis
import re
import traceback
import json
import os
import subprocess

DATA_DIR = os.path.join(os.getenv("HOME"), "musicazoo_videos")
YOUTUBE_DL = os.path.join(os.getenv("HOME"), ".local/bin/youtube-dl")

if not os.path.isdir(DATA_DIR):
	os.mkdir(DATA_DIR)

redis = redis.Redis()

# refresh the loading queue

while redis.lpop("musicaload") is not None:
	pass

for ent in redis.lrange("musicaqueue", 0, -1):
	redis.rpush("musicaload", json.loads(ent.decode())["ytid"])

def sanitize(ytid):
	print("given", ytid)
	return re.sub("[^-a-zA-Z0-9_:]", "?", ytid)

def path_for(ytid):
	return os.path.join(DATA_DIR, sanitize(ytid) + ".mp4")

def gen_cmdline(ytid, for_title=False):
	return [YOUTUBE_DL, "--no-playlist", "--id", "--no-progress", "--format", "mp4"] + (["--get-title"] if for_title else []) + ["--", sanitize(ytid)]

def get_title(ytid):
	return subprocess.check_output(gen_cmdline(ytid, for_title=True))

# "mplayer -fs"

while True:
	_, to_load = redis.blpop("musicaload")
	try:
		to_load = to_load.decode()
		if not os.path.exists(path_for(to_load)):
			if subprocess.call(gen_cmdline(to_load), cwd=DATA_DIR) != 0:
				redis.set("musicatitle." + to_load, b"Could not load video %s" % to_load.encode())
				continue
			subprocess.check_call(gen_cmdline(to_load), cwd=DATA_DIR)
			assert os.path.exists(path_for(to_load))
		if redis.get("musicatitle." + to_load) is None:
			redis.set("musicatitle." + to_load, get_title(to_load).strip())
	except:
		print("Failed to load.")
		traceback.print_exc()
