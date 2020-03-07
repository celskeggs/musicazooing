import traceback
import mqueue

queue = mqueue.Queue()
fetcher = mqueue.Fetcher()
stash = mqueue.Stash()
stash.create_datadir_if_missing()


def rebuild_loading_queue():
	queue.clear_loading_queue()

	for ent in queue.read_queue():
		queue.request_load_video(ent.ytid)


def try_load_one(to_load_ytid):
	title = queue.read_title(to_load_ytid)
	# TODO: stop using title as marker of loading state...
	if title is None or title.startswith("Could not load video "):
		queue.set_title(to_load_ytid, fetcher.get_title(to_load_ytid))
	if not stash.exists(to_load_ytid):
		if not fetcher.download_into(to_load_ytid, stash):
			queue.set_title(to_load_ytid, ("Could not load video %s" % to_load_ytid).encode())
		else:
			assert stash.exists(to_load_ytid)


def loading_loop():
	while True:
		to_load_ytid = queue.take_loading_queue()
		try:
			try_load_one(to_load_ytid)
		except:
			print("Failed to load.")
			traceback.print_exc()


if __name__ == "__main__":
	rebuild_loading_queue()
	loading_loop()

