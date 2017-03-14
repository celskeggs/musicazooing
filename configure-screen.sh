#!/bin/bash -e
xrandr --newmode "1920x1080_60.00"  173.00  1920 2048 2248 2576  1080 1083 1088 1120 -hsync +vsync || true
xrandr --addmode VGA-1 1920x1080_60.00
xrandr --output LVDS-1 --mode 1440x900 --pos 0x0 --rotate normal --output DVI-D-1 --off --output VGA-1 --mode 1920x1080_60.00 --pos 1440x0 --rotate normal

xset dpms force on  # is this necessary?
xset s off
xset -dpms
