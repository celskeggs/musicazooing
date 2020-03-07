import cherrypy
import os
import pkgutil

index_html = pkgutil.get_data("mqueue", "nope.html")

class Musicazoo:
	@cherrypy.expose
	def index(self):
		return index_html

cherrypy.config.update({'server.socket_port': 8000})

cherrypy.tree.mount(Musicazoo(), os.getenv("MZ_LOCATION") or "/")

cherrypy.engine.start()
cherrypy.engine.block()

