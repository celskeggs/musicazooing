#!/bin/bash
set -e -u

cd "$HOME/musicazoo_videos"

if [[ "$(df . --output=pcent | tail -n 1 | sed 's/%//')" -gt 90 ]]
then
	echo "current state is full:"
	du -hs
	echo "removing files..."
	rm -f -- $(wc -c -- * | sort -n | tail -n 30 | tr -s " " " " | cut -d " " -f 3)
	echo "removed! final state:"
	du -hs
	echo "done."
fi
