# encoding: utf-8
'''
funder---fundee

    while True:
        [fundee => funder]connect
        [funder => fundee]open_channel
        ...
        for 5:
            [fundee]invoice
            [funder]pay
        [fundee => funder]close_channel
        ...
'''

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


# MQTT broker
MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883
PAY_COUNT_MAX = 5

# global variable
TESTNAME = 'test1'      # publish my stoppage order
NODE_NUM = 2
FUNDER=0
FUNDEE=1
NODE_LABEL = ['funder', 'fundee']

node_id = [''] * NODE_NUM
dict_recv_node = dict()
dict_status_node = dict()
thread_request = None
loop_reqester = True
is_funding = 0      # 0:none, 1:connecting, 2:funding
funding_count = 0
pay_count = 0


# MQTT: connect
def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('#')
    #th = threading.Thread(target=poll_time, args=(client,), name='poll_time', daemon=True)
    #th.start()
    print('MQTT connected')


# MQTT: message subscribed
def on_message(client, _, msg):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count

    # topic
    #   'request/' + node_id    : requester --> responser
    #   'response/' + node_id   : responser ==> requester
    #   'stop/ + node_id        : requester --> responser'
    ret, recv_id = proc_topic(client, msg)
    if not ret:
        return

    # payload
    proc_payload(client, msg, recv_id)

    # status
    proc_status(client, msg, recv_id)


# check status health
#   起動して30秒以内にテスト対象のnode全部がstatusを送信すること
#   テスト対象のnodeは、60秒以内にstatusを毎回送信すること
def poll_time(client):
    global dict_recv_node

    stop_order = False
    while not stop_order:
        time.sleep(30)
        if len(dict_recv_node) < NODE_NUM:
            print('node not found')
            stop_order = True
            break
        for node in dict_recv_node:
            if time.time() - dict_recv_node[node] > 60:
                print('node not exist:' + node)
                stop_order = True
                break
    if stop_order:
        print('!!! stop order: poll_time')
        _stop(client)


# request check
def requester(client):
    global loop_reqester, pay_count

    while loop_reqester:
        print('payed:' + str(pay_count))
        if pay_count < PAY_COUNT_MAX:
            # request invoice: payee
            print('send to payee: invoice')
            client.publish('request/' + node_id[FUNDEE], '{"method":"invoice","params":[ 1000,0 ]}')
            pay_count += 1
            time.sleep(10)      # 送金の完了にかかわらず要求する。実環境に合わせて時間を調整しよう。
        else:
            # 一定回数送金要求したらチャネルを閉じる
            pay_count = 0
            client.publish('request/' + node_id[FUNDEE], '{"method":"closechannel", "params":[ "' + node_id[FUNDER] + '" ]}')
            print('CLOSE CHANNEL')
            break
    print('exit requester')


# topic
#   check our testing node_ids
def proc_topic(client, msg):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count

    if msg.topic == 'stop/' + TESTNAME:
        print('STOP!')
        _killme()

    ret = False
    mine = False
    recv_id = ''
    try:
        if msg.topic.startswith('response/') or msg.topic.startswith('status/'):
            if msg.topic.rfind('/') != -1:
                recv_id = msg.topic[msg.topic.rfind('/') + 1:]
                for i in range(NODE_NUM):
                    if node_id[i] == recv_id:
                        mine = True
                        dict_recv_node[recv_id] = time.time()
                        break
        if mine and (len(dict_recv_node) == NODE_NUM):
            ret = True
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())
        print('topic=', msg.topic)

    return ret, recv_id


# payload
def proc_payload(client, msg, recv_id):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count

    ret = True
    payload = ''
    try:
        #payload
        payload = str(msg.payload, 'utf-8')
        if len(payload) == 0:
            return
        if msg.topic.startswith('response/'):
            ret = message_response(client, json.loads(payload), msg, recv_id)
        elif msg.topic.startswith('status/'):
            message_status(client, json.loads(payload), msg, recv_id)
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())
        print('payload=', payload)
    if not ret:
        print('!!! False: proc_payload')
        _stop(client)


# process for status
def proc_status(client, msg, recv_id):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count

    if len(dict_status_node) != 2:
        return

    try:
        if thread_request is None:
            #need 2 normal status nodes
            all_normal = True
            all_none = True
            all_funding = True
            for node in dict_status_node:
                if dict_status_node[node]['status'] != 'Status.NORMAL':
                    all_normal = False
                if dict_status_node[node]['status'] != 'Status.NONE':
                    all_none = False
                if dict_status_node[node]['status'] != 'Status.FUNDING':
                    all_funding = False
            if all_normal:
                print('start requester thread')
                is_funding = 0
                loop_reqester = True
                thread_request = threading.Thread(target=requester, args=(client,), name='requester', daemon=True)
                thread_request.start()
            elif all_none and is_funding == 0:
                proc_status_funding(client)
            if all_funding:
                is_funding = 2
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


#################################################################################

def proc_status_funding(client):
    global is_funding

    print('REQ: connect: ' + node_id[FUNDEE] + ' ==> ' + node_id[FUNDER])
    is_funding = 1
    funder_ipaddr = dict_status_node[node_id[FUNDER]]['ipaddr']
    funder_port = dict_status_node[node_id[FUNDER]]['port']
    client.publish('request/' + node_id[FUNDEE], \
        '{"method":"connect", "params":['
            '"' + node_id[FUNDER] + '", '
            '"' + funder_ipaddr + '", ' + str(funder_port) + ' ]}')


# message: topic="response/#"
def message_response(client, json_msg, msg, recv_id):
    ret = True
    if msg.topic.endswith(node_id[FUNDER]):
        ret = message_response_funder(client, json_msg)
    elif msg.topic.endswith(node_id[FUNDEE]):
        ret = message_response_fundee(client, json_msg)
    else:
        ret = False
    return ret


# message: topic="response/[funder]"
def message_response_funder(client, json_msg):
    global funding_count, pay_count

    ret = True
    print('response_funder=' + json_msg['result'][0] + ' param[1]=' + json_msg['result'][1])
    if json_msg['result'][0] == 'openchannel':
        if json_msg['result'][1] == 'OK':
            funding_count += 1
            print('funding start: ' + str(funding_count))
        else:
            print('funding fail: ' + json_msg['result'][1] + '(' + str(funding_count) + ')')
            ret = False
    if json_msg['result'][0] == 'pay':
        if json_msg['result'][1] == 'OK':
            print('pay start: ', str(pay_count))
        else:
            print('pay fail: ' + json_msg['result'][1])
            ret = False
    return ret


# message: topic="response/[fundee]"
def message_response_fundee(client, json_msg):
    global is_funding

    ret = True
    if json_msg['result'][0] == 'connect':
        if json_msg['result'][1] == 'OK':
            client.publish('request/' + node_id[FUNDER], '{"method":"openchannel","params":[ "' + node_id[FUNDEE] + '", 50000 ]}')
        else:
            print('fail connect')
            is_funding = 0
            # ret = False   # close直後はありがちなので、スルー
            time.sleep(5)
    elif json_msg['result'][0] == 'invoice':
        if json_msg['result'][1] == 'NG':
            print('fail invoice')
            ret = False
        else:
            client.publish('request/' + node_id[FUNDER], '{"method":"pay","params":[ "' + json_msg['result'][1] + '" ]}')
    return ret

#################################################################################


# message: topic="status/#"
def message_status(client, json_msg, msg, recv_id):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count

    dict_status_node[recv_id] = json_msg
    if json_msg['status'] != 'Status.NORMAL':
        print('STATUS[' + msg.topic + ']' + json_msg['status'])
        print('      json_msg=', json_msg, ' is_funding=', is_funding)


def _stop(client):
    for node in node_id:
        print('stop: ' + node)
        client.publish('stop/' + node, 'stop all')
    client.publish('stop/' + TESTNAME, 'stop all')


def _killme():
    os.kill(os.getpid(), signal.SIGKILL)


# def linux_cmd_exec(cmd):
#     print('cmd:', cmd.split(' '))
#     ret = ''
#     try:
#         ret = subprocess.check_output(cmd.split(' ')).strip()
#     except subprocess.CalledProcessError as e:
#         print('!!! error happen(errcode=%d) !!!' % e.returncode)
#     return ret


def main():
    # MQTT brokerと接続
    g_mqtt = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    g_mqtt.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    g_mqtt.on_connect = on_connect
    g_mqtt.on_message = on_message
    g_mqtt.loop_forever()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('usage: ' + sys.argv[0] + ' node_id[FUNDER] node_id[FUNDEE]')
        sys.exit()
    node_id[FUNDER] = sys.argv[1]
    node_id[FUNDEE] = sys.argv[2]
    if len(node_id[FUNDER]) != 66 or len(node_id[FUNDEE]) != 66:
        print('invalid length')
        sys.exit()
    print(NODE_LABEL[FUNDER] + '= ' + node_id[FUNDER])
    print(NODE_LABEL[FUNDEE] + '= ' + node_id[FUNDEE])
    main()
