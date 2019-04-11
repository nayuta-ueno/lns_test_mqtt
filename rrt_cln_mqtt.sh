#!/bin/sh
set -eu

TESTNAME=$1
if [ $# -eq 2 ]; then
	PORT=$2
	ADDR=127.0.0.1
else
	PORT=$2
	ADDR=$3
fi
python3 mqtt_responser.py ${TESTNAME} clightning ${ADDR} ${PORT} /tmp/light${PORT}

