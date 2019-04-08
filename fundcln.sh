#!/bin/sh

set -eu

../lightning/cli/lightning-cli --rpc-file=/tmp/light$1 listfunds

