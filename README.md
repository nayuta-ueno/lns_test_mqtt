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

## regtest feerate

regtestを使う場合、estimatesmartfeeで取得できないことがあるため、
`regtestkeepfee.sh`というスクリプトを用意した。

```bash
bitcoin-cli getblockcount

# blockが少ない場合は、予め作成しておくこと(500くらい作成している)
# feerateが既に取得できて、それが非常に高額な場合は、問題なければブロックチェーンごと削除する

./regtestkeepfee.sh&
```

## テスト内容

* [mqtt_req4.py](README_req4.md)
* [mqtt_req3.py](README_req3.md)
* [mqtt_req2.py](README_req2.md)
* (中止)mqtt_req1.py

## 補足

* MQTTを使っているので、テストが動いているかどうかはMQTTのsubscriberを使って監視するのが良いだろう
  * `lntest1`を使うように書いているので、一度に動かすとどれがどれかわからなくなるという問題があるので、topicでフィルタできるようにすべきか
