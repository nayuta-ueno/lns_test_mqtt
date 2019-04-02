# encoding: utf-8
import paho.mqtt.client
import traceback
from datetime import datetime
import json


count = 0

MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883
#PEEK_TOPIC = 'status'
PEEK_TOPIC = 'response'
PEEK_ID = '03656ae6bbfcd61592d9b990c7833c2c7aa1fa92b235c5693159e66d033d373c12'

def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('#')
    print('MQTT connected')


def on_message(client, _, msg):
    global count

    if PEEK_ID not in msg.topic:
        return
    if 'status' in msg.topic:
        payload = str(msg.payload, 'utf-8')
        json_msg = json.loads(payload)
        if json_msg['status'] == 'Status.NORMAL':
            mark = 'n'
        elif json_msg['status'] == 'Status.CLOSING':
            mark = 'C'
        elif json_msg['status'] == 'Status.FUNDING':
            mark = 'F'
        elif json_msg['status'] == 'Status.UNKNOWN':
            mark = 'U'
        else:
            mark = '.'
        print(mark, end='', flush=True)
        return
    payload = str(msg.payload, 'utf-8')
    print('[' + datetime.now().strftime("%Y/%m/%d %H:%M:%S") + ']payload=' + payload, ' find=', str(payload.find('status')))
    if payload.find('openchannel') != -1:
        count += 1
        print('count=' + str(count) + '  ' + payload)


def main():
    mqtt_client = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    mqtt_client.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.loop_forever()


if __name__ == '__main__':
    main()
