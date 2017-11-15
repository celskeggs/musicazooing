import os
import json
import time
import datetime

import alphasign

sign = alphasign.Serial(device=os.environ["MZ_SIGN_PORT"])
sign.connect()
sign.clear_memory()

name_str = alphasign.String(size=50, label="1")
time_str = alphasign.String(size=20, label="2")
playing_text = alphasign.Text(
        "Now Playing: {}    {}".format(name_str.call(), time_str.call()),
        label="A",
        mode=alphasign.mode.ROLL_LEFT
)

sign_objs = (name_str, time_str, playing_text)
sign.allocate(objs)
sign.set_run_sequence((playing_text,))

for obj in sign_objs:
    sign.write(obj)

redis = redis.Redis()

while True:
    quent = redis.lindex("musicaqueue", 0)
    if quent is None:
        continue

    title = redis.get("musicatitle." + quent['ytid'])
    status = json.loads(redis.get("musicastatus"))

    elapsed = str(datetime.timedelta(seconds=status['time']))
    total = str(datetime.timedelta(seconds=status['length']))
    time_str.data = "elapsed / total"
    sign.write(time_str)

    name_str.data = title
    sign.write(name_str)

    time.sleep(0.5)
