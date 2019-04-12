# mqtt_req3.py

```text
NODE1 -+-> HOP --> NODE2
       |
NODE3 -+
```

* 説明文はregtestとして書いているが、IPアドレスなどを変更することでtestnetなどでも動く
* 都合上、`&`を付けてバックグラウンド起動させているが、個別にコンソールを立てた方がわかりやすいだろう
  * コンソールは、1つのLNノードに対して2つ、テスト制御として1つ(このテストは4ノードなので、最低9コンソール)
* NODE1(port=3333), NODE2(port=4444), NODE3(port=5555): c-lightning
* HOP = ptarmigan(port=9735)
* payer=NODE1, NODE3、payee=NODE2を繰り返す

0. bitcoindをregtestで起動

1. ノード立ち上げ

```bash
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
./rrt_cln_mqtt.sh REQ3 3333&
./rrt_cln_mqtt.sh REQ3 4444&
./rrt_cln_mqtt.sh REQ3 5555&
./rrt_pt.sh REQ3 9735&
```

2. NODE1, NODE3に入金

```bash
cd lns_mqtt_test
./rrt_cln_pay.sh 3333
./rrt_cln_pay.sh 5555
```

3. regtestのgenerator起動

```bash
cd lns_mqtt_test
./regtestkeepfee.sh&
```

4. 2の入金が反映されるのを待つ

```bash
cd lns_mqtt_test
./rrt_cln_fund.sh 3333
./rrt_cln_fund.sh 5555
```

5. テスト開始

```bash
cd lns_mqtt_test
python3 mqtt_req3.py <NODE1> <NODE3> <HOP> <NODE2>
```

----

## 簡易実行

* regtest
  * 事前に`regtestkeepfee.sh`をバックグラウンドで動かしておくのが良い。
* config.iniの編集
  * `TOPIC_PREFIX`: MQTT topicのprefix
  * `PORTBASE`: 使い始めるポート番号
    * 1ノードで10個ずつインクリメントして使う
* rrt_req3.shの編集
  * `STARTGENERATOR`: `regtestkeepfee.sh`の起動有無
    * 個人的には、`regtestkeepfee.sh`は手動で起動させたほうが良いと思う(複数テストを走らせる場合に忘れやすいので)

```bash
./rrt_req3.sh
```
