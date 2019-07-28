# -*- coding: utf-8 -*-

import ccxt
from secrets import BITFINEX_KEY, BITFINEX_SECRET


class BitfinexAdapter:
    def __init__(self):
        client = ccxt.bitfinex({
            'apiKey': BITFINEX_KEY,
            'secret': BITFINEX_SECRET,
            'enableRateLimit': True,
        })
        self.client = client
        self.maker_fee_rate = 0.001
        self.taker_fee_rate = 0.002

    def __getattr__(self, name):
        return getattr(self.client, name)
