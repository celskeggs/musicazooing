import redis
import time
import re
import json
import os
import subprocess

current_subprocess = None
current_uuid = None

DATA_DIR = "/tmp/musicazoo_videos"

redis = redis.Redis()

def sanitize(ytid):
	return re.sub("[^-a-zA-Z0-9_]", "?", ytid)

def path_for(ytid):
	return os.path.join(DATA_DIR, sanitize(ytid) + ".mp4")

def start_playing(uuid, ytid):
	global current_uuid, current_subprocess
	if current_uuid is not None:
		stop_playing()
	assert current_subprocess is None
	if os.path.exists(path_for(ytid)):
		current_uuid = uuid
		current_subprocess = subprocess.Popen(["mplayer", path_for(ytid)]) # -fs

def stop_playing():
	global current_uuid, current_subprocess
	assert current_uuid is not None and current_subprocess is not None
	current_uuid = None
	if current_subprocess.poll() is None:
		current_subprocess.terminate()
		if current_subprocess.poll() is None:
			time.sleep(0.2)
			if current_subprocess.poll() is None:
				current_subprocess.kill()
				current_subprocess.wait()
	assert current_subprocess.poll() is not None
	current_subprocess = None

def check_on_process():
	global current_uuid, current_subprocess
	if current_subprocess is not None and current_subprocess.poll() is not None:
		current_subprocess = None
		uuid = current_uuid
		current_uuid = None
		return uuid
	else:
		return False

while True:
	quent = redis.lindex("musicaqueue", 0)
	removed_uuid = check_on_process()
	if removed_uuid and quent and removed_uuid == json.loads(quent.decode())["uuid"]:
		print("DEQUEUE")
		redis.lpop("musicaqueue")
		quent = redis.lindex("musicaqueue", 0)
	if quent:
		quent = json.loads(quent.decode())
		if quent["uuid"] != current_uuid:
			start_playing(quent["uuid"], quent["ytid"])
	elif current_uuid is not None:
		stop_playing()
	time.sleep(1)
