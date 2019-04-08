#!/bin/sh
set -eu

if [ $# -eq 1 ]; then
	PORT=$1
	ADDR=127.0.0.1
else
	PORT=$1
	ADDR=$2
fi
python3 mqtt_responser.py clightning ${ADDR} ${PORT} /tmp/light${PORT}

