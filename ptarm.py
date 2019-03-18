# encoding: utf-8

import socket
import sys
import json
import traceback

import lnnode


PORT_PTARM = 9735

class Ptarm(lnnode.LnNode):
    rpcaddr = 'localhost'
    rpcport = PORT_PTARM + 1


    def setup(self):
        pass


    def check_status(self):
        node = ''
        result = False
        try:
            jcmd = '{"method":"getinfo","params":[]}'
            response = self._socket_send(jcmd)
            jrpc = json.loads(response.decode('utf-8'))
            node = jrpc['result']['node_id']
            for prm in jrpc['result']['peers']:
                print('status=' + prm['status'])
                if prm['status'] == 'normal operation':
                    result = True
                    break
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            sys.exit()
        return node, result


    def get_invoice(self, amount_msat):
        res = self._socket_send('{"method":"invoice","params":[ ' + str(amount_msat) + ',0 ]}')
        res = '{"result": ["invoice","' + json.loads(res.decode('utf-8'))['result']['bolt11'] + '"]}'
        return res


    def pay(self, invoice):
        res = self._socket_send('{"method":"routepay","params":["' + invoice + '",0]}')
        res = '{"result": ["pay"]}'
        return res


    def _socket_send(self, req):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self.rpcaddr, self.rpcport))
        client.send(req.encode())
        response = client.recv(4096)
        client.close()
        return response
