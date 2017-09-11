import redis
import time
import re
import json
import os
import subprocess
from mplayer import Player

current_uuid = None
should_be_paused = False

DATA_DIR = os.path.join(os.getenv("HOME"), "musicazoo_videos")
display_video = (os.getenv("MZ_VIDEO") == "true")
xinerama_screen = os.getenv("MZ_XINERAMA_SCREEN")

if display_video:
	os.environ["DISPLAY"] = ":0.0"
	if xinerama_screen:
		player_args = ("-fs", "--xineramascreen=%s" % xinerama_screen)
	else:
		player_args = ("-fs")
else:
	player_args = ("-vo", "null")

player = Player(args=player_args)

redis = redis.Redis()

def sanitize(ytid):
	return re.sub("[^-a-zA-Z0-9_]", "?", ytid)

def path_for(ytid):
	return os.path.join(DATA_DIR, sanitize(ytid) + ".mp4")

if display_video:
	subprocess.check_call(os.path.join(os.path.dirname(os.path.abspath(__file__)), "configure-screen.sh"))

def start_playing(uuid, ytid):
	global current_uuid, should_be_paused, player
	if current_uuid is not None:
		stop_playing()
	if player is None:
		player = Player(args=player_args)
	assert player.filename is None
	if os.path.exists(path_for(ytid)):
		current_uuid = uuid
		player.loadfile(path_for(ytid))
		should_be_paused = False

def stop_playing():
	global current_uuid, player
	assert current_uuid is not None
	current_uuid = None
	player.stop()

def playback_pause():
	global should_be_paused, player
	should_be_paused = not should_be_paused
	player.pause()

def check_finished_uuid():
	global current_uuid, player
	if player is not None and player.filename is None:
		uuid = current_uuid
		current_uuid = None
		return uuid
	else:
		return False

def control_callback(message):
	global player
	if player is not None and player.filename is not None:
		playback_pause()

p = redis.pubsub(ignore_subscribe_messages=True)
p.subscribe(musicacontrol=control_callback)

def status_update():
	global player
	if player is None:
		return
	redis.set("musicastatus", json.dumps({"paused": player.paused, "time": player.time_pos or 0, "length": player.length or 0}))

while True:
	if player is not None and player.filename is not None and player.paused != should_be_paused:
		player.pause()
	status_update()
	p.get_message()
	quent = redis.lindex("musicaqueue", 0)
	removed_uuid = check_finished_uuid()
	if removed_uuid and quent and removed_uuid == json.loads(quent.decode())["uuid"]:
		print("DEQUEUE")
		ent = redis.lpop("musicaqueue")
		redis.set("musicatime.%s" % json.loads(quent.decode())["ytid"], time.time())
		redis.rpush("musicaudit", "dequeued entry %s at %s because process ended" % (ent, time.ctime()));
		quent = redis.lindex("musicaqueue", 0)
	if quent:
		quent = json.loads(quent.decode())
		if quent["uuid"] != current_uuid:
			redis.set("musicatime.%s" % quent["ytid"], time.time())
			start_playing(quent["uuid"], quent["ytid"])
	else:
		if current_uuid is not None:
			stop_playing()
		if player is not None:
			player.quit()
			player = None
	time.sleep(0.5)
