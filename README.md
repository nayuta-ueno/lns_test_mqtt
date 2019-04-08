# lns_test_mqtt

## やれること

* c-lightningとptarmiganを使った連続テスト
* c-lightningとptarmiganを同じような操作だけで動かせるようにする(したい)

## 役割

* requester
  - テスト全体を動かす

* responser
  - reqesterからの指示通りに動かし、指示通りに結果を返す
  - 定期的に自分の状態を返す
  - ノードの種類に依存するが、テストに依存しない

## インストール

### MQTT broker

brokerになりたいマシンだけで良い

```
sudo apt install mosquitto
```

### requester, responser

```
sudo apt install python3-pip
sudo pip3 install -U pip
sudo pip3 install pylightning paho-mqtt
```

### ノード

ビルドに必要なaptなどは省略

```
#c-lightning
git clone https://github.com/ElementsProject/lightning.git
cd lightning
./configure
make

cd ..

#ptarmigan
git clone https://github.com/nayutaco/ptarmigan.git
cd ptarmigan
make full

cd ..
```

### test

```
git clone https://github.com/nayuta-ueno/lns_test_mqtt.git
cp lns_test_mqtt/rrt_cln*.sh ./lightning/
```

## テスト内容

* [mqtt_req3.py](README_req3.md)
* [mqtt_req2.py](README_req2.md)
* (中止)mqtt_req1.py
