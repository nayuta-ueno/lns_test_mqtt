# encoding: utf-8
# pip3 install pylightning
# ./lightningd/lightningd --rpc-file=/tmp/lightningrpc --testnet

import socket
import sys
import json
import traceback

from lnnode import LnNode
from lightning import LightningRpc
import random


class CLightning(LnNode):
    lnrpc = ''
    rpc_file = '/tmp/lightningrpc'


    def setup(self, ipaddr='127.0.0.1', port=9735, argv=None):
        self.ipaddr = ipaddr
        self.port = port
        if argv != None:
            self.rpc_file = argv
        self.lnrpc = LightningRpc(self.rpc_file)


    '''
    enum channel_state {
        /* In channeld, still waiting for lockin. */
        CHANNELD_AWAITING_LOCKIN = 2,

        /* Normal operating state. */
        CHANNELD_NORMAL,

        /* We are closing, pending HTLC resolution. */
        CHANNELD_SHUTTING_DOWN,

        /* Exchanging signatures on closing tx. */
        CLOSINGD_SIGEXCHANGE,

        /* Waiting for onchain event. */
        CLOSINGD_COMPLETE,

        /* Waiting for unilateral close to hit blockchain. */
        AWAITING_UNILATERAL,

        /* We've seen the funding spent, we're waiting for onchaind. */
        FUNDING_SPEND_SEEN,

        /* On chain */
        ONCHAIN
    };
    '''
    def get_status(self, num=-1):
        try:
            result = self.lnrpc.listpeers()
            if ('peers' not in result) or (len(result['peers']) == 0):
                return LnNode.Status.NONE
            if num == -1:
                num = 0
                for p in result['peers']:
                    for ch in p['channels']:
                        #print('status[' + str(num) + ']' + ch['state'])
                        if ch['state'] != 'ONCHAIN':
                            peer_status = ch['state']
                            break
                    else:
                        num += 1
                        continue
                    break
            peer = result['peers'][num]
            peer_status = ''
            for ch in peer['channels']:
                if ch['state'] != 'ONCHAIN':
                    peer_status = ch['state']
                    break
            #print('(status=', peer_status + ')')
            if peer_status == 'CHANNELD_NORMAL':
                status = LnNode.Status.NORMAL
            elif peer_status == 'CHANNELD_AWAITING_LOCKIN':
                status = LnNode.Status.FUNDING
            elif peer_status == 'CHANNELD_SHUTTING_DOWN' or\
                peer_status == 'CLOSINGD_SIGEXCHANGE' or\
                peer_status == 'CLOSINGD_COMPLETE' or\
                peer_status == 'AWAITING_UNILATERAL' or\
                peer_status == 'FUNDING_SPEND_SEEN':
                status = LnNode.Status.CLOSING
            else:
                status = LnNode.Status.NONE
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            status = LnNode.Status.NONE
        return status


    def check_status(self):
        node = ''
        result = False
        try:
            info = self.lnrpc.getinfo()
            node = info['id']
            status = self.get_status()
            if status == LnNode.Status.NORMAL:
                result = True
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            sys.exit()
        return node, result


    def connect(self, node_id, ipaddr, port):
        pass


    def open_channel(self, node_id, amount):
        res = self.lnrpc.fundchannel(node_id, amount)
        #print('open_channel=', res)
        res = '{"result": ["openchannel","' + res['txid'] + '"]}'
        return res


    def get_invoice(self, amount_msat):
        res = self.lnrpc.invoice(amount_msat, "lbl{}".format(random.random()), "testpayment")
        res = '{"result": ["invoice","' + res['bolt11'] + '"]}'
        return res


    def pay(self, invoice):
        res = self.lnrpc.pay(invoice)
        print('pay=', res)
        res = '{"result": ["pay"]}'
        return res


    def close_mutual(self, node_id):
        res = self.lnrpc.close(node_id)
        res = '{"result": ["closechannel"]]}'
        return res
