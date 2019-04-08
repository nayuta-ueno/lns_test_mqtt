# encoding: utf-8
# pip3 install pylightning
# ./lightningd/lightningd --rpc-file=/tmp/lightningrpc --testnet

import socket
import sys
import os
import json
import traceback
import signal

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
    def get_status(self, peer):
        try:
            result = self.lnrpc.listpeers()
            if ('peers' not in result) or (len(result['peers']) == 0):
                return LnNode.Status.NONE
            peer_status = ''
            for p in result['peers']:
                if p['id'] == peer:
                    for ch in p['channels']:
                        if ch['state'] != 'ONCHAIN':
                            # onchainなものは「済」と判断して無視する
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
            os.kill(os.getpid(), signal.SIGKILL)
        return status


    def get_nodeid(self):
        node = ''
        try:
            info = self.lnrpc.getinfo()
            return info['id']
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            os.kill(os.getpid(), signal.SIGKILL)


    # result[1] = "OK" or "NG"
    def connect(self, node_id, ipaddr, port):
        try:
            res = self.lnrpc.connect(node_id, ipaddr, port)
            print('connect=', res)
            res = '{"result": ["connect","OK","' + node_id + '"]}'
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            print('fail connect')
            res = '{"result": ["connect","NG","' + node_id + '"]}'
        return res


    # result[1] = "OK" or "NG"
    def disconnect(self, node_id):
        try:
            res = self.lnrpc.disconnect(node_id)
            print('disconnect=', res)
            res = '{"result": ["disconnect","OK","' + node_id + '"]}'
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            print('fail disconnect')
            res = '{"result": ["disconnect","NG","' + node_id + '"]}'
        return res


    # result[1] = "OK" or "NG"
    def open_channel(self, node_id, amount):
        try:
            res = self.lnrpc.fundchannel(node_id, amount)
            print('open_channel=', res)
            res = '{"result": ["openchannel","OK","' + node_id + '"]}'
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            print('fail open_channel')
            res = '{"result": ["openchannel","NG","' + node_id + '"]}'
        return res


    # result[1] = BOLT11 or "NG"
    def get_invoice(self, amount_msat, label=''):
        try:
            res = self.lnrpc.invoice(amount_msat, "lbl{}".format(random.random()), "testpayment")
            print('invoice=', res)
            res = '{"result": ["invoice","' + res['bolt11'] + '","' + label + '"]}'
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            print('fail invoice')
            res = '{"result": ["invoice","NG","' + label + '"]}'
        return res


    # result[1] = "OK" or "NG"
    def pay(self, invoice):
        try:
            res = self.lnrpc.pay(invoice, riskfactor=100)
            print('pay=', res)
            res = '{"result": ["pay","OK"]}'
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            print('fail pay')
            res = '{"result": ["pay","NG"]}'
        return res


    # result[1] = "OK" or "NG"
    def close_mutual(self, node_id):
        try:
            res = self.lnrpc.close(node_id)
            print('close=', res)
            res = '{"result": ["closechannel","OK","' + node_id + '"]}'
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            print('fail closechannel')
            res = '{"result": ["closechannel","NG","' + node_id + '"]}'
        return res
