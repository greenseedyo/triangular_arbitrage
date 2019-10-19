# -*- coding: utf-8 -*-

import ccxt
from bot.adapters.ccxt_adapter import CcxtAdapter


class GeneralAdapter(CcxtAdapter):
    def __init__(self, ccxt_module_name, apiKey=None, secret=None):
        self.ccxt_module_name = ccxt_module_name
        self.apiKey = apiKey
        self.secret = secret
        CcxtAdapter.__init__(self)
