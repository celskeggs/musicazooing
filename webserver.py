import cherrypy
import os
import redis
import json
import uuid
import subprocess

redis = redis.Redis()

index_html = """
<!DOCTYPE html>
<html>
<head>
<title>Musicazoo WIP</title>
</head>
<body>
<h1>Musicazoo</h1>
<p>Use this form to queue new videos:</p>
<input type="text" id="youtube_id" placeholder="youtube ID here"> <button id="submit">Queue</button>
<p>Queued items:</p>
<ul id="queue">
<li>Loading...</li>
</ul>
<script>
  (function() {
    function json_request(cb, err, endpoint) {
      var req = new XMLHttpRequest();
      req.addEventListener("load", function() {
        var json = JSON.parse(this.responseText);
        if (json) {
          cb(json);
        } else {
          err("bad json from endpoint " + endpoint);
        }
      });
      req.addEventListener("error", function() {
        err("xhr failed");
      });
      req.open("POST", endpoint, true);
      req.send();
    }
    function default_err(err) {
      console.log("error", err);
    }
    var youtube_id = document.getElementById("youtube_id");
    var submit = document.getElementById("submit");
    var queue = document.getElementById("queue");
    youtube_id.onkeypress = function(e) {
      if (!e) { e = window.event; }
      var keyCode = e.keyCode || e.which;
      if (keyCode == 13) {
        submit.onclick();
        return false;
      }
    };
    submit.onclick = function() {
      if (youtube_id.disabled) { return; }
      youtube_id.disabled = true;
      json_request(function(data) {
        youtube_id.value = "";
        youtube_id.disabled = false;
      }, function(err) {
        console.log(err);
        youtube_id.disabled = false;
      }, "/enqueue?youtube_id=" + encodeURIComponent(youtube_id.value));
    };
    function delete_uuid(x) {
      json_request(function(data) {}, default_err, "/delete?uuid=" + encodeURIComponent(x));
    }
    function refresh() {
      json_request(function(data) {
        var total = "";
        for (var i = 0; i < data.listing.length; i++) {
          total += "<li><span></span> | <button>delete</button></li>";
        }
        queue.innerHTML = total;
        for (var i = 0; i < data.listing.length; i++) {
          var span = queue.children[i].children[0];
          var deleter = queue.children[i].children[1];
          var title = data.listing[i].ytid;
          if (data.titles[title]) {
            title = data.titles[title];
          } else {
            title += " (loading)";
          }
          span.innerText = title;
          deleter.onclick = (function() { delete_uuid(this); }).bind(data.listing[i].uuid);
        }
      }, default_err, "/list");
    };
    setInterval(refresh, 1000);
  })();
</script>
</body>
</html>
"""

def query_search(query):
	try:
		return subprocess.check_output([os.path.join(os.getenv("HOME"), ".local/bin/youtube-dl"), "--get-id", "--", "ytsearch:%s" % query], cwd="/tmp").strip().decode()
	except:
		return None

class Musicazoo:
	def elems(self):
		return [json.loads(ent.decode()) for ent in redis.lrange("musicaqueue", 0, -1)]

	def titles(self, for_ytids):
		mapping = {}
		for ytid in for_ytids:
			value = redis.get("musicatitle.%s" % ytid)
			mapping[ytid] = value.decode() if value else None
		return mapping

	def find(self, uuid):
		found = [ent for ent in redis.lrange("musicaqueue", 0, -1) if json.loads(ent.decode())["uuid"] == uuid]
		assert len(found) <= 1
		return found[0] if found else None

	@cherrypy.expose
	def index(self):
		elems = self.elems()
		return index_html

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def enqueue(self, youtube_id):
		youtube_id = query_search(youtube_id) if youtube_id else None
		if not youtube_id:
			return json.dumps({"success": False})
		redis.rpush("musicaqueue", json.dumps({"ytid": youtube_id, "uuid": str(uuid.uuid4())}))
		redis.rpush("musicaload", youtube_id)
		return {"success": True}

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def list(self):
		elems = self.elems()
		return {"listing": elems, "titles": self.titles(set(elem["ytid"] for elem in elems))}

	@cherrypy.expose
	def delete(self, uuid):
		found = self.find(uuid)
		while found is not None:
			redis.lrem("musicaqueue", found)
			found = self.find(uuid)

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def search(self, q):
		return query_search(q)

cherrypy.config.update({'server.socket_port': 8000})

cherrypy.tree.mount(Musicazoo(), "/")

cherrypy.engine.start()
cherrypy.engine.block()
