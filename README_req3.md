# mqtt_req3.py

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
