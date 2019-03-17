#!/bin/bash
set -eu
#   method: htlc_changed
#   $1: short_channel_id
#   $2: node_id
#   $3: local_msat
DATE=`date -u +"%Y-%m-%dT%H:%M:%S.%N"`
JSON=`cat << EOS | jq -e '.'
{ "method":"htlc_changed", "short_channel_id":"$1", "node_id":"$2", "date":"$DATE", "local_msat":$3 }
EOS
`

echo ${JSON}
python3 script/mqtt_pub.py result "${JSON}"

