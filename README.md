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

### mqtt_req3.py

```
NODE1 -+-> HOP --> NODE2
       |
NODE3 -+
```
  * 説明文はregtestとして書いているが、IPアドレスなどを変更することでtestnetなどでも動くはず
  * 都合上、`&`を付けてバックグラウンド起動させているが、個別にコンソールを立てた方がわかりやすいだろう
    * コンソールは、1つのLNノードに対して2つ、テスト制御として1つ(このテストは4ノードなので、最低9コンソール)
  * NODE1(port=3333), NODE2(port=4444), NODE3(port=5555): c-lightning
  * HOP = ptarmigan(port=9735)
  * payer=NODE1, NODE3、payee=NODE2を繰り返す

0. bitcoindをregtestで起動

1. ノード立ち上げ

```
cd lns_mqtt_test
cp rrt_cln_daemon.sh ../lightning/
cd ../lightning
./rrt_cln_daemon.sh 3333&
./rrt_cln_daemon.sh 4444&
./rrt_cln_daemon.sh 5555&

pushd ../ptarmigan/install
./new_nodedir.sh rt
cd rt
../ptarmd --network=regtest&
popd

cd lns_mqtt_test
./rrt_cln_mqtt.sh 3333&
./rrt_cln_mqtt.sh 4444&
./rrt_cln_mqtt.sh 5555&
./rrt_pt.sh 9735&
```

2. NODE1, NODE3に入金

```
cd lns_mqtt_test
./rrt_cln_pay.sh 3333
./rrt_cln_pay.sh 5555
```

3. regtestのgenerator起動

```
cd lns_mqtt_test
./regtestkeepfee.sh&
```

4. 2の入金が反映されるのを待つ

```
cd lns_mqtt_test
./rrt_cln_fund.sh 3333
./rrt_cln_fund.sh 5555
```

5. テスト開始

```
cd lns_mqtt_test
python3 mqtt_req3.py <NODE1> <NODE3> <HOP> <NODE2>
```

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
./rrt_cln_daemon.sh 3333

# responser
cd lns_test_mqtt
./rrt_cln_mqtt.sh 3333
(NODE1のnode_idが出力される)
```

2. NODE2を動かす

```
# c-lightning port=4444
cd lightning
./rrt_cln_daemon.sh 4444

# responser
cd lns_test_mqtt
./rrt_cln_mqtt.sh 4444
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
./rrt_pt.sh 9735
(HOPのnode_idが出力される)
```

4. regtestの場合、定期的にgenerateするスクリプトを実行する

```
cd lns_test_mqtt
./regtestkeepfee.sh
```

5. NODE1に送金しておく

```
cd lns_mqtt_test
./rrt_cln_pay.sh 3333

# fundされたことを確認する。fundまではしばらく時間がかかるので注意。
```
./rrt_cln_fund.sh 3333
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
