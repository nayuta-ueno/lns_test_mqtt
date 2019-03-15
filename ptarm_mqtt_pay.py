# -*- coding: utf-8 -*-

import paho.mqtt.client
import socket
import sys
import json
import traceback


MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883


def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    check_status()
    client.subscribe('#')


def on_message(client, _, msg):
    print '[' + msg.topic + ']' + msg.payload
    if msg.topic == 'response':
        jrpc = json.loads(msg.payload)
        try:
            result = jrpc['result']
            print 'hash=' + result['hash']
            print 'amount_msat=' + str(result['amount_msat'])
            print 'bolt11=' + result['bolt11']
            if check_status():
                jcmd = '{"method":"routepay","params":["' + result['bolt11'] + '",0]}'
                print 'json=' + jcmd
                socket_send(jcmd)
        except:
            print 'traceback.format_exc():\n%s' % traceback.format_exc()
    elif msg.topic == 'stop':
        print 'STOP!'
        sys.exit()


def check_status():
    result = False
    try:
        jcmd = '{"method":"getinfo","params":[]}'
        print 'json=' + jcmd
        response = socket_send(jcmd)
        jrpc = json.loads(response)
        for prm in jrpc['result']['peers']:
            print 'status=' + prm['status']
            if prm['status'] == 'normal operation':
                result = True
                break
    except:
        print 'traceback.format_exc():\n%s' % traceback.format_exc()
        sys.exit()
    return result


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
    client.send(req)
    response = client.recv(4096)
    client.close()
    return response


def main():
    g_mqtt = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    g_mqtt.\
        connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    g_mqtt.on_connect = on_connect
    g_mqtt.on_message = on_message
    g_mqtt.loop_forever()


if __name__ == '__main__':
    main()
