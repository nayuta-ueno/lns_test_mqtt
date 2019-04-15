#!/bin/sh
set -eu

PORT=$1
RPC_FILE=/tmp/light${PORT}
LISTFUNDS=`../lightning/cli/lightning-cli --rpc-file=${RPC_FILE} listfunds`
echo ${LISTFUNDS} | jq -e .outputs
