# -*- coding: utf-8 -*-

import ccxt
from bot.adapters.ccxt_adapter import CcxtAdapter
from secrets import BITFINEX_KEY, BITFINEX_SECRET


class BitfinexAdapter(CcxtAdapter):

    ccxt_module_name = 'bitfinex'
    apiKey = BITFINEX_KEY
    secret = BITFINEX_SECRET
    maker_fee_rate = 0.001
    taker_fee_rate = 0.002
    websocket_uri = "wss://stream.binance.com:9443"

    def __getattr__(self, name):
        return getattr(self.client, name)
