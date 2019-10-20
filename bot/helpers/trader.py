# -*- coding: utf-8 -*-

import sys
import time
import ccxt
import urllib
from urllib import error
import bot.helpers.utils as utils
import websockets
import threading
import asyncio


class Trader:
    exchange = None
    exchange_adapter = None

    def __init__(self, exchange):
        self.exchange = exchange
        self.exchange_adapter = utils.get_exchange_adapter(exchange)

    def get_order_book(self, pair_symbol, limit):
        order_book = None
        if self.exchange in utils.cross_threads_variables['stream_order_books_dict']:
            if not utils.cross_threads_variables['stream_started']:
                raise ConnectionAbortedError('stream was not alive.')
            key = self.exchange_adapter.get_stream_order_book_key_by_market_symbol(pair_symbol)
            order_books = utils.cross_threads_variables['stream_order_books_dict'][self.exchange]
            # print(order_books)
            if key in order_books:
                order_book = order_books[key]
        else:
            try:
                order_book = self.exchange_adapter.fetch_order_book(pair_symbol, limit=limit)
            except ccxt.ExchangeError:
                raise BadMarketSymbolException
            except ccxt.BadRequest:
                raise BadMarketSymbolException
            except urllib.error.HTTPError:
                raise BadMarketSymbolException
        return order_book

    def get_currencies_amounts(self, symbols):
        balances = self.exchange_adapter.fetch_balance()
        amounts = {}
        for symbol in symbols:
            amounts[symbol] = self.get_currency_amount(symbol, balances)
        return amounts

    def get_currency_amount(self, symbol, balances=None):
        response = self.exchange_adapter.fetch_balance() if balances is None else balances
        try:
            free_amount = response['free'][symbol]
            if free_amount is not None:
                return free_amount
            else:
                total_amount = response['total'][symbol]
                if total_amount is not None:
                    return total_amount
                else:
                    return 0
        except (TypeError, KeyError):
            return 0

    @staticmethod
    def exec_test_trade(symbol_21, symbol_23, symbol_31, volume,
                        price_21, price_23, price_31):
        print('test trade {}-{}-{}, volume: {}, prices: {}, {}, {}'.format(
            symbol_21, symbol_23, symbol_31, volume, price_21, price_23, price_31))
        return

    def exec_forward_trade(self, symbol_21, symbol_23, symbol_31, volume_21,
                           price_21, price_23, price_31):
        utils.log_to_slack('start FORWARD trade, detected prices:\n{}: {}\n{}: {}\n{}: {}'.format(
            symbol_21, price_21, symbol_23, price_23, symbol_31, price_31
        ))

        cur2_amount = self.trade(symbol_21, 'buy', volume_21, price_21)
        time.sleep(1)

        cur3_amount = self.trade(symbol_23, 'sell', cur2_amount, price_23)
        time.sleep(1)

        cur1_amount = self.trade(symbol_31, 'sell', cur3_amount, price_31)
        return cur1_amount

    def exec_reverse_trade(self, symbol_21, symbol_23, symbol_31, volume_31,
                           price_21, price_23, price_31):
        utils.log_to_slack('start REVERSE trade, detected prices:\n{}: {}\n{}: {}\n{}: {}'.format(
            symbol_21, price_21, symbol_23, price_23, symbol_31, price_31
        ))

        cur3_amount = self.trade(symbol_31, 'buy', volume_31, price_31)
        time.sleep(1)

        volume_23 = cur3_amount / price_23
        decrease_step = volume_23 * 0.004
        # 若價格瞬間上漲，cur3_amount 可能不夠買 volume_23，就減少 volume_23，買到為止
        while 1:
            try:
                cur2_amount = self.trade(symbol_23, 'buy', volume_23, price_23)
                break
            except InsufficientFundsException:
                utils.log_to_slack('Insufficient funds.\nDecrease volume by {}'.format(decrease_step))
                volume_23 = volume_23 - decrease_step
        time.sleep(1)

        cur1_amount = self.trade(symbol_21, 'sell', cur2_amount, price_21)
        return cur1_amount

    def get_fee_rate(self, side):
        # side: taker/maker
        return self.exchange_adapter.fees['trading'][side]

    def trade(self, pair_symbol, side, amount, price):
        utils.log_to_slack('Trade start: {0}\n{1} volume: {2:.8f}'.format(pair_symbol, side, amount))
        exchange_adapter = self.exchange_adapter
        response = {}
        try:
            if 'buy' == side:
                acceptable_price = price * 1.01
                response = exchange_adapter.create_limit_buy_order(pair_symbol, amount, acceptable_price)
            elif 'sell' == side:
                acceptable_price = price * 0.99
                response = exchange_adapter.create_limit_sell_order(pair_symbol, amount, acceptable_price)
        except ccxt.InvalidOrder as e:
            msg = 'TRADE SKIPPED - invalid order: {0}. pair: {1}, side: {2}, amount: {3:.8f}'.format(str(e), pair_symbol, side, amount)
            raise InsufficientFundsException(msg)
        except ccxt.InsufficientFunds:
            msg = 'TRADE SKIPPED - insufficient balance. pair: {0}, side: {1}, amount: {2:.8f}'.format(pair_symbol, side, amount)
            raise InsufficientFundsException(msg)
        except Exception as e:
            msg = 'Unknown error: {0}. pair: {1}, side: {2}, amount: {3:.8f}'.format(str(e), pair_symbol, side, amount)
            raise TradeSkippedException(msg)

        order_id = response['id']
        tmp_timestamp = time.time()
        while 1:
            try:
                order = exchange_adapter.fetch_order(order_id, pair_symbol)
            except Exception:
                order = exchange_adapter.fetch_orders(pair_symbol)[-1]
                if order['id'] != order_id:
                    time.sleep(0.5)
                    continue

            if 'closed' != order['status'] and 'canceled' != order['status']:
                current_timestamp = time.time()
                if (current_timestamp - tmp_timestamp) > 1800:
                    utils.log_to_slack('The trade is still uncompleted...')
                    tmp_timestamp = current_timestamp
                time.sleep(0.5)
                continue

            taker_fee_rate = self.get_fee_rate('taker')

            # TODO: use adapter.fetch_trade()
            if 'buy' == side:
                try:
                    fee = order['fee']['cost']
                except Exception as e:
                    fee = order['filled'] * taker_fee_rate
                got_amount = order['filled'] - fee
            else:
                fee = order['cost'] * taker_fee_rate
                got_amount = order['cost'] - fee
            utils.log_to_slack('Trade complete: {0}\ngot amount: {1:.8f}'.format(pair_symbol, got_amount))
            return got_amount

    def thread_stream_order_books(self, market_symbols):
        def run_streaming(trader):
            asyncio.set_event_loop(asyncio.new_event_loop())
            utils.cross_threads_variables['stream_started'] = True
            asyncio.get_event_loop().run_until_complete(trader.stream_order_books(market_symbols))
            utils.cross_threads_variables['stream_started'] = False
        t = threading.Thread(target=run_streaming, args=(self,))
        t.start()

    async def stream_order_books(self, market_symbols):
        utils.cross_threads_variables['stream_order_books_dict'][self.exchange] = {}
        uri = self.exchange_adapter.get_stream_order_books_uri(market_symbols)
        async with websockets.connect(uri) as websocket:
            while True:
                result = await websocket.recv()
                order_book = self.exchange_adapter.format_stream_order_book(result)
                key = self.exchange_adapter.format_stream_order_book_key(result)
                utils.cross_threads_variables['stream_order_books_dict']['binance'][key] = order_book


class TradeSkippedException(Exception):
    pass


class InsufficientFundsException(TradeSkippedException):
    pass


class BadMarketSymbolException(Exception):
    pass
