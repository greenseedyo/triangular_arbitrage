# -*- coding: utf-8 -*-

from bot.adapters.ccxt_adapter import CcxtAdapter
from secrets import LIQUID_KEY, LIQUID_SECRET


class LiquidAdapter(CcxtAdapter):
    ccxt_module_name = 'liquid'
    apiKey = LIQUID_KEY
    secret = LIQUID_SECRET
    fees = {
        'trading': {
            'maker': 0.001,
            'taker': 0.001
        }
    }
