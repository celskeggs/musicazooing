#!/bin/bash -e

cd $(dirname $0)
HERE=$(pwd)

mkdir -p $HOME/.config/systemd/user

for x in webserver.service downloader.service player.service
do
	cat $HERE/$x | sed "s|DIR|$HERE|" >$HOME/.config/systemd/user/$x
done

systemctl daemon-reload --user
