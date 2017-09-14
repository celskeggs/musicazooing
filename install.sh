#!/bin/bash -e

cd $(dirname $0)
HERE=$(pwd)

. ./config.env


echo "=> Installing debian packages"
sudo apt-get update
sudo apt-get install python3-pip nginx redis-server mplayer


echo "=> Installing pip packages"
pip3 install --user --upgrade cherrypy youtube-dl redis pyserial mplayer.py


echo "=> Creating systemd services"
mkdir -p $HOME/.config/systemd/user

for x in webserver.service downloader.service player.service button.service
do
	cat $HERE/$x | sed "s|DIR|$HERE|g" >$HOME/.config/systemd/user/$x
done


echo "=> Setting up nginx web server"
cat $HERE/nginx-site | sed "s|DIR|$MZ_LOCATION|" | sudo tee /etc/nginx/sites-available/musicazoo > /dev/null
sudo ln -sf /etc/nginx/sites-available/musicazoo /etc/nginx/sites-enabled/musicazoo


echo "=> Disabling unwanted programs"
killall -q xscreensaver
echo -n > $HOME/.config/lxsession/LXDE/autostart


echo "=> Starting systemd services"
sudo systemctl restart redis-server nginx
sudo loginctl enable-linger $USER
systemctl daemon-reload --user
systemctl enable --user webserver downloader player
systemctl restart --user webserver downloader player
if [ "$MZ_BUTTON" == "true" ]
then
	systemctl enable --user button
	systemctl restart --user button
fi
