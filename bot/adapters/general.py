# -*- coding: utf-8 -*-

import ccxt


class GeneralAdapter:
    def __init__(self, exchange_name, key=None, secret=None):
        exchange = getattr(ccxt, exchange_name)
        client = exchange({
            'apiKey': key,
            'secret': secret,
        })
        self.client = client

    @staticmethod
    def get_min_trade_volume_limit(symbol):
        return 0

    def __getattr__(self, name):
        return getattr(self.client, name)
