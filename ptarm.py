# encoding: utf-8

import socket
import sys
import json
import traceback
import time

from lnnode import LnNode
from ptarm_base import PtarmBase


class Ptarm(PtarmBase):
    def get_open_command(self, node_id, amount):
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
        return cmd


if __name__ == '__main__':
    ipaddr = sys.argv[1]
    port = int(sys.argv[2])
    ln_node = Ptarm()
    ln_node.setup(ipaddr, port)
    print(ln_node.get_nodeid())
