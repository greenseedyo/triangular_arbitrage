# -*- coding: utf-8 -*-

import ccxt
from secrets import BINANCE_KEY, BINANCE_SECRET


class BinanceAdapter:
    def __init__(self):
        client = ccxt.binance({
            'apiKey': BINANCE_KEY,
            'secret': BINANCE_SECRET,
        })
        self.client = client
        self.maker_fee_rate = 0.001
        self.taker_fee_rate = 0.001

    @staticmethod
    def get_min_trade_volume_limit(symbol):
        symbol = symbol.upper()
        if 'USDT' == symbol:
            return 10.1  # 官方寫 10，但實測 10.026 失敗所以多加一點上去
        else:
            return None

    def fetch_order_book(self, symbol, limit):
        if limit < 5:
            limit = 5
        return self.client.fetch_order_book(symbol, limit)

    def __getattr__(self, name):
        return getattr(self.client, name)
