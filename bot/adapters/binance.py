# -*- coding: utf-8 -*-

import ccxt
from secrets import BINANCE_KEY, BINANCE_SECRET
import json


class BinanceAdapter:
    def __init__(self):
        client = ccxt.binance({
            'apiKey': BINANCE_KEY,
            'secret': BINANCE_SECRET,
        })
        self.client = client
        self.maker_fee_rate = 0.001
        self.taker_fee_rate = 0.001
        self.websocket_uri = "wss://stream.binance.com:9443"

    def fetch_trading_limits(self, market_symbol):
        self.load_markets()
        market = self.markets[market_symbol]
        return market['limits']

    def fetch_order_book(self, symbol, limit):
        if limit < 5:
            limit = 5
        return self.client.fetch_order_book(symbol, limit)

    def __getattr__(self, name):
        return getattr(self.client, name)

    def get_stream_order_books_uri(self, market_symbols):
        stream_names = []
        for market_symbol in market_symbols:
            market_string = market_symbol.replace('/', '').lower()
            stream_name = '{}@bookTicker'.format(market_string)
            stream_names.append(stream_name)
        stream_names_string = '/'.join(stream_names)
        uri = '{}/stream?streams={}'.format(self.websocket_uri, stream_names_string)
        return uri

    @staticmethod
    def format_stream_order_book(stream_contents):
        data = json.loads(stream_contents)['data']
        bid_info = [[data['b'], data['B']]]
        ask_info = [[data['a'], data['A']]]
        return {'bids': bid_info, 'asks': ask_info}

    @staticmethod
    def format_stream_order_book_key(stream_contents):
        data = json.loads(stream_contents)['data']
        imploded_symbol = data['s']
        return imploded_symbol

    @staticmethod
    def get_stream_order_book_key_by_market_symbol(market_symbol):
        return market_symbol.replace('/', '')
