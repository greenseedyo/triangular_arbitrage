# -*- coding: utf-8 -*-

from bot.adapters.ccxt_adapter import CcxtAdapter
from secrets import BITFINEX_KEY, BITFINEX_SECRET


class BitfinexAdapter(CcxtAdapter):
    ccxt_module_name = 'bitfinex'
    apiKey = BITFINEX_KEY
    secret = BITFINEX_SECRET
