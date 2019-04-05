# encoding: utf-8

import socket
import sys
import json
import traceback
import time

from lnnode import LnNode
from ptarm_base import PtarmBase


class PtarmJ(PtarmBase):
    # result[1] = "OK" or "NG"
    def open_channel(self, node_id, amount):
        res = ''
        time.sleep(3)       #wait init exchange
        ipaddr_dummy = '"0.0.0.0",0'
        txid = "0000000000000000000000000000000000000000000000000000000000000000"
        txindex = 0
        cmd = '{"method":"fund","params":["' + node_id + '",' + ipaddr_dummy + ',' + txid + ',' + str(txindex) + ',' + str(amount) + ',0,0,0 ]}'
        print('cmd= ' + cmd)
        response = self.socket_send(cmd)
        print('result= ' + response);
        jrpc = json.loads(response)
        if ('result' in jrpc) and (jrpc['result']['status'] == 'Progressing'):
            while True:
                st = self.get_status()
                if st == LnNode.Status.FUNDING:
                    res = '{"result": ["openchannel","OK","' + node_id + '"]}'
                    break
                print('  funding start check: ' + str(st))
                time.sleep(1)
        else:
            res = '{"result": ["openchannel","NG","' + node_id + '"]}'
        return res
