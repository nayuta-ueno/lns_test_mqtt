#!/bin/bash
set -eu
#   method: fail
#   $1: short_channel_id
#   $2: node_id
#   $3: info
DATE=`date -u +"%Y-%m-%dT%H:%M:%S.%N"`
JSON=`cat << EOS | jq -e '.'
{ "method":"fail", "short_channel_id":"$1", "node_id":"$2", "date":"$DATE", "info":"$3" }
EOS
`

echo ${JSON} | jq .
python3 script/mqtt_pub.py stop "${JSON}"
