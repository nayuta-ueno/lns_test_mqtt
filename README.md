# lns_test_mqtt
lnshieldのテスト用だが、そうでなくても使える。

## やれること

* testnetで動く、c-lightningとptarmiganを使った連続テスト
* MQTTを使っているので、どちらかがグローバルIPを持っていれば使える
  * 今回は、c-lightning側がグローバルIPを持っている

## テスト内容

1. ptarminganがc-lightningにconnectする
2. c-lightningがptarmiganにfundingする
3. funding_lockedを待つ
4. normal operationになったら、ptarmiganがinvoiceを発行し、c-lightningが支払う
5. 5回送金を行ったら、ptarmiganがcloseする
6. closeが終わったら、1に戻る

### こなれてはいない

* あまりこなれてないので、やりたいことを変更する場合はコーディングが必要

## 準備

### MQTT broker

```
sudo apt install mosquitto
```

### requester, responser

```
sudo apt install python3-pip
sudo pip3 install -U pip
sudo pip3 install pylightning paho-mqtt
```

## 手順

1. Mosquittoをどこかに立てる
  * ここでは`lntest1.japaneast.cloudapp.azure.com:1883`
2. c-lightningをグローバルIPが使えるところに立てる
  2.1 `--rpc-file`でどこかを指定する(ここでは`/tmp/lightningrpc`)
3. ptarmiganをどこかに立てる
4. それぞれのノードが立っているところでresponserを起動
  4.1 c-lightning: `python3 mqtt_responser.py clightning /tmp/lightningrpc`
  4.2 ptarmigan: `python3 mqtt_responser.py ptarm`
5. requesterを起動
  5.1 `python3 mqtt_requester [c-lightningのnode_id] [ptarmiganのnode_id]
    * 前者がfunder、後者がfundeeになる
6. 放置
