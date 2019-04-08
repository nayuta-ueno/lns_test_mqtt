#!/bin/sh
set -eu

if [ $# -eq 1 ]; then
	PORT=$1
	ADDR=127.0.0.1
else
	PORT=$1
	ADDR=$2
fi

rm -rf rt${PORT}
./lightningd/lightningd --network=regtest --lightning-dir=rt${PORT} --addr=${ADDR}:${PORT} --log-level=debug --rpc-file=/tmp/light${PORT}

