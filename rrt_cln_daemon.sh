#!/bin/sh
set -eu

rm -rf rt$1
./lightningd/lightningd --network=regtest --lightning-dir=rt$1 --addr=127.0.0.1:$1$1$1$1 --log-level=debug --rpc-file=/tmp/light$1

