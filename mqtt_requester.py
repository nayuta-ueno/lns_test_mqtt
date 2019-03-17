# encoding: utf-8
#   wait invoice request and publish invoice
import subprocess
import time
import sys

import paho.mqtt.client
import socket
import threading


MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883
payer_id = ''
payee_id = ''


def requester(client):
    while True:
        # request invoice: payee
        client.publish(payee_id, '{"method":"invoice","params":[ 1000,0 ]}')
        time.sleep(60)


def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('result')
    print('payee_id=' + payee_id)
    th = threading.Thread(target=requester, args=(client,), name='requester')
    th.start()


def on_message(client, _, msg):
    try:
        payload = str(msg.payload, 'utf-8')
        print('[' + msg.topic + ']' + payload)
        if msg.topic.startswith('response/'):
            json_msg = json.loads(payload)
            if msg.topic.endswith(payer_id):
                response_payer(json_msg)
                pass
            elif msg.topic.endswith(payee_id):
                response_payee(json_msg)
                pass
        elif msg.topic == 'stop':
            print('STOP!')
            sys.exit()
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())


def response_payer(json_msg):
    if json_msg['result'][0] == 'pay':
        print('pay start')


def response_payee(json_msg):
    if json_msg['result'][0] == 'invoice':
        client.publish(payer_id, '{"method":"pay","params":[ "' + json_msg['result'][1] + '" ]}')


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
    main()
