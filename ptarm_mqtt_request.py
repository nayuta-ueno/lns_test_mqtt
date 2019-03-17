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
NODE_ID = ''


def requester(client):
    while True:
        client.publish(NODE_ID, '{"method":"invoice","params":[ 1000,0 ]}')
        time.sleep(30)


def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('result')
    print 'NODE_ID=' + NODE_ID
    th = threading.Thread(target=requester, args=(client,), name='requester')
    th.start()


def on_message(client, _, msg):
    print '[' + msg.topic + ']' + msg.payload


def linux_cmd_exec(cmd):
    print 'cmd:', cmd.split(' ')
    ret = ''
    try:
        ret = subprocess.check_output(cmd.split(' ')).strip()
    except subprocess.CalledProcessError as e:
        print '!!! error happen(errcode=%d) !!!' % e.returncode
    return ret


def socket_send(req):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('localhost', 9736))
    print 'req=' + req
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
    if len(sys.argv) != 2:
        print 'usage: ' + sys.argv[0] + ' NODE_ID'
        sys.exit()
    NODE_ID = sys.argv[1]
    main()
