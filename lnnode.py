# encoding: utf-8

from abc import ABCMeta, abstractmethod
from enum import Enum, auto


class LnNode(metaclass=ABCMeta):
    class Status(Enum):
        NONE = auto()
        FUNDING = auto()
        NORMAL = auto()
        CLOSING = auto()

    ipaddr = '127.0.0.1'
    port = 9735


    @abstractmethod
    def setup(self, ipaddr='127.0.0.1', port=9735, argv=None):
        pass


    @abstractmethod
    def get_status(self, num=0):
        pass


    @abstractmethod
    def check_status(self):
        pass


    @abstractmethod
    def connect(self, node_id, ipaddr, port):
        pass


    @abstractmethod
    def open_channel(self, node_id, amount):
        pass


    '''
    {"result": ["invoice", "<BOLT11 invoice>"]}
    '''
    @abstractmethod
    def get_invoice(self, amount_msat):
        pass


    @abstractmethod
    def pay(self, invoice):
        pass


    @abstractmethod
    def close_mutual(self, node_id):
        pass
