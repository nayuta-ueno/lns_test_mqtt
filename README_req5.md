# mqtt_req5.py

```text
node1--+-hop-+-node2
       |     |
node3--+     +-node4
       |     |
       |     |
node19-+     +-node20
```

* 図の左側(奇数番号)がfunderかつpayer
* 図の右側(偶数番号)がfundeeかつpayee
* 個別の起動方法は[req3](README_req3.md)を参照
* 注: デフォルトのptarmdは10接続までしかできないため、接続に失敗してfundingまで進まない

## 簡易実行

* regtest
  * 事前に`regtestkeepfee.sh`をバックグラウンドで動かしておくのが良い。
* config.iniの編集
  * `TOPIC_PREFIX`: MQTT topicのprefix
  * `PORTBASE`: 使い始めるポート番号
    * 1ノードで2個ずつインクリメントして使う

```bash
./rrt_req5.sh
```
