# encoding: utf-8

from abc import ABCMeta, abstractmethod


class LnNode(metaclass=ABCMeta):
    @abstractmethod
    def setup(self):
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
