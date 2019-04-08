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

    ipaddr = '127.0.0.1'
    port = 9735


    @abstractmethod
    def setup(self, ipaddr='127.0.0.1', port=9735, argv=None):
        pass


    @abstractmethod
    def get_status(self, peer):
        pass


    @abstractmethod
    def get_nodeid(self):
        pass


    # result[1] = "OK" or "NG"
    @abstractmethod
    def connect(self, node_id, ipaddr, port):
        pass


    # result[1] = "OK" or "NG"
    @abstractmethod
    def open_channel(self, node_id, amount):
        pass


    # result[1] = BOLT11 or "NG"
    @abstractmethod
    def get_invoice(self, amount_msat, label=''):
        pass


    # result[1] = "OK" or "NG"
    @abstractmethod
    def pay(self, invoice):
        pass


    # result[1] = "OK" or "NG"
    @abstractmethod
    def close_mutual(self, node_id):
        pass
