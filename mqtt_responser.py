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
import configparser


config = configparser.ConfigParser()

TOPIC_PREFIX = ''
ln_node = ''
node_id = ''
peer_node = []


def _killme():
    # https://stackoverflow.com/questions/12919980/nohup-is-not-writing-log-to-output-file
    sys.stdout.flush()
    os.kill(os.getpid(), signal.SIGKILL)


def on_connect(client, user_data, flags, response_code):
    global node_id

    del user_data, flags, response_code
    node_id = ln_node.get_nodeid()
    print('node_id= ' + node_id)
    client.subscribe(TOPIC_PREFIX + '/#')
    th = threading.Thread(target=poll_status, args=(client,), name='poll_status')
    th.start()
    print('MQTT connected')


def on_message(client, _, msg):
    try:
        payload = str(msg.payload, 'utf-8')
        if msg.topic == TOPIC_PREFIX + '/request/' + node_id:
            #print('REQUEST[' + msg.topic + ']' + payload)
            exec_request(client, json.loads(payload))
        elif msg.topic == TOPIC_PREFIX + '/notify/' + node_id:
            #print('NOTIFY[' + msg.topic + ']' + payload)
            exec_notify(client, json.loads(payload))
        elif msg.topic == TOPIC_PREFIX + '/stop/' + node_id:
            print('STOP!')
            _killme()
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())


def poll_status(client):
    while True:
        status = []
        for peer in peer_node:
            st, local_msat = ln_node.get_status(peer)
            stat = [str(st), peer, local_msat]
            status.append(stat)
            # print('status=', status)
        res_dict = {'status': status, 'ipaddr': ln_node.ipaddr, 'port': ln_node.port, 'name': ln_node.get_name()}
        client.publish(TOPIC_PREFIX + '/status/' + node_id, json.dumps(res_dict))

        # https://stackoverflow.com/questions/12919980/nohup-is-not-writing-log-to-output-file
        sys.stdout.flush()

        time.sleep(10)


def exec_request(client, json_msg):
    method = json_msg['method']
    params = json_msg['params']
    res = ''
    if method == 'invoice':
        if len(params) == 1:
            res = ln_node.get_invoice(params[0])
        else:
            res = ln_node.get_invoice(params[0], params[1])
    elif method == 'pay':
        res = ln_node.pay(params[0])
    elif method == 'connect':
        res = ln_node.connect(params[0], params[1], params[2])
    elif method == 'disconnect':
        res = ln_node.disconnect(params[0])
    elif method == 'openchannel':
        if ln_node.get_status(params[0])[0] == LnNode.Status.NONE:
            res = ln_node.open_channel(params[0], params[1])
    elif method == 'closechannel':
        if ln_node.get_status(params[0])[0] == LnNode.Status.NORMAL:
            res = ln_node.close_mutual(params[0])
    elif method == 'closechannel_force':
        if ln_node.get_status(params[0])[0] == LnNode.Status.NORMAL:
            res = ln_node.close_force(params[0])
    else:
        print('unknown method=', method)
    if len(res) > 0:
        print('res=' + res)
        client.publish(TOPIC_PREFIX + '/response/' + node_id, res)


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
    host = config.get('MQTT', 'BROKER_URL')
    port = config.getint('MQTT', 'BROKER_PORT')
    mqtt_client = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    mqtt_client.connect(host, port=port, keepalive=60)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.loop_forever()


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('usage: ' + sys.argv[0] + ' <INI FILENAME> <ptarm or clightning> <ipaddr> <port> [option]')
        print('    [ptarm option]none')
        print('    [clightning option]rpc-file')
        sys.exit()

    argv = None

    config.read('./config.ini')
    testname = sys.argv[1]
    TOPIC_PREFIX = config.get(testname, 'TOPIC_PREFIX')

    if sys.argv[2] == 'ptarm':
        ln_node = Ptarm()
    elif sys.argv[2] == 'ptarmj':
        ln_node = PtarmJ()
    elif sys.argv[2] == 'clightning':
        ln_node = clightning.CLightning()
        if len(sys.argv) >= 6:
            argv = sys.argv[5]
    else:
        print('unknown lnnode')
        sys.exit()
    ipaddr = sys.argv[3]
    port = int(sys.argv[4])

    ln_node.setup(ipaddr, port, argv)
    main()
