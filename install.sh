#!/bin/bash -e

cd $(dirname $0)
HERE=$(pwd)

. ./config.env

mkdir -p $HOME/.config/systemd/user

for x in webserver.service downloader.service player.service button.service
do
	cat $HERE/$x | sed "s|DIR|$HERE|g" >$HOME/.config/systemd/user/$x
done

cat $HERE/nginx-site | sed "s|DIR|$MZ_LOCATION|" | sudo tee /etc/nginx/sites-available/musicazoo > /dev/null

pip3 install --user --upgrade cherrypy youtube-dl redis pyserial

sudo systemctl start redis-server
systemctl daemon-reload --user
systemctl enable --user webserver downloader player
systemctl start --user webserver downloader player
if [ "$MZ_BUTTON" == "true" ]
then
	systemctl enable --user button
	systemctl start --user button
fi
