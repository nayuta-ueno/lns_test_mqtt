# c-lightning developer mode

## configure

```bash
./configure --enable-developer
```

## 使えそうなoptions

options.cの`dev_register_opts()`参照

### 引数無し

* --dev-no-reconnect
  * Disable automatic reconnect attempts
* --dev-allow-localhost
  * Announce and allow announcments for localhost address

### 引数あり

* --dev-broadcast-interval=[ms]
  * Time between gossip broadcasts in milliseconds
* --dev-disconnect=[filename]
  * File containing disconnection points
* --dev-bitcoind-poll=[]
  * Time between polling for new transactions
* --dev-channel-update-interval=[s]
  * Time in seconds between channel updates for our own channels.
* --dev-gossip-time=[]
  * UNIX time to override gossipd to use.

## `--dev-disconnect=<filename>`

[使い方](https://github.com/ElementsProject/lightning/issues/366#issuecomment-346249070)

* パケット名の前に`-`をつけると、そのパケットを送信する前に切断
* パケット名の前に`+`をつけると、そのパケットを送信した後に切断
* `*`をパケット名の後ろに書いて数字を書くと、その数字の分だけパケット送信をした後に動作するようだ
* パケット名のルールはissueが書かれた当時と変わって、`WIRE_`で始まる名前になったようだ
* filenameは絶対パスで指定するようだ

### ファイル例

* `update_fulfill_htlc`送信前に切断

```text
-WIRE_UPDATE_FULFILL_HTLC
```
