# encoding: utf-8

import socket
import sys
import json
import traceback
import time

from lnnode import LnNode
from ptarm_base import PtarmBase


class Ptarm(PtarmBase):
    # result[1] = "OK" or "NG"
    def open_channel(self, node_id, amount):
        res = ''
        time.sleep(3)       #wait init exchange

        fconf = self.linux_cmd_exec('./ptarm_fundin.sh ' + str(100000 + amount) + ' ' + str(amount) + ' 0')
        if fconf is None:
            print('fail: pay_fundin.sh')
            return '{"result": ["openchannel","NG"]}'
        else:
            print('fconf=' + fconf)

        ipaddr_dummy = '"0.0.0.0",0'
        txid = "0000000000000000000000000000000000000000000000000000000000000000"
        txindex = 0
        # peer_node_id, peer_addr, peer_port, txid, txindex, funding_sat, push_sat, feerate_per_kw, is_private
        cmd = '{"method":"fund","params":["' + node_id + '",' + ipaddr_dummy + ',' + fconf + ',0 ]}'
        print('cmd= ' + cmd)
        response = self.socket_send(cmd)
        print('result= ' + response);
        jrpc = json.loads(response)
        if ('result' in jrpc) and (jrpc['result']['status'] == 'Progressing'):
            while True:
                st = self.get_status(node_id)
                if st == LnNode.Status.FUNDING:
                    print('  status:funding')
                    res = '{"result": ["openchannel","OK","' + node_id + '"]}'
                    break
                print('  funding start check: ' + str(st))
                time.sleep(1)
        else:
            res = '{"result": ["openchannel","NG","' + node_id + '"]}'
        return res
