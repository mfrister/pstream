#!/usr/bin/env bash
if [ -e production ]; then
	"$(which python)" "$(which twistd)" -l data/streams.log --pidfile data/twistd-streams.pid -y streamsserver.py
else
	sudo "$(which python)" "$(which twistd)" -l- -n -u $(id -u) -g $(id -g) --pidfile twistd-streams.pid -y streamsserver.py $@
fi
