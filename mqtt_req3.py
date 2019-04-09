# encoding: utf-8
'''
node1-+-hop---node2
      |
node2-+

    while True:
        [node1 => hop]connect
        [node2 => hop]connect
        [node3 => hop]connect
        [node1 => hop]open_channel
        [node3 => hop]open_channel
        [hop => node2]open_channel
        ...
        for 1000:
            [node2]invoice
            [node1]pay
            [node2]invoice
            [node3]pay
        close_all
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
FUNDING_FUNDED = 2
FUNDING_CLOSING = 3

PAY_START_BLOCK = 8
PAY_FAIL_BLOCK = 10


# 使うノード数
NODE_NUM = 4

# node_id[]のインデックス
NODE1=0
NODE3=1
HOP=2
NODE2=3

# ログ用のラベル
NODE_LABEL = ['node1', 'node3', 'hop', 'node2']

# [0]が[1]に向けてconnectする
# close_all()も同じ方向でcloseする
NODE_CONNECT = [ [NODE1, HOP], [NODE2, HOP], [NODE3, HOP] ]
NODE_OPEN = [ [NODE1, HOP], [HOP, NODE2], [NODE3, HOP] ]
NODE_OPEN_AMOUNT = 50000

# 送金回数。この回数だけ送金後、mutual closeする。
PAY_COUNT_MAX = 100

# 今のところ送金完了が分からないので、一定間隔で送金している
PAY_SEC = 10

# global variable
node_id = [''] * NODE_NUM
dict_recv_node = dict()
dict_status_node = dict()

array_connected_node = []

thread_request = None
loop_reqester = True

funded_block_count = 0      # 全チャネルがnormal operationになったときのblockcount
is_funding = FUNDING_NONE   # 0:none, 1:connecting, 2:funding
funding_wait_count = 0      # is_fundingが1になったままのカウント数

pay_count = 0
last_fail_pay_count = -1    # 前回payでNGが返ってきたときのpay_count
fail_count = 0


# MQTT: connect
def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('#')
    th1 = threading.Thread(target=poll_time, args=(client,), name='poll_time', daemon=True)
    th1.start()
    th2 = threading.Thread(target=notifier, args=(client,), name='notifier', daemon=True)
    th2.start()
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
        if (len(recv_id) != 0) and msg.topic.startswith('notify/'):
            print('yet: ' + node2label(recv_id))
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

        if is_funding == FUNDING_NONE:
            print('connected list:', array_connected_node)
            connect_all(client)

        time.sleep(5)


# check status health
#   起動して30秒以内にテスト対象のnode全部がstatusを送信すること
#   テスト対象のnodeは、120秒以内にstatusを毎回送信すること(通信が詰まっているときがあるのか、60秒で失敗することがあった))
def poll_time(client):
    global dict_recv_node, funding_wait_count
    SAME_LIMIT_SECOND = 30 * 60 # 同じ状態が継続できる上限(FUNDING_FUNDED以外)
    LOOP_SECOND = 30            # 監視周期

    bak_funding = FUNDING_NONE
    same_status = 0
    stop_order = False
    while not stop_order:
        time.sleep(LOOP_SECOND)

        print('*** is_funding=' + str(is_funding))

        # check health
        if len(dict_recv_node) < NODE_NUM:
            errlog_print('not all node found: ', dict_recv_node)
            stop_order = True
            break
        for node in dict_recv_node:
            if time.time() - dict_recv_node[node] > 120:
                errlog_print('node not exist:' + node)
                stop_order = True
                break
        if is_funding == FUNDING_WAIT:
            funding_wait_count += 1
            print('funding_wait_count=' + str(funding_wait_count))
            if funding_wait_count > FUNDING_WAIT_MAX:
                errlog_print('  --> funding not started long time')
                stop_order = True
                break
        if (bak_funding == is_funding) and (is_funding != FUNDING_FUNDED):
            same_status += 1
            print('same status: ' + str(same_status))
            if same_status > SAME_LIMIT_SECOND / LOOP_SECOND:
                errlog_print('  --> too many same status: ' + str(is_funding))
                stop_order = True
                break
        else:
            same_status = 0
        bak_funding = is_funding

        # https://stackoverflow.com/questions/12919980/nohup-is-not-writing-log-to-output-file
        sys.stdout.flush()
    if stop_order:
        print('!!! stop order: poll_time')
        publish_stop(client)


# topic
#   check our testing node_ids
def proc_topic(client, msg):
    global dict_recv_node

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
    global dict_status_node, thread_request, loop_reqester, is_funding, funded_block_count

    if len(dict_status_node) != NODE_NUM:
        return

    try:
        if thread_request is None:
            all_normal = True
            all_none = True
            #print('    proc_status-------------')
            for node in dict_status_node:
                for status in dict_status_node[node]['status']:
                    #print('    proc_status=' + status[0] + ': ' + node2label(status[1]))
                    if status[0] != 'Status.NORMAL':
                        all_normal = False
                    if status[0] != 'Status.NONE':
                        all_none = False
            if all_normal:
                funded_block_count = getblockcount()    # announcement計測用
                is_funding = FUNDING_FUNDED
                loop_reqester = True
                thread_request = threading.Thread(target=requester, args=(client,), name='requester', daemon=True)
                thread_request.start()
                print('all_normal: start requester thread: ' + str(funded_block_count))
            elif all_none and is_funding == FUNDING_CLOSING:
                print('all_none: close done')
                is_funding = FUNDING_NONE
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
    global pay_count

    while loop_reqester:
        blk = getblockcount()
        if blk - funded_block_count < PAY_START_BLOCK:
            print('wait confirm: ' + str(blk - funded_block_count))
            time.sleep(10)
            continue
        print('payed:' + str(pay_count))
        if pay_count < PAY_COUNT_MAX:
            # request invoice
            log_print('[REQ]invoice')
            client.publish('request/' + node_id[NODE2], '{"method":"invoice","params":[ 1000,"node1" ]}')
            client.publish('request/' + node_id[NODE2], '{"method":"invoice","params":[ 500,"node3" ]}')
            pay_count += 1
            time.sleep(PAY_SEC)
        else:
            # 一定回数送金要求したらチャネルを閉じる
            log_print('[REQ]close all')
            pay_count = 0
            close_all(client)
            break
    print('exit requester')


def proc_invoice_got(client, json_msg, msg, recv_id):
    log_print('[RESPONSE]invoice-->[REQ]pay:' + json_msg['result'][2])
    if json_msg['result'][2] == 'node1':
        client.publish('request/' + node_id[NODE1],
                '{"method":"pay","params":[ "' + json_msg['result'][1] + '" ]}')
    elif json_msg['result'][2] == 'node3':
        client.publish('request/' + node_id[NODE3],
                '{"method":"pay","params":[ "' + json_msg['result'][1] + '" ]}')


#################################################################################

def connect_all(client):
    global is_funding, array_connected_node

    if len(dict_status_node) != NODE_NUM:
        return

    for node in NODE_CONNECT:
        connector = node_id[node[0]]
        connectee = node_id[node[1]]
        pair = (connector, connectee)
        if pair not in array_connected_node:
            log_print('[REQ]connect: ' + NODE_LABEL[node[0]] + '=>' + NODE_LABEL[node[1]])
            ipaddr = dict_status_node[connectee]['ipaddr']
            port = dict_status_node[connectee]['port']
            client.publish('request/' + connector, \
                '{"method":"connect", "params":['
                    '"' + connectee + '", '
                    '"' + ipaddr + '", ' + str(port) + ' ]}')


def open_all(client):
    global is_funding

    log_print('open_all')
    for node in NODE_OPEN:
        opener = node_id[node[0]]
        openee = node_id[node[1]]
        print('[REQ]open: ' + NODE_LABEL[node[0]] + ' => ' + NODE_LABEL[node[1]])
        client.publish('request/' + opener,
                '{"method":"openchannel","params":[ "' + openee + '", ' + str(NODE_OPEN_AMOUNT) + ' ]}')
    is_funding = FUNDING_WAIT


def close_all(client):
    global is_funding, array_connected_node

    log_print('close_all')
    for node in NODE_CONNECT:
        closer = node_id[node[0]]
        closee = node_id[node[1]]
        print('[REQ]close: ' + NODE_LABEL[node[0]] + '=>' + NODE_LABEL[node[1]])
        client.publish('request/' + closer, '{"method":"closechannel", "params":[ "' + closee + '" ]}')
    is_funding = FUNDING_CLOSING
    array_connected_node = []


# message: topic="response/#"
def message_response(client, json_msg, msg, recv_id):
    global dict_connected_node, is_funding, pay_count, funded_block_count, last_fail_pay_count, fail_count

    ret = True
    if json_msg['result'][0] == 'connect':
        if json_msg['result'][1] == 'OK':
            log_print('connected: ' + node2label(recv_id) + ' => ' + node2label(json_msg['result'][2]))
            pair = (recv_id, json_msg['result'][2])
            if pair not in array_connected_node:
                array_connected_node.append(pair)
                if (len(array_connected_node) == len(NODE_CONNECT)) and (is_funding != FUNDING_WAIT):
                    open_all(client)
        else:
            log_print('fail connect[' + json_msg['result'][1] + ']: ' + node2label(recv_id) + ' => ' + node2label(json_msg['result'][2]))
            # ret = False   # close直後はありがちなので、スルー
            time.sleep(5)

    elif json_msg['result'][0] == 'openchannel':
        if json_msg['result'][1] == 'OK':
            log_print('funding start: ' + node2label(json_msg['result'][2]))
        else:
            log_print('funding fail[' + json_msg['result'][1] + ']: ' + node2label(json_msg['result'][2]))
            ret = False

    elif json_msg['result'][0] == 'closechannel':
        if json_msg['result'][1] == 'OK':
            log_print('closing start: ' + node2label(json_msg['result'][2]))
        else:
            log_print('closing fail[' + json_msg['result'][1] + ']: ' + node2label(json_msg['result'][2]))
            ret = False

    elif json_msg['result'][0] == 'invoice':
        if json_msg['result'][1] == 'NG':
            log_print('fail invoice')
            ret = False
        else:
            proc_invoice_got(client, json_msg, msg, recv_id)

    elif json_msg['result'][0] == 'pay':
        if json_msg['result'][1] == 'OK':
            log_print('pay start: ' + str(pay_count) + '(' + str(last_fail_pay_count) + ')' + ', fail_count=' + str(fail_count))
        else:
            blk = getblockcount()
            # announcementは 6 confirm以降で展開なので、少し余裕を持たせる
            if blk - funded_block_count > PAY_FAIL_BLOCK:
                fail_count += 1
                if last_fail_pay_count == pay_count:
                    log_print('pay fail: ' + json_msg['result'][1] + ', fail_count=' + str(fail_count))
                    ret = False
                else:
                    print('pay fail: last=' + str(last_fail_pay_count) + ' now=' + str(pay_count) + ', fail_count=' + str(fail_count))
                    last_fail_pay_count = pay_count
            else:
                print('pay fail: through(' + str(blk - funded_block_count) + ')')
                pay_count = 0

    if not ret:
        log_print('!!! False: message_response')
        publish_stop(client)

    return ret


# message: topic="status/#"
def message_status(client, json_msg, msg, recv_id):
    global dict_status_node

    dict_status_node[recv_id] = json_msg
    if json_msg['status'] != 'Status.NORMAL':
        pass


def publish_stop(client):
    for node in node_id:
        print('stop: ' + node)
        client.publish('stop/' + node, 'stop all')
    client.publish('stop/' + TESTNAME, 'stop all')
    log_print('send stop')


def kill_me():
    os.kill(os.getpid(), signal.SIGKILL)


def log_print(msg):
    print('#####################')
    print('# ' + msg)
    print('#####################')


def errlog_print(msg):
    print('!!!!!!!!!!!!!!!!!!!!!')
    print('! ' + msg)
    print('!!!!!!!!!!!!!!!!!!!!!')


def node2label(id):
    num = 0
    for node in node_id:
        if node == id:
            return NODE_LABEL[num]
        num += 1
    return '???(' + id + ')'


def json_node_connect():
    json_conn = []
    for lists in NODE_CONNECT:
        pair = [ node_id[lists[0]], node_id[lists[1]] ]
        json_conn.append(pair)
    return json_conn


def getblockcount():
    cnt = linux_cmd_exec('bitcoin-cli getblockcount')
    if cnt is not None:
        print('  getblockcount=' + cnt)
        return int(cnt)
    else:
        return 0


def linux_cmd_exec(cmd):
    # print('cmd:', cmd.split(' '))
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


#################################################################################

if __name__ == '__main__':
    if len(sys.argv) != 1 + NODE_NUM:
        print('usage: ' + sys.argv[0] + ' NODE1 NODE3 HOP NODE2')
        sys.exit()
    for i in range(NODE_NUM):
        if len(sys.argv[i + 1]) != 66:
            print('invalid length: ' + str(i) + ': ' + sys.argv[i + 1])
            sys.exit()

    # 引数とnode_idの対応
    node_id[NODE1] = sys.argv[1]
    node_id[NODE3] = sys.argv[2]
    node_id[HOP] = sys.argv[3]
    node_id[NODE2] = sys.argv[4]

    for num in range(NODE_NUM):
        print('  ' + NODE_LABEL[num] + '= ' + node_id[num])
    main()
