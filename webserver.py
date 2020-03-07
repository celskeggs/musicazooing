import cherrypy
import os
import mqueue
import pkgutil

skewlist = []

queue = mqueue.Queue()
stash = mqueue.Stash()
fetcher = mqueue.Fetcher()
volume = mqueue.Volume()

try:
	playlist_max = int(os.getenv("MZ_PLAYLIST_MAX") or "20")
except ValueError:
	playlist_max = 20

class Musicazoo:
	def skew(self):
		return cherrypy.request.headers.get("X-Forwarded-For") in skewlist

	@cherrypy.expose
	def index(self):
		return pkgutil.get_data("mqueue", "index.html")

#	@cherrypy.expose
#	def dice(self):
#		cherrypy.response.headers['Content-Type'] = 'image/svg'
#		return dice_svg

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def enqueue(self, youtube_id):
		if self.skew():
			return {"success": False}
		youtube_ids = fetcher.query_search(youtube_id)
		if not youtube_ids:
			return {"success": False}
		for youtube_id in youtube_ids[:playlist_max]:
			queue.enqueue_ytid(youtube_id)
		return {"success": True}

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def status(self):
		ents = queue.read_queue()
		playback_status = queue.playback_status()
		if self.skew():
			playback_status["listing"] = []
			playback_status["titles"] = {}
			playback_status["loaded"] = {}
			playback_status["volume"] = 0
		else:
			playback_status["listing"] = [ent.kvs for ent in ents]
			playback_status["titles"] = {ent.ytid: queue.read_title(ent.ytid) for ent in ents}
			playback_status["loaded"] = {ent.ytid: stash.exists(ent.ytid) for ent in ents}
			playback_status["volume"] = volume.get_volume()
		return playback_status

	@cherrypy.expose
	def delete(self, uuid):
		if self.skew():
			return
		# TODO: why is this a loop?
		while True:
			found = queue.read_queue_by_uuid(uuid)
			if found is None:
				break
			queue.remove(found)

	@cherrypy.expose
	def reorder(self, uuid, dir):
		try:
			rel = 1 if int(dir) >= 0 else -1
		except ValueError:
			return "fail"
		if not queue.move(uuid, rel):
			return "fail"
		return "ok"

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def search(self, q):
		return fetcher.query_search_multiple(q)

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def getvolume(self):
		return volume.get_volume()

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def setvolume(self, vol):
		if self.skew():
			return "ok"
		vol = min(volume.get_volume() + 5, int(vol))
		try:
			volume.set_volume(vol)
			return "ok"
		except ValueError:
			return "fail"

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def pause(self):
		queue.pause()
		return "ok"

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def navigate(self, rel):
		try:
			rel = float(rel)
		except ValueError:
			return "fail"
		queue.navigate(rel)
		return "ok"

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def top(self):
		frequencies = []
		for member, (title, plays) in queue.play_counts():
			frequencies.append((member, title, plays))
		frequencies.sort(reverse=True, key=lambda x: x[2])
		return frequencies

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def random(self):
		youtube_id = queue.random_previous_ytid()
		if not youtube_id:
			return {"success": False}
		youtube_ids = fetcher.query_search(youtube_id, search=False)
		if youtube_ids is None or len(youtube_ids) != 1:
			return {"success": False}
		youtube_id = youtube_ids[0]
		queue.enqueue_ytid(youtube_id, increment=False)
		return {"success": True, "ytid": youtube_id}

cherrypy.config.update({'server.socket_port': 8000})

cherrypy.tree.mount(Musicazoo(), os.getenv("MZ_LOCATION") or "/", config={
	"/images": {
		"tools.staticdir.on": True,
		"tools.staticdir.dir": os.path.abspath(os.path.join(os.path.dirname(__file__), "images")),
	},
	"/video": {
		"tools.staticdir.on": True,
		"tools.staticdir.dir": os.path.abspath(stash.dir),
	},
})

if __name__ == "__main__":
	cherrypy.engine.start()
	cherrypy.engine.block()
