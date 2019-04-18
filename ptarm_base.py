# encoding: utf-8

import socket
import os
import json
import traceback
import time
import subprocess
import signal

from lnnode import LnNode


PORT_PTARM = 9735


class PtarmBase(LnNode):
    def __init__(self):
        super().__init__()
        self.rpc_addr = 'localhost'
        self.rpc_port = PORT_PTARM + 1

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
    case LN_STATUS_CLOSED:
        p_str_stat = "closed";
        break;
    default:
        p_str_stat = "???";
    }
    '''
    def get_status(self, peer):
        local_msat = 0
        response = ''
        try:
            jcmd = '{"method":"getinfo","params":[]}'
            response = self.socket_send(jcmd)
            jrpc = json.loads(response)
            if ('result' not in jrpc) or ('peers' not in jrpc['result']) or (len(jrpc['result']['peers']) == 0):
                print('  status: none')
                return LnNode.Status.NONE, 0
            peer_status = ''
            current_ch = None
            for p in jrpc['result']['peers']:
                if p['node_id'] == peer:
                    current_ch = p
                    peer_status = p['status']
                    break
            print('(status=', peer_status + ') : ' + peer)
            if peer_status == 'normal operation':
                status = LnNode.Status.NORMAL
                local_msat = current_ch['local']['msatoshi']
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
            print('response=' + response)
            status = LnNode.Status.UNKNOWN
        return status, local_msat

    def get_nodeid(self):
        try:
            jcmd = '{"method":"getinfo","params":[]}'
            response = self.socket_send(jcmd)
            jrpc = json.loads(response)
            return jrpc['result']['node_id']
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            os.kill(os.getpid(), signal.SIGKILL)

    # result[1] = "OK" or "NG"
    def connect(self, node_id, ipaddr, port):
        jcmd = '{"method":"connect","params":["' + node_id + '","' + ipaddr + '",' + str(port) + ']}'
        print(jcmd)
        response = self.socket_send(jcmd)
        jrpc = json.loads(response)
        print('jrpc=', jrpc)
        if ('result' in jrpc) and (jrpc['result'] == 'OK'):
            res = '{"result": ["connect","OK","' + node_id + '"]}'
        elif ('error' in jrpc) and (jrpc['error']['code'] == -10002):
            # already connected
            res = '{"result": ["connect","OK","' + node_id + '"]}'
        else:
            res = '{"result": ["connect","NG","' + node_id + '"]}'
        return res

    # result[1] = "OK" or "NG"
    def disconnect(self, node_id):
        print('disconnect: ' + node_id)
        jcmd = '{"method":"disconnect","params":["' + node_id + ',"0.0.0.0",0"]}'
        print(jcmd)
        response = self.socket_send(jcmd)
        jrpc = json.loads(response)
        if ('result' in jrpc) and (jrpc['result'] == 'OK'):
            res = '{"result": ["disconnect","OK","' + node_id + '"]}'
        else:
            res = '{"result": ["disconnect","NG","' + node_id + '"]}'
        return res

    # result[1] = BOLT11 or "NG"
    def get_invoice(self, amount_msat, label=''):
        res = self.socket_send('{"method":"invoice","params":[ ' + str(amount_msat) + ',0 ]}')
        if 'error' not in res:
            res = '{"result": ["invoice","' + json.loads(res)['result']['bolt11'] + '","' + label + '"]}'
        else:
            res = '{"result": ["invoice","NG"]}'
        return res

    # result[1] = "OK" or "NG"
    def pay(self, invoice):
        res = self.socket_send('{"method":"routepay","params":["' + invoice + '",0]}')
        if 'error' not in res:
            res = '{"result": ["pay","OK","' + invoice + '"]}'
        else:
            print('fail pay: ' + invoice)
            res = '{"result": ["pay","NG","' + invoice + '"]}'
        return res

    # result[1] = "OK" or "NG"
    def open_channel(self, node_id, amount):
        res = ''
        time.sleep(3)       # wait init exchange

        cmd = self.get_open_command(node_id, amount)
        print('cmd=' + cmd)
        response = self.socket_send(cmd)
        print('result= ' + response)
        jrpc = json.loads(response)
        if ('result' in jrpc) and (jrpc['result']['status'] == 'Progressing'):
            while True:
                st = self.get_status(node_id)[0]
                if st == LnNode.Status.FUNDING:
                    print('  status:funding')
                    res = '{"result": ["openchannel","OK","' + node_id + '"]}'
                    break
                print('  funding start check: ' + str(st))
                time.sleep(1)
        else:
            res = '{"result": ["openchannel","NG","' + node_id + '"]}'
        return res

    # result[1] = "OK" or "NG"
    def close_mutual(self, node_id):
        return self._close(node_id, False)

    # result[1] = "OK" or "NG"
    def close_force(self, node_id):
        return self._close(node_id, True)

    # result[1] = "OK" or "NG"
    def _close(self, node_id, force):
        if force:
            params = '["' + node_id + '","0.0.0.0",0,"force"]'
        else:
            params = '["' + node_id + '","0.0.0.0",0]'
        res = self.socket_send('{"method":"close","params":' + params + '}')
        str_force = 'force' if force else 'mutual'
        if 'error' not in res:
            res = '{"result": ["closechannel","OK","' + node_id + '","' + str_force + '"]}'
        else:
            res = '{"result": ["closechannel","NG","' + node_id + '","' + str_force + '"]}'
        return res

    def socket_send(self, req):
        response = ''
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.rpc_addr, self.rpc_port))
            client.send(req.encode())
            response = client.recv(1024 * 1024).decode('utf-8')
            time.sleep(1)
            # client.close()
        except:
            print('traceback.format_exc():\n%s' % traceback.format_exc())
            os.kill(os.getpid(), signal.SIGKILL)
        return response

    def linux_cmd_exec(self, cmd):
        print('cmd:', cmd.split(' '))
        ret = ''
        try:
            ret = subprocess.check_output(cmd.split(' ')).strip().decode('utf-8')
        except subprocess.CalledProcessError as e:
            print('!!! error happen(errcode=%d) !!!' % e.returncode)
            ret = None
        return ret
