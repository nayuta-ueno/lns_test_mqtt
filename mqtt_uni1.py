# encoding: utf-8
'''
node0---node1

    while True:
        [node0 => node1]connect
        [node0 => node1]open_channel
        ...
        for PAY_COUNT_MAX:
            [node1]invoice
            [node0]pay-node1
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
import configparser


class PayCount:
    def __init__(self):
        self.invoice_count = 0
        self.pay_count = 0
        self.last_fail_pay_count = -1    # 前回payでNGが返ってきたときのpay_count
        self.fail_cont_count = 0         # failが連続した回数
        self.fail_count = 0


config = configparser.ConfigParser()

# MQTT
MQTT_HOST = ''
MQTT_PORT = 0
TOPIC_PREFIX = ''

# random requester name
RANDNAME = ''.join([random.choice(
                    string.ascii_letters + string.digits) for i in range(16)])

# const variable
FUNDING_NONE = 0
FUNDING_WAIT = 1
FUNDING_FUNDED = 2
FUNDING_CLOSING = 3

PAY_START_BLOCK = 8
PAY_FAIL_BLOCK = 10

# 使うノード数
NODE_NUM = 2

# array_node_id[]のインデックス
#   偶数番n(payer)とn+1(payee)がセットになる
NODE0 = 0
NODE1 = 1

# ログ用のラベル
NODE_LABEL = [
    'node0', 'node1'
]

# [0]が[1]に向けてconnectする
# close_all()も同じ方向でcloseする
NODE_CONNECT = [
    [NODE0, NODE1]
]
NODE_OPEN = [
    [NODE0, NODE1]
]
NODE_OPEN_AMOUNT = 0

# 送金回数。この回数だけ送金後、mutual closeする。
PAY_COUNT_MAX = 0

# 今のところ送金完了が分からないので、一定間隔で送金している
PAY_INVOICE_ELAPSE = 0

# 送信失敗が連続してテストを終了するカウント
FAIL_CONT_MAX = 3

# global variable
array_node_id = [''] * NODE_NUM
dict_recv_node = dict()
dict_status_node = dict()
dict_amount = dict()
dict_paycount = dict()

array_connected_node = []

thread_request = None
loop_reqester = True

funded_block_count = 0      # 全チャネルがnormal operationになったときのblockcount
is_funding = FUNDING_NONE   # FUNDING_xxx


# MQTT: connect
def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe(TOPIC_PREFIX + '/#')
    th1 = threading.Thread(target=poll_time, args=(client,), name='poll_time',
                           daemon=True)
    th1.start()
    th2 = threading.Thread(target=notifier, args=(client,), name='notifier',
                           daemon=True)
    th2.start()
    print('MQTT connected')


# MQTT: message subscribed
def on_message(client, _, msg):
    global dict_recv_node, dict_status_node, thread_request, loop_reqester,\
           is_funding

    # topic
    #   'request/' + node_id    : requester --> responser
    #   'response/' + node_id   : responser ==> requester
    #   'stop/ + node_id        : requester --> responser'
    ret, recv_id = proc_topic(client, msg)
    if not ret:
        if (len(recv_id) != 0) and msg.topic.startswith(TOPIC_PREFIX + '/notify/'):
            print('yet: ' + nodeid2label(recv_id))
        return

    # payload
    proc_payload(client, msg, recv_id)

    # status
    proc_status(client, msg, recv_id)


def notifier(client):
    while True:
        # notify
        conn_dict = {"connect": json_node_connect()}
        for node in array_node_id:
            # print('notify: ' + node)
            client.publish(TOPIC_PREFIX + '/notify/' + node,
                           json.dumps(conn_dict))

        if is_funding == FUNDING_NONE:
            # print('connected list:', array_connected_node)
            connect_all(client)

        # https://stackoverflow.com/questions/12919980/nohup-is-not-writing-log-to-output-file
        sys.stdout.flush()

        time.sleep(5)


# check status health
#   起動して30秒以内にテスト対象のnode全部がstatusを送信すること
#   テスト対象のnodeは、120秒以内にstatusを毎回送信すること(通信が詰まっているときがあるのか、60秒で失敗することがあった))
def poll_time(client):
    global dict_recv_node
    SAME_LIMIT_SECOND = 30 * 60     # 同じ状態が継続できる上限(FUNDING_FUNDED以外)
    LOOP_SECOND = 30                # 監視周期

    bak_funding = FUNDING_NONE
    same_status = 0
    stop_order = False
    reason = ''
    while not stop_order:
        time.sleep(LOOP_SECOND)

        print('*** is_funding=' + str(is_funding))

        # check health
        if len(dict_recv_node) < NODE_NUM:
            reason = 'not all node found: ' + str(dict_recv_node)
            stop_order = True
            break
        for node in dict_recv_node:
            if time.time() - dict_recv_node[node] > 120:
                reason = 'node not exist:' + node
                stop_order = True
                break
        if (bak_funding == is_funding) and (is_funding != FUNDING_FUNDED):
            same_status += 1
            print('same status: ' + str(same_status))
            if same_status > SAME_LIMIT_SECOND / LOOP_SECOND:
                reason = 'too many same status: ' + str(is_funding)
                stop_order = True
                break
        else:
            same_status = 0
        bak_funding = is_funding
    if stop_order:
        errlog_print(reason)
        stop_all(client, reason)


# topic
#   check our testing node_ids
def proc_topic(client, msg):
    global dict_recv_node

    if msg.topic == TOPIC_PREFIX + '/stop/' + RANDNAME:
        print('STOP!')
        kill_me()

    ret = False
    mine = False
    recv_id = ''
    try:
        if msg.topic.startswith(TOPIC_PREFIX + '/response/') or msg.topic.startswith(TOPIC_PREFIX + '/status/'):
            if msg.topic.rfind('/') != -1:
                recv_id = msg.topic[msg.topic.rfind('/') + 1:]
                for i in range(NODE_NUM):
                    if array_node_id[i] == recv_id:
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
    payload = ''
    try:
        # payload
        payload = str(msg.payload, 'utf-8')
        if len(payload) == 0:
            return
        if msg.topic.startswith(TOPIC_PREFIX + '/response/'):
            message_response(client, json.loads(payload), msg, recv_id)
        elif msg.topic.startswith(TOPIC_PREFIX + '/status/'):
            message_status(client, json.loads(payload), msg, recv_id)
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())
        print('payload=', payload)


# process for status
def proc_status(client, msg, recv_id):
    global dict_status_node, thread_request, loop_reqester,\
           is_funding, funded_block_count

    if len(dict_status_node) != NODE_NUM:
        return

    try:
        if thread_request is None:
            all_normal = True
            all_none = True
            # print('    proc_status-------------')
            for node in dict_status_node:
                for status in dict_status_node[node]['status']:
                    # print('    proc_status=' + status[0] + ': ' + nodeid2label(status[1]))
                    if status[0] != 'Status.NORMAL':
                        all_normal = False
                    if status[0] != 'Status.NONE':
                        all_none = False
            if all_normal:
                funded_block_count = getblockcount()    # announcement計測用
                is_funding = FUNDING_FUNDED
                loop_reqester = True
                thread_request = threading.Thread(target=requester,
                                                  args=(client,),
                                                  name='requester',
                                                  daemon=True)
                thread_request.start()
                print('all_normal: start requester thread: ' +
                      str(funded_block_count))
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


###############################################################################

# request check
def requester(client):
    global dict_paycount

    while loop_reqester:
        blk = getblockcount()
        if blk - funded_block_count < PAY_START_BLOCK:
            print('wait confirm: ' + str(blk - funded_block_count))
            time.sleep(10)
            continue
        pay_max_count = 0
        for lp in range(int(NODE_NUM / 2)):
            payer_idx = lp * 2
            payee_idx = payer_idx + 1
            payer_node = array_node_id[payer_idx]
            if payer_node not in dict_paycount:
                dict_paycount[payer_node] = PayCount()
            pay_count = dict_paycount[payer_node].pay_count
            if pay_count < PAY_COUNT_MAX:
                # request invoice
                log_print('[REQ]invoice(' + NODE_LABEL[payer_idx] + ')')
                client.publish(TOPIC_PREFIX + '/request/' + array_node_id[payee_idx],
                               '{"method":"invoice",'
                               '"params":[ 1000,"' + NODE_LABEL[payer_idx]+'" ]}')
            else:
                pay_max_count += 1
        if pay_max_count == int(NODE_NUM / 2):
            # 一定回数送金要求したらチャネルを閉じる
            log_print('[REQ]close all')
            close_force_all(client)
            for pay_obj in dict_paycount.values():
                pay_obj.pay_count = 0
                pay_obj.invoice_count = 0
            break
        else:
            time.sleep(PAY_INVOICE_ELAPSE)
    print('exit requester')


def proc_invoice_got(client, json_msg, msg, recv_id):
    global dict_paycount

    invoice = json_msg['result'][1]
    target = json_msg['result'][2]
    idx = label2idx(target)

    dict_paycount[array_node_id[idx]].invoice_count += 1
    log_print('[RESPONSE]invoice-->[REQ]pay:' + target +
              ': ' + invoice)
    client.publish(TOPIC_PREFIX + '/request/' + array_node_id[idx],
                   '{"method":"pay",'
                   '"params":[ "' + invoice + '" ]}')


###############################################################################

def connect_all(client):
    global is_funding, array_connected_node

    if len(dict_status_node) != NODE_NUM:
        return

    for node_conn in NODE_CONNECT:
        connector_idx = node_conn[0]
        connectee_idx = node_conn[1]
        connector = array_node_id[connector_idx]
        connectee = array_node_id[connectee_idx]
        pair = (connector, connectee)
        if pair not in array_connected_node:
            log_print('[REQ]connect: ' + NODE_LABEL[connector_idx] +
                      '=>' + NODE_LABEL[connectee_idx])
            ipaddr = dict_status_node[connectee]['ipaddr']
            port = dict_status_node[connectee]['port']
            client.publish(TOPIC_PREFIX + '/request/' + connector,
                           '{"method":"connect", "params":['
                           '"' + connectee + '", '
                           '"' + ipaddr + '", ' + str(port) + ' ]}')


def disconnect_all(client):
    global is_funding, array_connected_node

    log_print('disconnect_all')
    for node_conn in NODE_CONNECT:
        connector_idx = node_conn[0]
        connectee_idx = node_conn[1]
        connector = array_node_id[connector_idx]
        connectee = array_node_id[connectee_idx]
        log_print('[REQ]disconnect: ' + NODE_LABEL[connector_idx] +
                  '=>' + NODE_LABEL[connectee_idx])
        client.publish(TOPIC_PREFIX + '/request/' + connector,
                       '{"method":"disconnect", "params":['
                       '"' + connectee + '" ]}')


def open_all(client):
    global is_funding

    log_print('open_all')
    for node_open in NODE_OPEN:
        opener_idx = node_open[0]
        openee_idx = node_open[1]
        opener = array_node_id[opener_idx]
        openee = array_node_id[openee_idx]
        print('[REQ]open: ' + NODE_LABEL[opener_idx] +
              ' => ' + NODE_LABEL[openee_idx])
        client.publish(TOPIC_PREFIX + '/request/' + opener,
                       '{"method":"openchannel","params":[ "' + openee +
                       '", ' + str(NODE_OPEN_AMOUNT) + ' ]}')
    is_funding = FUNDING_WAIT


def close_all(client):
    global is_funding, array_connected_node

    log_print('close_all')
    for node_close in NODE_CONNECT:
        closer_idx = node_close[0]
        closee_idx = node_close[1]
        closer = array_node_id[closer_idx]
        closee = array_node_id[closee_idx]
        print('[REQ]close: ' + NODE_LABEL[closer_idx] +
              '=>' + NODE_LABEL[closee_idx])
        client.publish(TOPIC_PREFIX + '/request/' + closer,
                       '{"method":"closechannel",'
                       '"params":["' + closee + '","mutual"]}')
    is_funding = FUNDING_CLOSING
    array_connected_node = []


def close_force_all(client):
    global is_funding, array_connected_node

    disconnect_all(client)

    log_print('close_all_force')
    for node_close in NODE_CONNECT:
        closer_idx = node_close[0]
        closee_idx = node_close[1]
        closer = array_node_id[closer_idx]
        closee = array_node_id[closee_idx]
        print('[REQ]close: ' + NODE_LABEL[closer_idx] +
              '=>' + NODE_LABEL[closee_idx])
        client.publish(TOPIC_PREFIX + '/request/' + closer,
                       '{"method":"closechannel",'
                       '"params":["' + closee + '","force"]}')
    is_funding = FUNDING_CLOSING
    array_connected_node = []


def stop_all(client, reason):
    for node in array_node_id:
        print('stop: ' + node)
        client.publish(TOPIC_PREFIX + '/stop/' + node, reason)
    client.publish(TOPIC_PREFIX + '/stop/' + RANDNAME, reason)
    log_print('send stop: ' + reason)


# message: topic="response/#"
def message_response(client, json_msg, msg, recv_id):
    global is_funding, dict_paycount, funded_block_count, array_connected_node

    recv_name = nodeid2label(recv_id)
    ret = True
    reason = ''
    res_command = json_msg['result'][0]
    res_result = json_msg['result'][1]
    if res_command == 'connect':
        direction = recv_name +\
                    ' => ' + nodeid2label(json_msg['result'][2])
        if res_result == 'OK':
            log_print('[RESPONSE]connected: ' + direction)
            pair = (recv_id, json_msg['result'][2])
            if pair not in array_connected_node:
                array_connected_node.append(pair)
                if (len(array_connected_node) == len(NODE_CONNECT)) and (is_funding != FUNDING_WAIT):
                    open_all(client)
        else:
            log_print('fail connect[' + res_result + ']: ' + direction)
            # ret = False   # close直後はありがちなので、スルー
            time.sleep(5)

    elif res_command == 'openchannel':
        direction = recv_name +\
                    ' => ' + nodeid2label(json_msg['result'][2])
        if res_result == 'OK':
            log_print('[RESPONSE]funding start: ' + direction)
        else:
            reason = 'funding fail[' + res_result + ']: ' + direction
            ret = False

    elif res_command == 'closechannel':
        direction = recv_name +\
                    ' => ' + nodeid2label(json_msg['result'][2])
        if res_result == 'OK':
            log_print('[RESPONSE]closing start: ' + direction)
        else:
            reason = 'closing fail[' + res_result + ']: ' + direction
            ret = False

    elif res_command == 'invoice':
        if res_result == 'NG':
            reason = 'fail invoice'
            ret = False
        else:
            proc_invoice_got(client, json_msg, msg, recv_id)

    elif res_command == 'pay':
        invoice = json_msg['result'][2]
        if recv_id not in dict_paycount:
            dict_paycount[recv_id] = PayCount()
        pay_obj = dict_paycount[recv_id]

        def pay_reason():
            return '(' + recv_name +\
                '): ' + res_result +\
                ', invoice_count=' + str(pay_obj.invoice_count) +\
                ', pay_count=' + str(pay_obj.pay_count) +\
                ', last_fail_pay_count=' + str(pay_obj.last_fail_pay_count) +\
                ', fail_count=' + str(pay_obj.fail_count) +\
                ', fail_cont_count=' + str(pay_obj.fail_cont_count) +\
                ': ' + invoice

        if res_result == 'OK':
            pay_obj.pay_count += 1
            log_print('[RESPONSE]pay ' + pay_reason())
            pay_obj.fail_cont_count = 0
            print(' pay_count=' + str(pay_obj.pay_count))
        else:
            blk = getblockcount()
            # announcementは 6 confirm以降で展開なので、少し余裕を持たせる
            if blk - funded_block_count > PAY_FAIL_BLOCK:
                pay_obj.fail_count += 1
                reason = 'pay fail' + pay_reason()
                print(reason)
                if pay_obj.last_fail_pay_count == pay_obj.pay_count:
                    # 連続してNG
                    pay_obj.fail_cont_count += 1
                    if pay_obj.fail_cont_count >= FAIL_CONT_MAX:
                        # 連続NG数が許容を超えた
                        errlog_print('too many failure')
                        ret = False
                else:
                    # 単発NG
                    pay_obj.last_fail_pay_count = pay_obj.pay_count
                    pay_obj.fail_cont_count = 0
            else:
                print('pay through' + pay_reason())

    if not ret:
        errlog_print(reason)
        stop_all(client, reason)


# message: topic="status/#"
def message_status(client, json_msg, msg, recv_id):
    global dict_status_node

    recv_name = nodeid2label(recv_id)
    if recv_id not in dict_paycount:
        dict_paycount[recv_id] = PayCount()
    print(recv_name + 
          ':  invoice_count=' + str(dict_paycount[recv_id].invoice_count) +
          ',  pay_count=' + str(dict_paycount[recv_id].pay_count) +
          ', last_fail_pay_count=' + str(dict_paycount[recv_id].last_fail_pay_count) +
          ', fail_cont_count=' + str(dict_paycount[recv_id].fail_cont_count) +
          ', fail_count=' + str(dict_paycount[recv_id].fail_count))
    if dict_paycount[recv_id].pay_count > 0:
        if recv_id in dict_status_node:
            print('--------------------------')
            for stat in json_msg['status']:
                # print('DBG:  stat ' + stat[0] + ':' + stat[1])
                if stat[0] == 'Status.NORMAL':
                    for old in dict_status_node[recv_id]['status']:
                        if stat[1] == old[1] and old[0] == 'Status.NORMAL':
                            print('AMT:' + stat[1] +
                                  '  old=' + str(old[2]) +
                                  ', new=' + str(stat[2]) +
                                  ', diff=' + str(stat[2] - old[2]))
                            break
                    else:
                        continue
            print('--------------------------')
    dict_status_node[recv_id] = json_msg


def kill_me():
    # https://stackoverflow.com/questions/12919980/nohup-is-not-writing-log-to-output-file
    sys.stdout.flush()
    os.kill(os.getpid(), signal.SIGKILL)


def log_print(msg):
    print('#####################')
    print('# ' + msg)
    print('#####################')


def errlog_print(msg):
    print('!!!!!!!!!!!!!!!!!!!!!')
    print('! ' + msg)
    print('!!!!!!!!!!!!!!!!!!!!!')


def nodeid2label(id):
    num = 0
    for node in array_node_id:
        if node == id:
            return NODE_LABEL[num]
        num += 1
    return '???(' + id + ')'


def label2idx(label):
    return NODE_LABEL.index(label)


def json_node_connect():
    json_conn = []
    for lists in NODE_CONNECT:
        pair = [array_node_id[lists[0]], array_node_id[lists[1]]]
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


###############################################################################

if __name__ == '__main__':
    if len(sys.argv) != 2 + NODE_NUM:
        print('usage: ' + sys.argv[0] + ' INI_SECTION NODE0 NODE1')
        sys.exit()
    for i in range(NODE_NUM):
        if len(sys.argv[2 + i]) != 66:
            print('invalid length: ' + str(i) + ': ' + sys.argv[2 + i])
            sys.exit()

    config.read('./config.ini')
    testname = sys.argv[1]
    print('testname= ' + testname)

    MQTT_HOST = config.get('MQTT', 'BROKER_URL')
    MQTT_PORT = config.getint('MQTT', 'BROKER_PORT')
    TOPIC_PREFIX = config.get(testname, 'TOPIC_PREFIX')
    NODE_OPEN_AMOUNT = config.getint(testname, 'NODE_OPEN_AMOUNT')
    PAY_COUNT_MAX = config.getint(testname, 'PAY_COUNT_MAX')
    PAY_INVOICE_ELAPSE = config.getint(testname, 'PAY_INVOICE_ELAPSE')
    PAY_START_BLOCK = config.getint(testname, 'PAY_START_BLOCK')
    PAY_FAIL_BLOCK = config.getint(testname, 'PAY_FAIL_BLOCK')

    # 引数とnode_idの対応
    cnt = 0
    for i in sys.argv[2:]:
        array_node_id[cnt] = i
        cnt += 1

    for num in range(NODE_NUM):
        print('  ' + NODE_LABEL[num] + '= ' + array_node_id[num])
    main()
