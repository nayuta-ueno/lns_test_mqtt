# encoding: utf-8
'''
node1---hop---node2

    while True:
        [node1 => hop]connect
        [node2 => hop]connect
        [node1 => hop]open_channel
        [hop => node2]open_channel
        ...
        for 10:
            [node2]invoice
            [node1]pay
        [hop => node1]close_channel
        [hop => node2]close_channel
        ...
'''

import subprocess
import time
import sys
import json
import traceback
import os
import signal
import random
import string

import paho.mqtt.client
import socket
import threading


# MQTT broker
MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883

# random requester name
TESTNAME = ''.join([random.choice(string.ascii_letters + string.digits) for i in range(16)])

# const variable
FUNDING_WAIT_MAX = 10   # funding_wait_countの上限
FUNDING_NONE = 0
FUNDING_WAIT = 1
FUNDING_NOW = 2

# const variable
NODE_NUM = 3
NODE1=0
HOP=1
NODE2=2
NODE_LABEL = ['node1', 'hop', 'node2']
PAY_COUNT_MAX = 10
NODE_CONNECT = [ [NODE1, HOP], [NODE2, HOP] ]

# global variable
node_id = [''] * NODE_NUM
dict_recv_node = dict()
dict_status_node = dict()
thread_request = None
loop_reqester = True
is_funding = FUNDING_NONE   # 0:none, 1:connecting, 2:funding
funding_wait_count = 0      # is_fundingが1になったままのカウント数
pay_count = 0
funded_block_count = 0


# MQTT: connect
def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('#')
    th = threading.Thread(target=poll_time, args=(client,), name='poll_time', daemon=True)
    th = threading.Thread(target=notifier, args=(client,), name='notifier', daemon=True)
    th.start()
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


def notifier(client):
    while True:
        # notify
        conn_dict = { "connect": json_node_connect() }
        for node in node_id:
            # print('notify: ' + node)
            client.publish('notify/' + node, json.dumps(conn_dict))
        time.sleep(5)


# check status health
#   起動して30秒以内にテスト対象のnode全部がstatusを送信すること
#   テスト対象のnodeは、60秒以内にstatusを毎回送信すること
def poll_time(client):
    global dict_recv_node, funding_wait_count

    stop_order = False
    while not stop_order:
        time.sleep(30)

        # check health
        if len(dict_recv_node) < NODE_NUM:
            print('node not found')
            stop_order = True
            break
        for node in dict_recv_node:
            if time.time() - dict_recv_node[node] > 60:
                print('node not exist:' + node)
                stop_order = True
                break
        if is_funding == FUNDING_WAIT:
            funding_wait_count += 1
            print('funding_wait_count=' + str(funding_wait_count))
            if funding_wait_count > FUNDING_WAIT_MAX:
                print('funding not started long time')
                stop_order = True
                break
    if stop_order:
        print('!!! stop order: poll_time')
        publish_stop(client)


# topic
#   check our testing node_ids
def proc_topic(client, msg):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count

    if msg.topic == 'stop/' + TESTNAME:
        print('STOP!')
        kill_me()

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
        publish_stop(client)


# process for status
def proc_status(client, msg, recv_id):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count, funded_block_count

    if len(dict_status_node) != NODE_NUM:
        return

    try:
        if thread_request is None:
            all_normal = True
            all_none = True
            all_funding = True
            for node in dict_status_node:
                for status in dict_status_node[node]['status']:
                    # print('status=' + status[0])
                    if status[0] != 'Status.NORMAL':
                        all_normal = False
                    if status[0] != 'Status.NONE':
                        all_none = False
                    if status[0] != 'Status.FUNDING':
                        all_funding = False
            if all_normal:
                print('start requester thread')
                funded_block_count = getblockcount()    #announcement計測用
                is_funding = FUNDING_NONE
                loop_reqester = True
                thread_request = threading.Thread(target=requester, args=(client,), name='requester', daemon=True)
                thread_request.start()
            elif all_none and is_funding == FUNDING_NONE:
                proc_connect_start(client)
            if all_funding:
                is_funding = FUNDING_NOW
        else:
            all_normal = True
            for node in dict_status_node:
                for status in dict_status_node[node]['status']:
                    if status[0] != 'Status.NORMAL':
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

# request check
def requester(client):
    global loop_reqester, pay_count

    while loop_reqester:
        print('payed:' + str(pay_count))
        if pay_count < PAY_COUNT_MAX:
            # request invoice
            log_print('[REQ]invoice')
            client.publish('request/' + node_id[NODE2], '{"method":"invoice","params":[ 1000,0 ]}')
            pay_count += 1
            time.sleep(10)      # 送金の完了にかかわらず要求する。実環境に合わせて時間を調整しよう。
        else:
            # 一定回数送金要求したらチャネルを閉じる
            log_print('[REQ]close all')
            pay_count = 0
            client.publish('request/' + node_id[HOP], '{"method":"closechannel", "params":[ "' + node_id[NODE1] + '" ]}')
            client.publish('request/' + node_id[HOP], '{"method":"closechannel", "params":[ "' + node_id[NODE2] + '" ]}')
            break
    print('exit requester')


def proc_connect_start(client):
    global is_funding

    is_funding = FUNDING_WAIT

    for conn in NODE_CONNECT:
        connector = node_id[conn[0]]
        connectee = node_id[conn[1]]
        log_print('[REQ]connect: ' + NODE_LABEL[conn[0]] + '=>' + NODE_LABEL[conn[1]])
        ipaddr = dict_status_node[connectee]['ipaddr']
        port = dict_status_node[connectee]['port']
        client.publish('request/' + connector, \
            '{"method":"connect", "params":['
                '"' + connectee + '", '
                '"' + ipaddr + '", ' + str(port) + ' ]}')


def proc_connected(client, json_msg, msg, recv_id):
    log_print('[RESPONSE]connect-->[REQ]open ' + node2label(recv_id) + '..' + node2label(json_msg['result'][2]))
    if recv_id == node_id[NODE1]:
        client.publish('request/' + node_id[NODE1],
                '{"method":"openchannel","params":[ "' + node_id[HOP] + '", 50000 ]}')
    elif recv_id == node_id[NODE2]:
        client.publish('request/' + node_id[HOP],
                '{"method":"openchannel","params":[ "' + node_id[NODE2] + '", 50000 ]}')


def proc_invoice_got(client, json_msg, msg, recv_id):
    log_print('[RESPONSE]invoice-->[REQ]pay')
    client.publish('request/' + node_id[NODE1],
            '{"method":"pay","params":[ "' + json_msg['result'][1] + '" ]}')


#################################################################################

def close_all(client):
    for conn in NODE_CONNECT:
        closer = node_id[conn[0]]
        closee = node_id[conn[1]]
        log_print('[REQ]close: ' + NODE_LABEL[conn[0]] + '=>' + NODE_LABEL[conn[1]])
        client.publish('request/' + closer, '{"method":"closechannel", "params":[ "' + closee + '" ]}')


# message: topic="response/#"
def message_response(client, json_msg, msg, recv_id):
    global connect_num, pay_count, is_funding

    ret = True
    if json_msg['result'][0] == 'connect':
        if json_msg['result'][1] == 'OK':
            log_print('connected: ' + node2label(json_msg['result'][2]))
            proc_connected(client, json_msg, msg, recv_id)
        else:
            log_print('fail connect: ' + node2label(json_msg['result'][2]))
            is_funding = FUNDING_NONE
            # ret = False   # close直後はありがちなので、スルー
            time.sleep(5)

    elif json_msg['result'][0] == 'openchannel':
        if json_msg['result'][1] == 'OK':
            log_print('funding start: ' + node2label(json_msg['result'][2]))
        else:
            log_print('funding fail: ' + node2label(json_msg['result'][2]))
            ret = False

    elif json_msg['result'][0] == 'closechannel':
        if json_msg['result'][1] == 'OK':
            log_print('closing start: ' + node2label(json_msg['result'][2]))
        else:
            log_print('closing fail: ' + node2label(json_msg['result'][2]))
            ret = False

    elif json_msg['result'][0] == 'invoice':
        if json_msg['result'][1] == 'NG':
            log_print('fail invoice')
            ret = False
        else:
            proc_invoice_got(client, json_msg, msg, recv_id)

    elif json_msg['result'][0] == 'pay':
        if json_msg['result'][1] == 'OK':
            log_print('pay start: ' + str(pay_count))
        else:
            blk = getblockcount()
            # announcementは 6 confirm以降で展開なので、少し余裕を持たせる
            if blk - funded_block_count > 8:
                log_print('pay fail: ' + json_msg['result'][1])
                ret = False
            else:
                print('pay fail: through(' + str(blk - funded_block_count) + ')')

    if not ret:
        log_print('!!! False: message_response')
        publish_stop(client)

    return ret


# message: topic="status/#"
def message_status(client, json_msg, msg, recv_id):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester, is_funding, pay_count

    dict_status_node[recv_id] = json_msg
    if json_msg['status'] != 'Status.NORMAL':
        pass
        #print('STATUS[' + msg.topic + ']' + json_msg['status'])
        #print('      json_msg=', json_msg, ' is_funding=', is_funding)


def publish_stop(client):
    for node in node_id:
        print('stop: ' + node)
        client.publish('stop/' + node, 'stop all')
    client.publish('stop/' + TESTNAME, 'stop all')


def kill_me():
    os.kill(os.getpid(), signal.SIGKILL)


def log_print(msg):
    print('#####################')
    print('# ' + msg)
    print('#####################')


def node2label(id):
    num = 0
    for node in node_id:
        if node == id:
            return NODE_LABEL[num]
        num += 1
    return '???'


def json_node_connect():
    json_conn = []
    for lists in NODE_CONNECT:
        pair = [ node_id[lists[0]], node_id[lists[1]] ]
        json_conn.append(pair)
    return json_conn


def getblockcount():
    cnt = linux_cmd_exec('bitcoin-cli getblockcount')
    if cnt is not None:
        return int(cnt)
    else:
        return 0


def linux_cmd_exec(cmd):
    print('cmd:', cmd.split(' '))
    ret = ''
    try:
        ret = subprocess.check_output(cmd.split(' ')).strip().decode('utf-8')
    except subprocess.CalledProcessError as e:
        print('!!! error happen(errcode=%d) !!!' % e.returncode)
    return ret


def main():
    # MQTT brokerと接続
    g_mqtt = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    g_mqtt.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    g_mqtt.on_connect = on_connect
    g_mqtt.on_message = on_message
    g_mqtt.loop_forever()


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('usage: ' + sys.argv[0] + ' NODE1 HOP NODE2')
        sys.exit()
    for i in range(len(sys.argv) - 1):
        if len(sys.argv[i + 1]) != 66:
            print('invalid length: ' + str(i) + ': ' + sys.argv[i + 1])
            sys.exit()
    node_id[NODE1] = sys.argv[1]
    node_id[HOP] = sys.argv[2]
    node_id[NODE2] = sys.argv[3]
    for num in range(NODE_NUM):
        print('  ' + NODE_LABEL[num] + '= ' + node_id[num])
    main()
