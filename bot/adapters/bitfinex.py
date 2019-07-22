# -*- coding: utf-8 -*-

import ccxt
from secrets import BITFINEX_KEY, BITFINEX_SECRET


class BitfinexAdapter:
    def __init__(self):
        client = ccxt.bitfinex({
            'apiKey': BITFINEX_KEY,
            'secret': BITFINEX_SECRET,
        })
        self.client = client

    def fetch_order_book(self, symbol, limit):
        return self.client.fetch_order_book(symbol, limit)
