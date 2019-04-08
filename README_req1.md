# mqtt_req1.py

1. ptarminganがc-lightningにconnectする
2. c-lightningがptarmiganにfundingする
3. funding_lockedを待つ
4. normal operationになったら、ptarmiganがinvoiceを発行し、c-lightningが支払う
5. 5回送金を行ったら、ptarmiganがcloseする
6. closeが終わったら、1に戻る
