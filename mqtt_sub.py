# encoding: utf-8
import paho.mqtt.client
import traceback
from datetime import datetime


count = 0

MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883
#PEEK_TOPIC = 'status'
PEEK_TOPIC = 'response'
PEEK_ID = '0200120ad5b68c2f97e3cf7555cfd32193cc7417d0b99d53faed4ba9dc0facf77a'

def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('#')
    print('MQTT connected')


def on_message(client, _, msg):
    global count

    if PEEK_ID not in msg.topic:
        return
    if 'status' in msg.topic:
        print('.', end='', flush=True)
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
