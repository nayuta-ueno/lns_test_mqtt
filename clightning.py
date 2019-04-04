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
                        # print('status[' + str(num) + ']' + ch['state'])
                        if ch['state'] != 'ONCHAIN':
                            break
                    else:
                        num += 1
                        continue
                    break
            if num >= len(result['peers']):
                return LnNode.Status.NONE
            peer = result['peers'][num]
            peer_status = ''
            for ch in peer['channels']:
                if ch['state'] != 'ONCHAIN':
                    peer_status = ch['state']
                    break
            # print('(status=', peer_status + ')')
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
            status = LnNode.Status.UNKNOWN
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


    # result[1] = "OK" or "NG"
    def connect(self, node_id, ipaddr, port):
        try:
            res = self.lnrpc.connect(node_id, ipaddr, port)
            print('connect=', res)
            res = '{"result": ["connect","OK"]}'
        except:
            print('fail connect')
            res = '{"result": ["connect","NG"]}'
        return res


    # result[1] = "OK" or "NG"
    def disconnect(self, node_id):
        try:
            res = self.lnrpc.disconnect(node_id)
            print('disconnect=', res)
            res = '{"result": ["disconnect","OK"]}'
        except:
            print('fail disconnect')
            res = '{"result": ["disconnect","NG"]}'
        return res


    # result[1] = "OK" or "NG"
    def open_channel(self, node_id, amount):
        try:
            res = self.lnrpc.fundchannel(node_id, amount)
            #print('open_channel=', res)
            res = '{"result": ["openchannel","OK"]}'
        except:
            print('fail open_channel')
            res = '{"result": ["openchannel","NG"]}'
        return res


    # result[1] = BOLT11 or "NG"
    def get_invoice(self, amount_msat):
        try:
            res = self.lnrpc.invoice(amount_msat, "lbl{}".format(random.random()), "testpayment")
            res = '{"result": ["invoice","' + res['bolt11'] + '"]}'
        except:
            print('fail invoice')
            res = '{"result": ["invoice","NG"]}'
        return res


    # result[1] = "OK" or "NG"
    def pay(self, invoice):
        try:
            res = self.lnrpc.pay(invoice)
            print('pay=', res)
            res = '{"result": ["pay","OK"]}'
        except:
            print('fail pay')
            res = '{"result": ["pay","NG"]}'
        return res


    # result[1] = "OK" or "NG"
    def close_mutual(self, node_id):
        try:
            res = self.lnrpc.close(node_id)
            print('close=', res)
            res = '{"result": ["closechannel","OK"]}'
        except:
            print('fail closechannel')
            res = '{"result": ["closechannel","NG"]}'
        return res
