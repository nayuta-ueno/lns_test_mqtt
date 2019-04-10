#!/bin/sh
set -eu

AMOUNT=0.05
PORT=$1
bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light${PORT} newaddr | jq -r .address` ${AMOUNT}
