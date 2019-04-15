#!/bin/sh
set -eu

AMOUNT=0.02
PORT=$1
RPC_FILE=/tmp/light${PORT}

#some inputs
if [ $# -eq 2 ]; then
    LOOP=$2
else
    LOOP=1
fi

newaddr() {
    NEWADDR=`../lightning/cli/lightning-cli --rpc-file=${RPC_FILE} newaddr`
    echo ${NEWADDR}
    NEWADDR=`echo ${NEWADDR} | jq -r .address`
    echo ${NEWADDR}
    bitcoin-cli sendtoaddress ${NEWADDR} ${AMOUNT}
}

for i in `seq 0 ${LOOP}`; do
    newaddr
done
