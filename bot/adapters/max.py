# -*- coding: utf-8 -*-

from max.client import Client as MaxClient
from secrets import MAX_KEY, MAX_SECRET


class MaxAdapter:
    def __init__(self):
        client = MaxClient(MAX_KEY, MAX_SECRET)
        self.client = client

    def fetch_order_book(self, symbol, limit):
        symbol = self.format_symbol(symbol)
        # 回傳的 asks 是由價格高排到低，要反過來把最低價排在前面
        response = self.client.get_public_pair_depth(symbol, limit)
        #print(response)
        asks = response['asks'][::-1]
        response['asks'] = asks
        return response

    def format_symbol(self, symbol):
        return symbol.replace('/', '')
