# encoding: utf-8

import socket
import sys
import json
import traceback

from lnnode import LnNode


PORT_PTARM = 9735

class Ptarm(LnNode):
    rpc_addr = 'localhost'
    rpc_port = PORT_PTARM + 1


    def setup(self, ipaddr='127.0.0.1', port=9735, argv=None):
        self.ipaddr = ipaddr
        self.port = port
        self.rpc_port = port + 1
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
    def get_status(self, num=0):
        try:
            jcmd = '{"method":"getinfo","params":[]}'
            response = self._socket_send(jcmd)
            jrpc = json.loads(response.decode('utf-8'))
            if ('result' not in jrpc) or ('peers' not in jrpc['result']) or (len(jrpc['result']['peers']) == 0):
                return LnNode.Status.NONE
            peer = jrpc['result']['peers'][num]
            peer_status = peer['status']
            #print('(status=', peer_status + ')')
            if peer_status == 'normal operation':
                status = LnNode.Status.NORMAL
            elif peer_status == 'establishing':
                status = LnNode.Status.FUNDING
            elif peer_status == 'close waiting' or\
                peer_status == 'mutual close' or\
                peer_status == 'unilateral close(local)' or\
                peer_status == 'unilateral close(remote)' or\
                peer_status == 'revoked transaction close':
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
            jcmd = '{"method":"getinfo","params":[]}'
            response = self._socket_send(jcmd)
            jrpc = json.loads(response.decode('utf-8'))
            node = jrpc['result']['node_id']
            for peer in jrpc['result']['peers']:
                #print('status=' + peer['status'])
                if peer['status'] == 'normal operation':
                    result = True
                    break
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            sys.exit()
        return node, result


    def connect(self, node_id, ipaddr, port):
        jcmd = '{"method":"connect","params":["' + node_id + '","' + ipaddr + '",' + str(port) + ']}'
        print(jcmd)
        response = self._socket_send(jcmd)
        jrpc = json.loads(response.decode('utf-8'))
        print('jrpc=', jrpc)
        if ('result' in jrpc) and (jrpc['result'] == 'OK'):
            res = '{"result": ["connect","OK"]}'
        elif ('error' in jrpc) and (jrpc['error']['code'] == -10002):
            #already connected
            res = '{"result": ["connect","OK"]}'
        else:
            res = '{"result": ["connect","NG"]}'
        return res


    def disconnect(self, node_id):
        jcmd = '{"method":"disconnect","params":["' + node_id + ',"0.0.0.0",0"]}'
        print(jcmd)
        response = self._socket_send(jcmd)
        jrpc = json.loads(response.decode('utf-8'))
        if ('result' in jrpc) and (jrpc['result'] == 'OK'):
            res = '{"result": ["disconnect","OK"]}'
        else:
            res = '{"result": ["disconnect","NG"]}'
        return res


    def open_channel(self, node_id, amount):
        res = self._socket_send('{"method":"fund","params":[ ' + str(amount) + ',0 ]}')
        res = '{"result": ["openchannel","' + json.loads(res.decode('utf-8'))['result']['bolt11'] + '"]}'
        return res


    def get_invoice(self, amount_msat):
        res = self._socket_send('{"method":"invoice","params":[ ' + str(amount_msat) + ',0 ]}')
        res = '{"result": ["invoice","' + json.loads(res.decode('utf-8'))['result']['bolt11'] + '"]}'
        return res


    def pay(self, invoice):
        res = self._socket_send('{"method":"routepay","params":["' + invoice + '",0]}')
        res = '{"result": ["pay"]}'
        return res


    def close_mutual(self, node_id):
        res = self._socket_send('{"method":"close","params":["' + node_id + '","0.0.0.0",0]}')
        res = '{"result": ["closechannel"]}'
        return res


    def _socket_send(self, req):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self.rpc_addr, self.rpc_port))
        client.send(req.encode())
        response = client.recv(4096)
        client.close()
        return response
