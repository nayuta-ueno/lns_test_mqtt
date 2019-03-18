# encoding: utf-8
#   wait invoice request and publish invoice

import paho.mqtt.client
import sys
import json
import traceback

import lnnode
import ptarm
import clightning


MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883

ln_node = ''
node_id = ''


def on_connect(client, user_data, flags, response_code):
    global node_id

    del user_data, flags, response_code
    node_id, _ = ln_node.check_status()
    print('node_id=' + node_id)
    client.subscribe('#')
    print('MQTT connected')


def on_message(client, _, msg):
    try:
        payload = str(msg.payload, 'utf-8')
        if msg.topic == 'request/' + node_id:
            print('REQUEST[' + msg.topic + ']' + payload)
            _, ret = ln_node.check_status()
            if ret:
                exec_request(client, json.loads(payload))
        elif msg.topic == 'stop':
            print('STOP!')
            sys.exit()
    except SystemExit:
        raise
    except:
        print('traceback.format_exc():\n%s' % traceback.format_exc())



def exec_request(client, json_msg):
    method = json_msg['method']
    params = json_msg['params']
    if method == 'invoice':
        res = ln_node.get_invoice(params[0])
    elif method == 'pay':
        res = ln_node.pay(params[0])
    print('res=' + res)
    client.publish('response/' + node_id, res)


def linux_cmd_exec(cmd):
    print('cmd:', cmd.split(' '))
    ret = ''
    try:
        ret = subprocess.check_output(cmd.split(' ')).strip()
    except subprocess.CalledProcessError as e:
        print('!!! error happen(errcode=%d) !!!' % e.returncode)
    return ret


def main():
    mqtt_client = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    mqtt_client.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.loop_forever()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: ' + sys.argv[0] + ' ptarm or clightning')
        sys.exit()
    
    if sys.argv[1] == 'ptarm':
        ln_node = ptarm.Ptarm()
    elif sys.argv[1] == 'clightning':
        ln_node = clightning.CLightning()
    else:
        print('unknown lnnode')
        sys.exit()

    ln_node.setup()
    main()
