# mqtt_req1.py

```text
node1---node2
```

* node1がfunderかつpayer
* node2がfundeeかつpayee

## 簡易実行

* regtest
  * 事前に`regtestkeepfee.sh`をバックグラウンドで動かしておくのが良い。
* config.iniの編集
  * `TOPIC_PREFIX`: MQTT topicのprefix
  * `PORTBASE`: 使い始めるポート番号
    * 1ノードで10個ずつインクリメントして使う

```bash
./rrt_req1.sh
```
