# mqtt_req4.py

```text
NODE1 -+-> HOP -+--> NODE2
       |        |
NODE3 -+        +--> NODE4
```

* NODE2のinvoiceでNODE1が送金
* NODE4のinvoiceでNODE3が送金
* 個別の起動方法は[req3](README_req3.md)を参照

## 簡易実行

* regtest
  * 事前に`regtestkeepfee.sh`をバックグラウンドで動かしておくのが良い。
* config.iniの編集
  * `TOPIC_PREFIX`: MQTT topicのprefix
  * `PORTBASE`: 使い始めるポート番号
    * 1ノードで10個ずつインクリメントして使う
* rrt_req4.shの編集
  * `STARTGENERATOR`: `regtestkeepfee.sh`の起動有無
    * 個人的には、`regtestkeepfee.sh`は手動で起動させたほうが良いと思う(複数テストを走らせる場合に忘れやすいので)

```bash
./rrt_req4.sh
```
