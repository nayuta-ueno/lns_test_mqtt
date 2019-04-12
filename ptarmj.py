# encoding: utf-8

import socket
import sys
import json
import traceback
import time

from lnnode import LnNode
from ptarm_base import PtarmBase


class PtarmJ(PtarmBase):
    def get_open_command(self, node_id, amount):
        ipaddr_dummy = '"0.0.0.0",0'
        txid = "0000000000000000000000000000000000000000000000000000000000000000"
        txindex = 0
        cmd = '{"method":"fund","params":["' + node_id + '",' + ipaddr_dummy + ',' + txid + ',' + str(txindex) + ',' + str(amount) + ',0,0,0 ]}'
        return cmd


    def get_name(self):
        return 'PtarmJ'


if __name__ == '__main__':
    ipaddr = sys.argv[1]
    port = int(sys.argv[2])
    ln_node = Ptarm()
    ln_node.setup(ipaddr, port)
    print(ln_node.get_nodeid())
