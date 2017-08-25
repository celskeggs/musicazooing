#!/bin/bash -e
WW=1920
HH=1080
# HH=720
# HH=$((${WW} * 5625 / 10000))
RR=60
CVT=$(cvt $WW $HH $RR | tail -n 1 | cut -d " " -f 2-)
CNAME=$(echo $CVT | cut -d " " -f 1)
xrandr --newmode ${CVT} 2>/dev/null || true
# xrandr --newmode "${WW}x1080_60.00"  173.00  ${WW} 2048 2248 2576  1080 1083 1088 1120 -hsync +vsync || true
xrandr --addmode VGA1 ${CNAME}
xrandr --output VGA1 --mode ${CNAME} --pos 0x0 --rotate normal

xset dpms force on  # is this necessary?
xset s off
xset -dpms
