# encoding: utf-8
import paho.mqtt.client
import traceback


count = 0

MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883


def on_connect(client, user_data, flags, response_code):
    del user_data, flags, response_code
    client.subscribe('response/02c42924185506dafb183391a65d5fe46d7a4d53fe563311d8d2a0ae0537f8de95')
    print('MQTT connected')


def on_message(client, _, msg):
    global count

    payload = str(msg.payload, 'utf-8')
    #print('payload=' + payload, ' find=', str(payload.find('status')))
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
