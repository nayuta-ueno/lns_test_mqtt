#!/bin/sh
set -eu

PORT=$1
bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light${PORT} newaddr | jq -r .address` 0.01
