# -*- coding: utf-8 -*-

from max.client import Client as MaxClient
from secrets import MAX_KEY, MAX_SECRET
from ccxt.base.exchange import Exchange
import math
from urllib.error import HTTPError
import ccxt


class MaxAdapter(Exchange):
    def __init__(self):
        Exchange.__init__(self)
        client = MaxClient(MAX_KEY, MAX_SECRET)
        self.client = client
        self.maker_fee_rate = 0.001
        self.taker_fee_rate = 0.0015

    @staticmethod
    def get_min_trade_volume_limit(symbol):
        symbol = symbol.upper()
        if 'TWD' == symbol:
            return 250
        elif 'BTC' == symbol:
            return 0.0015
        elif 'ETH' == symbol:
            return 0.05
        elif 'LTC' == symbol:
            return 0.1112
        elif 'BCH' == symbol:
            return 0.03
        elif 'MITH' == symbol:
            return 190.0
        elif 'USDT' == symbol:
            return 8
        elif 'TRX' == symbol:
            return 340.0
        elif 'CCCX' == symbol:
            return 2100.0
        elif 'EOS' == symbol:
            return 1.7
        elif 'BAT' == symbol:
            return 20.0
        elif 'ZRX' == symbol:
            return 30.0
        elif 'GNT' == symbol:
            return 110.0
        elif 'OMG' == symbol:
            return 5.0
        elif 'KNC' == symbol:
            return 36.0
        elif 'XRP' == symbol:
            return 27.0
        elif 'FMF' == symbol:
            return 8000.0
        elif 'MAX' == symbol:
            return 100.0
        elif 'SEELE' == symbol:
            return 1180.0
        elif 'BCNT' == symbol:
            return 300.0
        else:
            return None

    def fetch_order_book(self, symbol, limit=None, params=None):
        if limit is None:
            limit = 5
        market_id = self.pair_symbol_to_martet_id(symbol)
        # 回傳的 asks 是由價格高排到低，要反過來把最低價排在前面
        response = self.client.get_public_pair_depth(market_id, limit)
        orderbook = self.parse_order_book(response)
        return orderbook

    def fetch_ticker(self, pair_symbol, params=None):
        self.load_markets()
        market_id = self.pair_symbol_to_martet_id(pair_symbol)
        response = self.client.get_public_all_tickers(market_id)
        market = self.markets[pair_symbol]
        return self.parse_ticker(response, market)

    def parse_ticker(self, ticker, market=None):
        self.load_markets()
        timestamp = self.safe_float(ticker, 'at')
        if timestamp is not None:
            timestamp *= 1000
        symbol = market['symbol']
        last = self.safe_float(ticker, 'last')
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'high': self.safe_float(ticker, 'high'),
            'low': self.safe_float(ticker, 'low'),
            'bid': self.safe_float(ticker, 'buy'),
            'bidVolume': None,
            'ask': self.safe_float(ticker, 'sell'),
            'askVolume': None,
            'vwap': None,
            'open': self.safe_float(ticker, 'open'),
            'close': last,
            'last': last,
            'previousClose': None,
            'change': None,
            'percentage': None,
            'average': None,
            'baseVolume': self.safe_float(ticker, 'vol'),
            'quoteVolume': None,
            'info': ticker,
        }

    def fetch_balance(self):
        response = self.client.get_private_account_balances()
        result = {'info': response}
        for balance in response:
            currencyId = balance['currency']
            code = self.safe_currency_code(currencyId)
            account = self.account()
            account['free'] = self.safe_float(balance, 'balance')
            account['used'] = self.safe_float(balance, 'locked')
            result[code] = account
        return self.parse_balance(result)

    def create_order(self, symbol, trade_type, side, amount, price=None, params=None):
        if params is None:
            params = {}
        if price is None:
            price = ''
        stop_price = ''
        if 'stopPrice' in params:
            stop_price = params['stopPrice']
        self.load_markets()
        market = self.markets[symbol]
        market_id = market['id']
        response = None
        amount = self.amount_to_precision(symbol, amount)
        try:
            response = self.client.set_private_create_order(market_id, side, amount, price, stop_price, trade_type)
        except HTTPError as e:
            if str(e) == 'HTTP Error 400: Bad Request':
                raise ccxt.InvalidOrder('not enough trade amount or insufficient fund')

        #print(response)
        return self.parse_order(response)

    def parse_order_status(self, status):
        statuses = {
            'wait': 'open',
            'done': 'closed',
            'cancel': 'canceled',
        }
        return self.safe_string(statuses, status, status)

    def parse_order(self, order, market=None):
        self.load_markets()
        id = self.safe_string(order, 'id')
        timestamp = self.safe_integer(order, 'created_at') * 1000
        market_id = self.safe_string(order, 'market')
        if market is None:
            for key in self.markets:
                entry = self.markets[key]
                if entry['id'] == market_id:
                    market = entry
                    break
        symbol = market['symbol']
        ord_type = self.safe_string(order, 'ord_type')
        side = self.safe_string(order, 'side')
        average = self.safe_float(order, 'avg_price')
        price = self.safe_float(order, 'price')
        if price is None:
            price = average
        amount = self.safe_float(order, 'volume')
        filled = self.safe_float(order, 'executed_volume')
        remaining = self.safe_float(order, 'remaining_volume')
        cost = float(self.cost_to_precision(symbol, price * filled))
        status = self.parse_order_status(self.safe_string(order, 'state'))
        fee = None
        return {
            'info': order,
            'id': id,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'lastTradeTimestamp': None,
            'symbol': symbol,
            'type': ord_type,
            'side': side,
            'price': price,
            'amount': amount,
            'cost': cost,
            'average': average,
            'filled': filled,
            'remaining': remaining,
            'status': status,
            'fee': fee,
        }

    def fetch_markets(self, params=None):
        # 先寫死比較快
        #response = self.client.get_public_all_markets()
        markets = [{'id': 'maxtwd', 'name': 'MAX/TWD', 'base_unit': 'max', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 2}, {'id': 'btctwd', 'name': 'BTC/TWD', 'base_unit': 'btc', 'base_unit_precision': 8, 'quote_unit': 'twd', 'quote_unit_precision': 1}, {'id': 'ethtwd', 'name': 'ETH/TWD', 'base_unit': 'eth', 'base_unit_precision': 6, 'quote_unit': 'twd', 'quote_unit_precision': 1}, {'id': 'ltctwd', 'name': 'LTC/TWD', 'base_unit': 'ltc', 'base_unit_precision': 4, 'quote_unit': 'twd', 'quote_unit_precision': 1}, {'id': 'mithtwd', 'name': 'MITH/TWD', 'base_unit': 'mith', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 3}, {'id': 'bchtwd', 'name': 'BCH/TWD', 'base_unit': 'bch', 'base_unit_precision': 6, 'quote_unit': 'twd', 'quote_unit_precision': 1}, {'id': 'usdttwd', 'name': 'USDT/TWD', 'base_unit': 'usdt', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 2}, {'id': 'maxbtc', 'name': 'MAX/BTC', 'base_unit': 'max', 'base_unit_precision': 2, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'maxeth', 'name': 'MAX/ETH', 'base_unit': 'max', 'base_unit_precision': 2, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'trxtwd', 'name': 'TRX/TWD', 'base_unit': 'trx', 'base_unit_precision': 1, 'quote_unit': 'twd', 'quote_unit_precision': 4}, {'id': 'ethbtc', 'name': 'ETH/BTC', 'base_unit': 'eth', 'base_unit_precision': 4, 'quote_unit': 'btc', 'quote_unit_precision': 6}, {'id': 'trxeth', 'name': 'TRX/ETH', 'base_unit': 'trx', 'base_unit_precision': 1, 'quote_unit': 'eth', 'quote_unit_precision': 8}, {'id': 'maxusdt', 'name': 'MAX/USDT', 'base_unit': 'max', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 3}, {'id': 'btcusdt', 'name': 'BTC/USDT', 'base_unit': 'btc', 'base_unit_precision': 6, 'quote_unit': 'usdt', 'quote_unit_precision': 2}, {'id': 'ethusdt', 'name': 'ETH/USDT', 'base_unit': 'eth', 'base_unit_precision': 5, 'quote_unit': 'usdt', 'quote_unit_precision': 2}, {'id': 'bchusdt', 'name': 'BCH/USDT', 'base_unit': 'bch', 'base_unit_precision': 5, 'quote_unit': 'usdt', 'quote_unit_precision': 2}, {'id': 'ltcusdt', 'name': 'LTC/USDT', 'base_unit': 'ltc', 'base_unit_precision': 5, 'quote_unit': 'usdt', 'quote_unit_precision': 2}, {'id': 'mithbtc', 'name': 'MITH/BTC', 'base_unit': 'mith', 'base_unit_precision': 2, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'mithusdt', 'name': 'MITH/USDT', 'base_unit': 'mith', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 5}, {'id': 'cccxbtc', 'name': 'CCCX/BTC', 'base_unit': 'cccx', 'base_unit_precision': 1, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'cccxeth', 'name': 'CCCX/ETH', 'base_unit': 'cccx', 'base_unit_precision': 1, 'quote_unit': 'eth', 'quote_unit_precision': 8}, {'id': 'cccxtwd', 'name': 'CCCX/TWD', 'base_unit': 'cccx', 'base_unit_precision': 1, 'quote_unit': 'twd', 'quote_unit_precision': 4}, {'id': 'cccxusdt', 'name': 'CCCX/USDT', 'base_unit': 'cccx', 'base_unit_precision': 1, 'quote_unit': 'usdt', 'quote_unit_precision': 6}, {'id': 'eosbtc', 'name': 'EOS/BTC', 'base_unit': 'eos', 'base_unit_precision': 3, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'eoseth', 'name': 'EOS/ETH', 'base_unit': 'eos', 'base_unit_precision': 3, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'eostwd', 'name': 'EOS/TWD', 'base_unit': 'eos', 'base_unit_precision': 3, 'quote_unit': 'twd', 'quote_unit_precision': 3}, {'id': 'eosusdt', 'name': 'EOS/USDT', 'base_unit': 'eos', 'base_unit_precision': 3, 'quote_unit': 'usdt', 'quote_unit_precision': 5}, {'id': 'batbtc', 'name': 'BAT/BTC', 'base_unit': 'bat', 'base_unit_precision': 2, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'bateth', 'name': 'BAT/ETH', 'base_unit': 'bat', 'base_unit_precision': 2, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'battwd', 'name': 'BAT/TWD', 'base_unit': 'bat', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 3}, {'id': 'batusdt', 'name': 'BAT/USDT', 'base_unit': 'bat', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 5}, {'id': 'zrxbtc', 'name': 'ZRX/BTC', 'base_unit': 'zrx', 'base_unit_precision': 2, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'zrxeth', 'name': 'ZRX/ETH', 'base_unit': 'zrx', 'base_unit_precision': 2, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'zrxtwd', 'name': 'ZRX/TWD', 'base_unit': 'zrx', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 2}, {'id': 'zrxusdt', 'name': 'ZRX/USDT', 'base_unit': 'zrx', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 4}, {'id': 'gntbtc', 'name': 'GNT/BTC', 'base_unit': 'gnt', 'base_unit_precision': 2, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'gnteth', 'name': 'GNT/ETH', 'base_unit': 'gnt', 'base_unit_precision': 2, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'gnttwd', 'name': 'GNT/TWD', 'base_unit': 'gnt', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 3}, {'id': 'gntusdt', 'name': 'GNT/USDT', 'base_unit': 'gnt', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 5}, {'id': 'omgbtc', 'name': 'OMG/BTC', 'base_unit': 'omg', 'base_unit_precision': 3, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'omgeth', 'name': 'OMG/ETH', 'base_unit': 'omg', 'base_unit_precision': 3, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'omgtwd', 'name': 'OMG/TWD', 'base_unit': 'omg', 'base_unit_precision': 3, 'quote_unit': 'twd', 'quote_unit_precision': 3}, {'id': 'omgusdt', 'name': 'OMG/USDT', 'base_unit': 'omg', 'base_unit_precision': 3, 'quote_unit': 'usdt', 'quote_unit_precision': 5}, {'id': 'kncbtc', 'name': 'KNC/BTC', 'base_unit': 'knc', 'base_unit_precision': 2, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'knceth', 'name': 'KNC/ETH', 'base_unit': 'knc', 'base_unit_precision': 2, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'knctwd', 'name': 'KNC/TWD', 'base_unit': 'knc', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 2}, {'id': 'kncusdt', 'name': 'KNC/USDT', 'base_unit': 'knc', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 4}, {'id': 'xrptwd', 'name': 'XRP/TWD', 'base_unit': 'xrp', 'base_unit_precision': 2, 'quote_unit': 'twd', 'quote_unit_precision': 3}, {'id': 'xrpusdt', 'name': 'XRP/USDT', 'base_unit': 'xrp', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 5}, {'id': 'trxbtc', 'name': 'TRX/BTC', 'base_unit': 'trx', 'base_unit_precision': 1, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'mitheth', 'name': 'MITH/ETH', 'base_unit': 'mith', 'base_unit_precision': 2, 'quote_unit': 'eth', 'quote_unit_precision': 6}, {'id': 'ltcmax', 'name': 'LTC/MAX', 'base_unit': 'ltc', 'base_unit_precision': 5, 'quote_unit': 'max', 'quote_unit_precision': 2}, {'id': 'bchmax', 'name': 'BCH/MAX', 'base_unit': 'bch', 'base_unit_precision': 5, 'quote_unit': 'max', 'quote_unit_precision': 2}, {'id': 'mithmax', 'name': 'MITH/MAX', 'base_unit': 'mith', 'base_unit_precision': 2, 'quote_unit': 'max', 'quote_unit_precision': 5}, {'id': 'trxusdt', 'name': 'TRX/USDT', 'base_unit': 'trx', 'base_unit_precision': 1, 'quote_unit': 'usdt', 'quote_unit_precision': 6}, {'id': 'trxmax', 'name': 'TRX/MAX', 'base_unit': 'trx', 'base_unit_precision': 1, 'quote_unit': 'max', 'quote_unit_precision': 6}, {'id': 'cccxmax', 'name': 'CCCX/MAX', 'base_unit': 'cccx', 'base_unit_precision': 1, 'quote_unit': 'max', 'quote_unit_precision': 6}, {'id': 'eosmax', 'name': 'EOS/MAX', 'base_unit': 'eos', 'base_unit_precision': 3, 'quote_unit': 'max', 'quote_unit_precision': 5}, {'id': 'batmax', 'name': 'BAT/MAX', 'base_unit': 'bat', 'base_unit_precision': 2, 'quote_unit': 'max', 'quote_unit_precision': 5}, {'id': 'zrxmax', 'name': 'ZRX/MAX', 'base_unit': 'zrx', 'base_unit_precision': 2, 'quote_unit': 'max', 'quote_unit_precision': 4}, {'id': 'gntmax', 'name': 'GNT/MAX', 'base_unit': 'gnt', 'base_unit_precision': 2, 'quote_unit': 'max', 'quote_unit_precision': 5}, {'id': 'omgmax', 'name': 'OMG/MAX', 'base_unit': 'omg', 'base_unit_precision': 3, 'quote_unit': 'max', 'quote_unit_precision': 5}, {'id': 'kncmax', 'name': 'KNC/MAX', 'base_unit': 'knc', 'base_unit_precision': 2, 'quote_unit': 'max', 'quote_unit_precision': 4}, {'id': 'xrpmax', 'name': 'XRP/MAX', 'base_unit': 'xrp', 'base_unit_precision': 2, 'quote_unit': 'max', 'quote_unit_precision': 5}, {'id': 'fmfmax', 'name': 'FMF/MAX', 'base_unit': 'fmf', 'base_unit_precision': 1, 'quote_unit': 'max', 'quote_unit_precision': 6}, {'id': 'fmfeth', 'name': 'FMF/ETH', 'base_unit': 'fmf', 'base_unit_precision': 1, 'quote_unit': 'eth', 'quote_unit_precision': 8}, {'id': 'seelebtc', 'name': 'SEELE/BTC', 'base_unit': 'seele', 'base_unit_precision': 2, 'quote_unit': 'btc', 'quote_unit_precision': 8}, {'id': 'seeleusdt', 'name': 'SEELE/USDT', 'base_unit': 'seele', 'base_unit_precision': 2, 'quote_unit': 'usdt', 'quote_unit_precision': 6}, {'id': 'seelemax', 'name': 'SEELE/MAX', 'base_unit': 'seele', 'base_unit_precision': 2, 'quote_unit': 'max', 'quote_unit_precision': 6}, {'id': 'bcnttwd', 'name': 'BCNT/TWD', 'base_unit': 'bcnt', 'base_unit_precision': 1, 'quote_unit': 'twd', 'quote_unit_precision': 4}, {'id': 'bcntusdt', 'name': 'BCNT/USDT', 'base_unit': 'bcnt', 'base_unit_precision': 1, 'quote_unit': 'usdt', 'quote_unit_precision': 5}, {'id': 'bcntmax', 'name': 'BCNT/MAX', 'base_unit': 'bcnt', 'base_unit_precision': 1, 'quote_unit': 'max', 'quote_unit_precision': 6}]

        result = []
        for i in range(0, len(markets)):
            market = markets[i]
            id = self.safe_string(market, 'id')
            baseId = market['base_unit']
            quoteId = market['quote_unit']
            base = self.safe_currency_code(baseId)
            quote = self.safe_currency_code(quoteId)
            symbol = base + '/' + quote
            precision = {
                'base': market['base_unit_precision'],
                'quote': market['quote_unit_precision'],
                'amount': market['base_unit_precision'],
                'price': market['quote_unit_precision'],
            }
            entry = {
                'id': id,
                'symbol': symbol,
                'base': base,
                'quote': quote,
                'baseId': baseId,
                'quoteId': quoteId,
                'info': market,
                'active': None,
                'precision': precision,
                'limits': {
                    'amount': {
                        'min': math.pow(10, -precision['amount']),
                        'max': None,
                    },
                    'price': {
                        'min': None,
                        'max': None,
                    },
                    'cost': {
                        'min': -1 * math.log10(precision['amount']),
                        'max': None,
                    },
                },
            }
            result.append(entry)
        return result

    def fetch_order(self, id, symbol=None, params=None):
        if params is None:
            params = {}
        self.load_markets()
        id = str(id)
        response = self.client.get_private_order_detail(id)
        #print(response)
        order = self.parse_order(response)
        return order

    def fetch_orders(self, symbol=None, since=None, limit=None, params=None):
        if params is None:
            params = {}
        if limit is None:
            limit=100
        self.load_markets()
        market = self.markets[symbol]
        market_id = market['id']
        state = ['wait', 'done', 'cancel', 'convert']
        response = self.client.get_private_order_history(market_id, state=state, limit=limit, sort='desc')
        #print(response)
        orders = self.parse_orders(response, market, since, limit)
        return orders

    @staticmethod
    def pair_symbol_to_martet_id(symbol):
        return symbol.replace('/', '').lower()
