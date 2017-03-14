#!/bin/bash -e

cd $(dirname $0)
HERE=$(pwd)

mkdir -p $HOME/.config/systemd/user

for x in webserver.service downloader.service player.service
do
	cat $HERE/$x | sed "s|DIR|$HERE|" >$HOME/.config/systemd/user/$x
done

pip3 install --user --upgrade cherrypy youtube-dl redis

sudo systemctl start redis-server
systemctl daemon-reload --user
systemctl enable --user webserver downloader player
systemctl start --user webserver downloader player
