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
        cmd = '{"method":"fund","params":["' + node_id + '","0.0.0.0",0,"0000000000000000000000000000000000000000000000000000000000000000",0,' + str(amount) + ',0,0,0 ]}'
        print('cmd= ' + cmd)
        response = self._socket_send(cmd)
        print('result= ' + response.decode('utf-8'));
        jrpc = json.loads(response.decode('utf-8'))
        if ('result' in jrpc) and (jrpc['result']['status'] == 'Progressing'):
            while True:
                st = self.get_status()
                if st == LnNode.Status.FUNDING:
                    res = '{"result": ["openchannel","OK"]}'
                    break
                print('  funding start check: ' + str(st))
                time.sleep(1)
        else:
            res = '{"result": ["openchannel","NG"]}'
        return res
