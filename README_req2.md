# mqtt_req2.py

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
./rrt_cln_fund.sh 3333
```

6. requester起動

```
cd lns_test_mqtt
python3 mqtt_req2.py <NODE1のnode_id> <HOPのnode_id> <NODE2のnode_id>
```
