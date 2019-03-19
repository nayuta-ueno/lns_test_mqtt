# encoding: utf-8
#   wait invoice request and publish invoice
import subprocess
import time
import sys
import json
import traceback
import os
import signal

import paho.mqtt.client
import socket
import threading


MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883
payer_id = ''
payee_id = ''
dict_recv_node = dict()
dict_status_node = dict()
thread_request = None
loop_reqester = True
is_funding = False


def _killme():
    os.kill(os.getpid(), signal.SIGKILL)


def requester(client):
    global loop_reqester

    while loop_reqester:
        # request invoice: payee
        print('send to payee: invoice')
        client.publish('request/' + payee_id, '{"method":"invoice","params":[ 1000,0 ]}')
        time.sleep(10)
    print('exit requester')


def poll_time(client):
    global dict_recv_node

    while True:
        time.sleep(30)
        if len(dict_recv_node) < 2:
            print('node not found')
            client.publish('stop', 'node not found')
            _killme()
        for node in dict_recv_node:
            if time.time() - dict_recv_node[node] > 60:
                print('node not exist:' + node)
                client.publish('stop', 'node not exist:' + node)
                _killme()


def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('#')
    th = threading.Thread(target=poll_time, args=(client,), name='poll_time', daemon=True)
    th.start()
    print('MQTT connected')


'''
topic:
    'request/' + node_id    : requester --> responser
    'response/' + node_id   : responser ==> requester
    'result/' + node_id     : responser ==> requester
    'stop'
'''
def on_message(client, _, msg):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding

    try:
        #node check(need 2 nodes)
        if msg.topic.startswith('response/') or msg.topic.startswith('status/'):
            if msg.topic.rfind('/') != -1:
                recv_id = msg.topic[msg.topic.rfind('/') + 1:]
                dict_recv_node[recv_id] = time.time()
            else:
                recv_id = ''
        if len(dict_recv_node) != 2:
            return

        #payload
        payload = str(msg.payload, 'utf-8')
        if msg.topic.startswith('response/'):
            print('RESPONSE[' + msg.topic + ']' + payload)
            json_msg = json.loads(payload)
            if msg.topic.endswith(payer_id):
                response_payer(client, json_msg)
                pass
            elif msg.topic.endswith(payee_id):
                response_payee(client, json_msg)
                pass
        elif msg.topic.startswith('result/'):
            print('RESULT[' + msg.topic + ']' + payload)
        elif msg.topic.startswith('status/'):
            json_msg = json.loads(payload)
            dict_status_node[recv_id] = json_msg
            if json_msg['status'] != 'Status.NORMAL':
                print('STATUS[' + msg.topic + ']' + json_msg['status'])
                print('      json_msg=', json_msg)
        elif msg.topic == 'stop':
            print('STOP!')
            _killme()
        else:
            pass
            #print('[' + msg.topic + ']' + payload)


        if len(dict_status_node) != 2:
            return

        if thread_request is None:
            #need 2 normal status nodes
            all_normal = True
            all_none = True
            for node in dict_status_node:
                if dict_status_node[node]['status'] != 'Status.NORMAL':
                    all_normal = False
                elif dict_status_node[node]['status'] != 'Status.NONE':
                    all_none = False
            if all_normal:
                print('start requester thread')
                is_funding = False
                loop_reqester = True
                thread_request = threading.Thread(target=requester, args=(client,), name='requester', daemon=True)
                thread_request.start()
            elif all_none and not is_funding:
                print('start funding: ', dict_status_node[payer_id])
                client.publish('request/' + payee_id, \
                    '{"method":"connect", "params":['
                        '"' + payer_id + '", '
                        '"' + dict_status_node[payer_id]['ipaddr'] + '", ' +\
                        str(dict_status_node[payer_id]['port']) +\
                        ' ]}')
                is_funding = True
        else:
            all_normal = True
            for node in dict_status_node:
                if dict_status_node[node]['status'] != 'Status.NORMAL':
                    all_normal = False
                    break
            if not all_normal:
                print('stop requester thread')
                loop_reqester = False
                thread_request.join()
                thread_request = None
                return
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())


def response_payer(client, json_msg):
    if json_msg['result'][0] == 'pay':
        print('pay start')


'''
{"result": ["invoice", "<BOLT11 invoice>"]}
'''
def response_payee(client, json_msg):
    if json_msg['result'][0] == 'connect':
        if json_msg['result'][1] == 'OK':
            client.publish('request/' + payer_id, '{"method":"openchannel","params":[ "' + payee_id + '", 5000 ]}')
    elif json_msg['result'][0] == 'invoice':
        client.publish('request/' + payer_id, '{"method":"pay","params":[ "' + json_msg['result'][1] + '" ]}')


def linux_cmd_exec(cmd):
    print('cmd:', cmd.split(' '))
    ret = ''
    try:
        ret = subprocess.check_output(cmd.split(' ')).strip()
    except subprocess.CalledProcessError as e:
        print('!!! error happen(errcode=%d) !!!' % e.returncode)
    return ret


def socket_send(req):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('localhost', 9736))
    print('req=' + req)
    client.send(req)
    response = client.recv(4096)
    client.close()
    return response


def main():
    # MQTT brokerと接続
    g_mqtt = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    g_mqtt.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    g_mqtt.on_connect = on_connect
    g_mqtt.on_message = on_message
    g_mqtt.loop_forever()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('usage: ' + sys.argv[0] + ' payer_id payee_id')
        sys.exit()
    payer_id = sys.argv[1]
    payee_id = sys.argv[2]
    if len(payer_id) != 66 or len(payee_id) != 66:
        print('invalid length')
        sys.exit()
    main()
