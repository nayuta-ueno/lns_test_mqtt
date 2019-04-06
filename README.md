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

## テスト内容

### mqtt_req2.py

`NODE1 --> HOP --> NODE2`
  * regtestの想定
  * NODE1 = c-lightning port=3333
  * HOP = ptarmigan port=9735
  * NODE2 = c-lightning port=4444

1. NODE1を動かす

```
# c-lightning port=3333
cd lightning
rm -rf rt3
./lightningd/lightningd --network=regtest --lightning-dir=rt3 --addr=127.0.0.1:3333 --log-level=debug --rpc-file=/tmp/light3

# responser
cd lns_test_mqtt
python3 mqtt_responser.py clightning 127.0.0.1 3333 /tmp/light3
(NODE1のnode_idが出力される)
```

2. NODE2を動かす

```
# c-lightning port=4444
cd lightning
rm -rf rt4
./lightningd/lightningd --network=regtest --lightning-dir=rt4 --addr=127.0.0.1:4444 --log-level=debug --rpc-file=/tmp/light4

# responser
cd lns_test_mqtt
python3 mqtt_responser.py clightning 127.0.0.1 4444 /tmp/light4
(NODE2のnode_idが出力される)
```

3. HOPを動かす

```
# ptarmigan port=9735
cd ptarmigan/install/rt
rm -rf db logs
../ptarmd --network=regtest

# responser
cd lns_test_mqtt
python3 mqtt_responser.py ptarm 127.0.0.1 9735
(HOPのnode_idが出力される)
```

4. NODE1に送金しておく

```
cd lightning
bitcoin-cli sendtoaddress `./cli/lightning-cli  --rpc-file=/tmp/light3 newaddr | jq -r .address` 0.01
bitcoin-cli generate 1
./cli/lightning-cli  --rpc-file=/tmp/light3 listfunds
(fundされたことを確認する。fundまではしばらく時間がかかるので注意。)
```

5. regtestの場合、定期的にgenerateするスクリプトを実行する

```
cd lns_test_mqtt
./regtestkeepfee.sh
```

6. requester起動

```
cd lns_test_mqtt
python3 mqtt_req2.py <NODE1のnode_id> <HOPのnode_id> <NODE2のnode_id>
```

### (中止)mqtt_req1.py

1. ptarminganがc-lightningにconnectする
2. c-lightningがptarmiganにfundingする
3. funding_lockedを待つ
4. normal operationになったら、ptarmiganがinvoiceを発行し、c-lightningが支払う
5. 5回送金を行ったら、ptarmiganがcloseする
6. closeが終わったら、1に戻る

## インストール

### MQTT broker(brokerになりたいマシンだけで良い)

```
sudo apt install mosquitto
```

### requester, responser

```
sudo apt install python3-pip
sudo pip3 install -U pip
sudo pip3 install pylightning paho-mqtt
```