#!/bin/sh

set -eu

PORT=$1
../lightning/cli/lightning-cli --rpc-file=/tmp/light${PORT} listfunds | jq -e .outputs
