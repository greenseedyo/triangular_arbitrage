# -*- coding: utf-8 -*-

import ccxt
import json


class CcxtAdapter:
    ccxt_module_name = ''
    apiKey = ''
    secret = ''
    websocket_uri = None

    def __init__(self):
        self.set_client()

    def set_client(self):
        client_init_method = getattr(ccxt, self.ccxt_module_name)
        client = client_init_method({
            'apiKey': self.apiKey,
            'secret': self.secret,
        })
        self.client = client

    def fetch_trading_limits(self, market_symbol):
        self.load_markets()
        market = self.markets[market_symbol]
        return market['limits']

    def __getattr__(self, name):
        return getattr(self.client, name)

    # Websocket implementation
    def get_stream_order_books_uri(self, market_symbols):
        raise NotImplementedError('Websocket not implemented')

    @staticmethod
    def format_stream_order_book(stream_contents):
        raise NotImplementedError('Websocket not implemented')

    @staticmethod
    def format_stream_order_book_key(stream_contents):
        raise NotImplementedError('Websocket not implemented')

    @staticmethod
    def get_stream_order_book_key_by_market_symbol(market_symbol):
        raise NotImplementedError('Websocket not implemented')
