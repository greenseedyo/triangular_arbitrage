# -*- coding: utf-8 -*-

import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))

from max.client import Client as MaxClient
import ccxt
from secrets import MAX_KEY, MAX_SECRET, BITFINEX_KEY, BITFINEX_SECRET

def get_max_client():
    client = MaxClient(MAX_KEY, MAX_SECRET)
    return client

def get_bitfinex_client():
    bfx = BitfinexClient(
        API_KEY=BITFINEX_KEY,
        API_SECRET=BITFINEX_SECRET
    )
    return bfx

def get_local_exchange_info(pair, limit):
    client = get_max_client()
    response = client.get_public_pair_depth(pair, limit)
    asks = []
    bids = []
    # MAX 的 asks 是由價格高排到低，要反過來把最低價排在前面
    for data in reversed(response['asks']):
        ask = {
            'price': data[0],
            'volume': data[1]
        }
        asks.append(ask)

    for data in response['bids']:
        bid = {
            'price': data[0],
            'volume': data[1]
        }
        bids.append(bid)

    info = {
        'timestamp': response['timestamp'],
        'asks': asks,
        'bids': bids,
    }
    print(f"local exchagne info: \n    {info}\n")
    return info

def get_foreign_exchange_info(symbol, length):
    bfx = ccxt.bitfinex({
        'apiKey': BITFINEX_KEY,
        'secret': BITFINEX_SECRET,
    })
    orderbook = bfx.fetch_order_book(symbol, limit=length)
    asks = []
    bids = []
    for data in orderbook['asks']:
        ask = {
            'price': data[0],
            'volume': data[1]
        }
        asks.append(ask)

    for data in orderbook['bids']:
        bid = {
            'price': data[0],
            'volume': data[1]
        }
        bids.append(bid)

    info = {
        'timestamp': orderbook['timestamp'],
        'asks': asks,
        'bids': bids,
    }
    print(f"foreign exchange info: \n    {info}\n")
    return info
