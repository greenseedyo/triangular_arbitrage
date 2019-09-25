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

    @staticmethod
    def get_min_trade_volume_limit(symbol):
        symbol = symbol.upper()
        if 'USDT' == symbol:
            return 10  # 待確認
        else:
            return None

    def __getattr__(self, name):
        return getattr(self.client, name)
