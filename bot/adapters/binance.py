# -*- coding: utf-8 -*-

import ccxt
from secrets import BINANCE_KEY, BINANCE_SECRET
import websockets
import json
import bot.helpers.utils as utils


order_books = {}


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

    async def stream_book_tickers(self, markets):
        utils.order_books['binance'] = {}
        stream_names = []
        for symbol in markets:
            market_string = symbol.replace('/', '').lower()
            stream_name = '{}@bookTicker'.format(market_string)
            stream_names.append(stream_name)
        stream_names_string = '/'.join(stream_names)
        uri = '{}/stream?streams={}'.format(self.websocket_uri, stream_names_string)
        async with websockets.connect(uri) as websocket:
            while True:
                result = await websocket.recv()
                data = json.loads(result)['data']
                imploded_symbol = data['s']
                bid_info = [[data['b'], data['B']]]
                ask_info = [[data['a'], data['A']]]
                utils.order_books['binance'][imploded_symbol] = {'bids': bid_info, 'asks': ask_info}
