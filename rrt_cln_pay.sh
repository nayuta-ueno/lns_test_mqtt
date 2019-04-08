#!/bin/sh
set -eu

bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light$1 newaddr | jq -r .address` 0.01
