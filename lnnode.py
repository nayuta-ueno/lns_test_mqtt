# encoding: utf-8

from abc import ABCMeta, abstractmethod
from enum import Enum


class LnNode(metaclass=ABCMeta):
    class Status(Enum):
        UNKNOWN = -1
        NONE = 0
        FUNDING = 1
        NORMAL = 2
        CLOSING = 3

    def __init__(self):
        self.ipaddr = '127.0.0.1'
        self.port = 9735

    @abstractmethod
    def setup(self, ipaddr='127.0.0.1', port=9735, argv=None):
        pass

    @abstractmethod
    def get_name(self):
        return 'noname'

    @abstractmethod
    def get_status(self, peer):
        return Status.UNKNOWN, -1

    @abstractmethod
    def get_nodeid(self):
        return '@@@'

    # result[1] = "OK" or "NG"
    @abstractmethod
    def connect(self, node_id, ipaddr, port):
        return '{"result": ["connect","NG","@@@"]}'

    # result[1] = "OK" or "NG"
    @abstractmethod
    def disconnect(self, node_id, ipaddr, port):
        return '{"result": ["disconnect","NG","@@@"]}'

    # result[1] = "OK" or "NG"
    @abstractmethod
    def open_channel(self, node_id, amount):
        return '{"result": ["openchannel","NG","@@@"]}'

    # result[1] = BOLT11 or "NG"
    @abstractmethod
    def get_invoice(self, amount_msat, label=''):
        return '{"result": ["invoice","NG","@@@"]}'

    # result[1] = "OK" or "NG"
    @abstractmethod
    def pay(self, invoice):
        return '{"result": ["pay","NG","@@@"]}'

    # result[1] = "OK" or "NG"
    @abstractmethod
    def close_mutual(self, node_id):
        return '{"result": ["closechannel","NG","@@@"]}'

    # result[1] = "OK" or "NG"
    def close_force(self, node_id):
        return '{"result": ["closechannel_force","NG","@@@"]}'
