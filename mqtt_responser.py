# encoding: utf-8
#   wait invoice request and publish invoice

import paho.mqtt.client
import sys
import json
import traceback
import threading
import time
import os
import signal

from lnnode import LnNode
from ptarm import Ptarm
from ptarmj import PtarmJ
import clightning


MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883

ln_node = ''
node_id = ''
peer_node = []


def _killme():
    os.kill(os.getpid(), signal.SIGKILL)


def on_connect(client, user_data, flags, response_code):
    global node_id

    del user_data, flags, response_code
    node_id = ln_node.get_nodeid()
    print('node_id= ' + node_id)
    client.subscribe('#')
    th = threading.Thread(target=poll_status, args=(client,), name='poll_status')
    th.start()
    print('MQTT connected')


def on_message(client, _, msg):
    try:
        payload = str(msg.payload, 'utf-8')
        if msg.topic == 'request/' + node_id:
            #print('REQUEST[' + msg.topic + ']' + payload)
            exec_request(client, json.loads(payload))
        elif msg.topic == 'notify/' + node_id:
            #print('NOTIFY[' + msg.topic + ']' + payload)
            exec_notify(client, json.loads(payload))
        elif msg.topic == 'stop/' + node_id:
            print('STOP!')
            _killme()
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())


def poll_status(client):
    while True:
        status = []
        for peer in peer_node:
            stat = [str(ln_node.get_status(peer)), peer]
            status.append(stat)
            # print('status=', status)
        res_dict = {'status': status, 'ipaddr': ln_node.ipaddr, 'port': ln_node.port}
        client.publish('status/' + node_id, json.dumps(res_dict))
        time.sleep(10)


def exec_request(client, json_msg):
    method = json_msg['method']
    params = json_msg['params']
    res = ''
    if method == 'invoice':
        res = ln_node.get_invoice(params[0])
    elif method == 'pay':
        res = ln_node.pay(params[0])
    elif method == 'connect':
        res = ln_node.connect(params[0], params[1], params[2])
    elif method == 'openchannel':
        if ln_node.get_status(params[0]) == LnNode.Status.NONE:
            res = ln_node.open_channel(params[0], params[1])
    elif method == 'closechannel':
        if ln_node.get_status(params[0]) == LnNode.Status.NORMAL:
            res = ln_node.close_mutual(params[0])
    else:
        print('method=', method)
    if len(res) > 0:
        print('res=' + res)
        client.publish('response/' + node_id, res)


def exec_notify(client, json_msg):
    global peer_node

    if 'connect' in json_msg:
        for node in json_msg['connect']:
            if (node[0] == node_id) and (node[1] not in peer_node):
                peer_node.append(node[1])
            elif (node[1] == node_id) and (node[0] not in peer_node):
                peer_node.append(node[0])
        # print('peer_node: ', peer_node)


def main():
    mqtt_client = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    mqtt_client.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.loop_forever()


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('usage: ' + sys.argv[0] + ' <ptarm or clightning> <ipaddr> <port> [option]')
        print('    [ptarm option]none')
        print('    [clightning option]rpc-file')
        sys.exit()

    argv = None
    ipaddr = sys.argv[2]
    port = int(sys.argv[3])
    if sys.argv[1] == 'ptarm':
        ln_node = Ptarm()
    elif sys.argv[1] == 'ptarmj':
        ln_node = PtarmJ()
    elif sys.argv[1] == 'clightning':
        ln_node = clightning.CLightning()
        if len(sys.argv) >= 5:
            argv = sys.argv[4]
    else:
        print('unknown lnnode')
        sys.exit()

    ln_node.setup(ipaddr, port, argv)
    main()
