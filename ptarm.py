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

    '''
    switch (pChannel->status) {
    case LN_STATUS_NONE:
        p_str_stat = "none";
        break;
    case LN_STATUS_ESTABLISH:
        p_str_stat = "establishing";
        break;
    case LN_STATUS_NORMAL:
        p_str_stat = "normal operation";
        break;
    case LN_STATUS_CLOSE_WAIT:
        p_str_stat = "close waiting";
        break;
    case LN_STATUS_CLOSE_MUTUAL:
        p_str_stat = "mutual close";
        break;
    case LN_STATUS_CLOSE_UNI_LOCAL:
        p_str_stat = "unilateral close(local)";
        break;
    case LN_STATUS_CLOSE_UNI_REMOTE:
        p_str_stat = "unilateral close(remote)";
        break;
    case LN_STATUS_CLOSE_REVOKED:
        p_str_stat = "revoked transaction close";
        break;
    default:
        p_str_stat = "???";
    }
    '''
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
