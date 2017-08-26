from urllib.request import urlopen
from urllib.parse import quote
import json
import sys
import serial

def get_status():
	return json.loads(urlopen("http://musicazoo.mit.edu/list").read().decode("utf-8"))

def enqueue(query):
	response = json.loads(urlopen("http://musicazoo.mit.edu/enqueue?youtube_id={}".format(quote(query)), data=b"").read().decode("utf-8"))
	return response["success"]

def delete(uuid):
	urlopen("http://musicazoo.mit.edu/delete?uuid={}".format(uuid), data=b"")

port = serial.Serial("/dev/ttyACM0", 115200, timeout=1)

while True:
	line = port.readline().strip()
	if line and line.isdigit():
		press_length = int(line)
		if press_length < 2000:
			urlopen("http://musicazoo.mit.edu/random").read()
		elif press_length > 7000:
			enqueue("A5-kJMeKysU")
		else:
			listing = get_status()["listing"]
			if listing:
				delete(listing[0]["uuid"])
