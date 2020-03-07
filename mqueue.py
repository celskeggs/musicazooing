import json
import os
import re
import redis
import random
import subprocess
import time
import urllib.parse
import uuid


class Entry:
	def __init__(self, kvs: dict, encoded: bytes=None):
		self.kvs = dict(kvs)
		if encoded is None:
			self.encoded = json.dumps(self.kvs).encode()
		else:
			self.encoded = encoded

	@property
	def ytid(self) -> str:
		return self.kvs["ytid"]

	@property
	def uuid(self) -> str:
		return self.kvs["uuid"]

	@property
	def random(self) -> bool:
		return self.kvs.get("random", False)

	@classmethod
	def from_ytid(self, ytid: str, is_random: bool=False) -> "Entry":
		return Entry({
			"ytid": ytid,
			"uuid": str(uuid.uuid4()),
			"random": is_random,
		})

	@classmethod
	def decode(self, entry: bytes) -> "Entry":
		return Entry(json.loads(entry.decode()), entry)


class Queue:
	def __init__(self):
		self.redis = redis.Redis()
		self.subscriptions = None
		self.cb_on_pause = None
		self.cb_on_navigate = None

	def read_queue(self) -> list:
		return [Entry.decode(ent) for ent in self.redis.lrange("musicaqueue", 0, -1)]

	def current_playable_on_queue(self) -> Entry:
		entry = self.redis.lindex("musicaqueue", 0)
		return Entry.decode(entry) if entry else None

	def read_queue_by_uuid(self, uuid: str):
		found = [ent for ent in self.read_queue() if ent.uuid == uuid]
		if len(found) > 1:
			raise Exception("unexpected state: queue had multiple elements with uuid %s" % uuid)
		return found[0] if found else None

	def dequeue_playable(self) -> None:
		ent = self.redis.lpop("musicaqueue")
		if ent is not None:
			quent = Entry.decode(ent)
			self.record_play_start(quent.ytid)
			self.redis.rpush("musicaudit", "dequeued entry %s at %s because process ended" % (ent, time.ctime()));

	def record_play_start(self, ytid) -> None:
		self.redis.set("musicatime.%s" % ytid, time.time())

	def read_title(self, ytid: str):
		value = self.redis.get("musicatitle.%s" % ytid)
		return value.decode() if value else None

	def set_title(self, ytid: str, title: str) -> None:
		self.redis.set("musicatitle." + ytid, title)

	def enqueue_ytid(self, ytid: str, increment=True) -> None:
		self.enqueue(Entry.from_ytid(ytid, is_random=not increment), increment=increment)

	def enqueue(self, entry: Entry, increment=True) -> None:
		self.redis.rpush("musicaqueue", entry.encoded)
		self.request_load_video(entry.ytid)
		if increment:
			self.redis.incr("musicacommon.%s" % entry.ytid)
			self.redis.sadd("musicacommonset", entry.ytid)
		self.redis.set("musicatime.%s" % entry.ytid, time.time())

	def request_load_video(self, ytid: str) -> None:
		self.redis.rpush("musicaload", ytid)

	def remove(self, entry: Entry) -> None:
		count = self.redis.lrem("musicaqueue", 0, entry.encoded)
		self.redis.rpush("musicaudit", "removed entry for %s at %s because of deletion request" % (entry.encoded, time.ctime()))

	def move(self, uuid: str, rel: int) -> bool:
		assert rel in (-1, 1)
		with self.redis.pipeline() as pipe:
			while True:
				try:
					pipe.watch("musicaqueue")
					cur_queue = pipe.lrange("musicaqueue", 0, -1)
					found = [ent for ent in cur_queue if json.loads(ent.decode())["uuid"] == uuid]
					if len(found) != 1:
						return False
					cur_index = cur_queue.index(found[0])
					if (cur_index == 0 and rel < 0) or (cur_index == len(found) - 1 and rel > 0):
						return False
					pipe.multi()
					pipe.lset("musicaqueue", cur_index, cur_queue[cur_index + rel])
					pipe.lset("musicaqueue", cur_index + rel, cur_queue[cur_index])
					pipe.execute()
					return True
				except WatchError:
					continue

	def set_playback_status(self, status: dict) -> None:
		self.redis.set("musicastatus", json.dumps(status))

	def playback_status(self) -> dict:
		raw_status = self.redis.get("musicastatus")
		return json.loads(raw_status.decode()) if raw_status else {}

	def pause(self) -> None:
		self.redis.publish("musicacontrol", json.dumps({"cmd": "pause"}))

	def navigate(self, rel: float) -> None:
		assert type(rel) == float
		self.redis.publish("musicacontrol", json.dumps({"cmd": "navigate", "rel": rel}))

	def subscribe_on_pause(self, on_pause):
		if self.cb_on_pause is not None:
			raise Exception("duplicate subscription of on_pause")
		self.cb_on_pause = on_pause
		self.subscribe_updates()

	def subscribe_on_navigate(self, on_navigate):
		if self.cb_on_navigate is not None:
			raise Exception("duplicate subscription of on_navigate")
		self.cb_on_navigate = on_navigate
		self.subscribe_updates()

	def _recv_callback(self, message):
		jmsg = json.loads(message["data"].decode())
		if type(jmsg) != dict:
			raise Exception("invalid format for message")
		if jmsg.get("cmd") == "pause":
			if self.cb_on_pause is not None:
				self.cb_on_pause()
		elif jmsg.get("cmd") == "navigate" and type(jmsg.get("rel")) == float:
			if self.cb_on_navigate is not None:
				self.cb_on_navigate(jmsg["rel"])
		else:
			print("unrecognized message: %s" % jmsg)

	def check_messages(self):
		if self.subscriptions is None:
			raise Exception("attempt to check_messages before subscribe_updates!")
		self.subscriptions.get_message()

	def subscribe_updates(self):
		if self.subscriptions is None:
			self.subscriptions = self.redis.pubsub(ignore_subscribe_messages=True)
			self.subscriptions.subscribe(musicacontrol=self._recv_callback)

	def play_counts(self) -> dict:
		members = [x.decode() for x in self.redis.smembers("musicacommonset")]
		plays_strs = self.redis.mget(*["musicacommon.%s" % member for member in members])
		titles = self.redis.mget(*["musicatitle.%s" % member for member in members])

		plays = [int(x) for x in plays_strs]
		titles = [x.decode() if x else "%s (loading)" % member for member, x in zip(members, titles)]
		return {member: (title, plays) for member, title, play in zip(members, titles, plays)}

	def random_previous_ytid(self) -> str:
		youtube_ids = self.redis.srandmember("musicacommonset", 300)
		if not youtube_ids:
			return None
		nonrecent = []
		total = 0
		for youtube_id in youtube_ids:
			youtube_id = youtube_id.decode()
			ltime = self.redis.get("musicatime.%s" % youtube_id)
			if ltime is None or time.time() - (float(ltime.decode()) or 0) >= 3600:
				for i in range(int(self.redis.get("musicacommon.%s" % youtube_id).decode()) or 1):
					nonrecent.append(youtube_id)
		if not nonrecent:
			return None
		return random.choice(nonrecent)

	def clear_loading_queue(self) -> None:
		while self.redis.lpop("musicaload") is not None:
			pass

	def take_loading_queue(self) -> str:
		_, value = self.redis.blpop("musicaload")
		return value.decode()


def sanitize_ytid(ytid):
	return re.sub("[^-a-zA-Z0-9_:]", "?", ytid)


class Stash:
	def __init__(self, directory=None):
		if directory is None:
			self.dir = os.getenv("MZ_DATA_DIR")
			if self.dir is None:
				raise Exception("no MZ_DATA_DIR set!")
		else:
			self.dir = directory

	def create_datadir_if_missing(self):
		if not os.path.isdir(self.dir):
			os.mkdir(self.dir)

	def path_for(self, ytid):
		return os.path.join(self.dir, sanitize_ytid(ytid) + ".mp4")

	def exists(self, ytid):
		return os.path.exists(self.path_for(ytid))


class Fetcher:
	def __init__(self):
		self.ytdl_path = os.path.join(os.getenv("HOME"), ".local", "bin", "youtube-dl")

	def _gen_cmdline(self, ytid: str, for_title: bool=False) -> list:
		return [self.ytdl_path, "--no-playlist", "--id", "--no-progress", "--format", "mp4"] + (["--get-title"] if for_title else []) + ["--", sanitize_ytid(ytid)]

	def get_title(self, ytid: str) -> str:
		return subprocess.check_output(self._gen_cmdline(ytid, for_title=True)).strip()

	# TODO: manage filenames explicitly
	def download_into(self, ytid: str, stash: Stash):
		return subprocess.call(self._gen_cmdline(ytid), cwd=stash.dir) == 0

	def parse_video_url(self, url: str):
		"""
		If the provided URL is a unique reference to a youtube ID, return the ID. Otherwise, return None.
		"""
		if "//" not in url:
			url = "https://" + url
		try:
			urp = urllib.parse.urlparse(url)
		except ValueError:
			return None
		if urp is None or urp.scheme not in ("", "http", "https"):
			return None
		if urp.netloc in ("youtube.com", "m.youtube.com", "www.youtube.com"):
			if urp.path != "/watch":
				return None
			videos = urllib.parse.parse_qs(urp.query).get("v","")
			if not videos:
				return None
			video = videos[0]
		elif urp.netloc == "youtu.be":
			video = urp.path.lstrip("/")
		else:
			return None
		if len(video) != 11 or sanitize_ytid(video) != video:
			return None
		return video

	def query_search(self, query, search=True):
		if not query:
			return None
		ytid = self.parse_video_url(query)
		if ytid:
			return [ytid]

		p = subprocess.Popen([self.ytdl_path, "--ignore-errors", "--get-id", "--", query], cwd="/tmp", stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
		out, _ = p.communicate()
		results = out.strip().decode().split('\n')

		if results != ['']:
			return results

		if not search:
			return None
		try:
			return [subprocess.check_output([self.ytdl_path, "--no-playlist", "--get-id", "--", "ytsearch:%s" % query], cwd="/tmp").strip().decode()]
		except:
			return None

	def query_search_multiple(self, query, n=5):
		try:
			lines = subprocess.check_output([self.ytdl_path, "--no-playlist", "--get-id", "--get-title", "--", "ytsearch%d:%s" % (n, query)], cwd="/tmp").strip().decode().split("\n")
			assert len(lines) % 2 == 0
			return [{"title": ai, "ytid": bi} for ai, bi in zip(lines[::2], lines[1::2])]
		except:
			return None


class Volume:
	def __init__(self):
		self.scale = 0.4

	def raw_get_volume(self):
		try:
			elems = subprocess.check_output(["/usr/bin/amixer", "get", "Master"]).decode().split("[")
			elems = [e.split("]")[0] for e in elems]
			elems = [e for e in elems if e.endswith("%")]
			assert len(elems) in (1, 2) and elems[0][-1] == "%"
			return int(elems[0][:-1], 10)
		except:
			return None

	def get_volume(self):
		vol = self.raw_get_volume()
		if vol is None:
			return None
		else:
			return min(100, int(vol / self.scale))

	def set_raw_volume(self, volume):
		try:
			volume = min(100, max(0, volume))
			subprocess.check_call(["/usr/bin/amixer", "set", "Master", "--", "%d%%" % volume])
		except:
			pass

	def set_volume(self, volume):
		self.set_raw_volume(min(100, volume * self.scale))

