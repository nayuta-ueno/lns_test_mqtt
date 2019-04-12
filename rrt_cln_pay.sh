#!/bin/sh
set -eu

#some inputs

AMOUNT=0.02
PORT=$1
bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light${PORT} newaddr | jq -r .address` ${AMOUNT}
bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light${PORT} newaddr | jq -r .address` ${AMOUNT}
bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light${PORT} newaddr | jq -r .address` ${AMOUNT}
bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light${PORT} newaddr | jq -r .address` ${AMOUNT}
bitcoin-cli sendtoaddress `../lightning/cli/lightning-cli  --rpc-file=/tmp/light${PORT} newaddr | jq -r .address` ${AMOUNT}
