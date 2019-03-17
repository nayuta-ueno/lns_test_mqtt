# encoding: utf-8
# pip3 install pylightning
# ./lightningd/lightningd --rpc-file=/tmp/lightningrpc --testnet

import socket
import sys
import json
import traceback

import lnnode
from lightning import LightningRpc
import random


class CLightning(lnnode.LnNode):
    lnrpc = ''


    def setup(self):
        self.lnrpc = LightningRpc("/tmp/lightningrpc")


    def check_status(self):
        node = ''
        result = False
        try:
            info = self.lnrpc.getinfo()
            node = info['id']
            result = self.lnrpc.listpeers()
            for peer in result['peers']:
                print('status=', peer['channels'][0]['state'])
                # 1つでも生きていれば良いことにする
                if peer['channels'][0]['state'] == 'CHANNELD_NORMAL':
                    result = True
                    break
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            sys.exit()
        return node, result


    def get_invoice(self, amount_msat):
        res = self.lnrpc.invoice(amount_msat, "lbl{}".format(random.random()), "testpayment")
        res = '{"result": ["invoice","' + res['bolt11'] + '"]}'
        return res


    def pay(self, invoice):
        res = self.lnrpc.pay(invoice)
        print('pay=', res)
        res = '{"result": ["pay"]}'
        return res
