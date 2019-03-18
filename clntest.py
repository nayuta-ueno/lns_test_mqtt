# encoding: utf-8
#   wait invoice request and publish invoice

import paho.mqtt.client
import sys
import json
import traceback

import lnnode
import ptarm
import clightning


ln_node = clightning.CLightning()
ln_node.setup()
status = ln_node.get_status()
print(status)
