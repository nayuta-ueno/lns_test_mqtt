# encoding: utf-8

from abc import ABCMeta, abstractmethod
from enum import Enum, auto


class LnNode(metaclass=ABCMeta):
    class Status(Enum):
        NONE = auto()
        FUNDING = auto()
        NORMAL = auto()
        CLOSING = auto()


    @abstractmethod
    def setup(self):
        pass


    @abstractmethod
    def get_status(self, num=0):
        pass


    @abstractmethod
    def check_status(self):
        pass


    @abstractmethod
    def get_invoice(self, amount_msat):
        pass


    @abstractmethod
    def pay(self, invoice):
        pass
