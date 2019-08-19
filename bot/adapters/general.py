# -*- coding: utf-8 -*-

import ccxt
from secrets import LIQUID_KEY, LIQUID_SECRET


class GeneralAdapter:
    def __init__(self, KEY=None, SECRET=None):
        client = ccxt.liquid({
            'apiKey': KEY,
            'secret': SECRET,
        })
        self.client = client

    @staticmethod
    def get_min_trade_volume_limit(symbol):
        return 0

    def __getattr__(self, name):
        return getattr(self.client, name)
