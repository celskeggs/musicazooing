import cherrypy
import random
import time
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
<style>
body {
	color: #f3fde1;
	background-color: #406873;
}
</style>
</head>
<body>
<h1>Musicazoo</h1>
Musicazoo has been disabled until the end of the party.
</body>
</html>
"""

class Musicazoo:
	@cherrypy.expose
	def index(self):
		return index_html

cherrypy.config.update({'server.socket_port': 8080})

cherrypy.tree.mount(Musicazoo(), os.getenv("MZ_LOCATION") or "/")

cherrypy.engine.start()
cherrypy.engine.block()
