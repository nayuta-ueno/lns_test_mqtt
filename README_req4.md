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
* `PORTBASE`: 使い始めるポート番号
  * 1ノードで10個ずつインクリメントして使う
* `STARTGENERATOR`: `regtestkeepfee.sh`の起動有無
  * 個人的には、`regtestkeepfee.sh`は手動で起動させたほうが良いと思う(複数テストを走らせる場合に忘れやすいので)

```bash
./rrt_req4.sh
```
