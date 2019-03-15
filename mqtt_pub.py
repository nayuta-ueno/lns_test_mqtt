import paho.mqtt.client
import sys

MQTT_HOST = 'lntest1.japaneast.cloudapp.azure.com'
MQTT_PORT = 1883


def main(topic, msg):
    client = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    client.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
    client.publish(topic, msg)


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
