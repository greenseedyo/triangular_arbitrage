# -*- coding: utf-8 -*-

import sys
import time
import ccxt
import urllib
from urllib import error
from bot.helpers.slack import Slack
import bot.helpers.utils as utils


def get_exchange_adapter(exchange_name):
    exchange_adapter_module_name = 'bot.adapters.{}'.format(exchange_name)
    __import__(exchange_adapter_module_name)
    module = sys.modules[exchange_adapter_module_name]
    adapter_name = '{}Adapter'.format(exchange_name.capitalize())
    adapter = getattr(module, adapter_name)()
    return adapter


class Trader:
    def __init__(self, config):
        self.exchange = config['exchange']
        self.exchange_adapter = get_exchange_adapter(config['exchange'])

    def get_min_trade_volume_limit(self, symbol):
        return self.exchange_adapter.get_min_trade_volume_limit(symbol)

    def get_order_book(self, pair_symbol, limit):
        adapter = self.exchange_adapter
        order_book = None
        while 1:
            try:
                order_book = adapter.fetch_order_book(pair_symbol, limit=limit)
                break
            except ccxt.ExchangeError as e:
                if str(e).find('No market symbol'):
                    break
                else:
                    print(str(e))
                    break
            except urllib.error.HTTPError as e:
                if 'HTTP Error 400: Bad Request' == str(e):
                    return
                else:
                    print('sleep 10s...')
                    time.sleep(10)
                    continue
            except Exception as e:
                # TODO: raise exception
                print(e)
                print('sleep 10s...')
                time.sleep(10)
                continue
        #print(order_book)
        return order_book

    def get_currencies_amounts(self, symbols):
        response = self.exchange_adapter.fetch_balance()
        amounts = {}
        for symbol in symbols:
            try:
                amounts[symbol] = response['free'][symbol]
            except (TypeError, KeyError):
                amounts[symbol] = 0
        return amounts

    def get_currency_amount(self, symbol):
        response = self.exchange_adapter.fetch_balance()
        try:
            amount = response['free'][symbol]
            if amount is None:
                return 0
            else:
                return amount
        except (TypeError, KeyError):
            return 0

    def exec_test_trade(self, symbol_BA, symbol_BC, symbol_CA, volume,
                        price_BA, price_BC, price_CA):
        print('test trade {}-{}-{}, volume: {}, prices: {}, {}, {}'.format(
            symbol_BA, symbol_BC, symbol_CA, volume, price_BA, price_BC, price_CA))
        return

    def exec_forward_trade(self, symbol_BA, symbol_BC, symbol_CA, volume_BA,
                           price_BA, price_BC, price_CA):
        Slack.send_message('start FORWARD trade, detected prices:\n{}: {}\n{}: {}\n{}: {}'.format(
            symbol_BA, price_BA, symbol_BC, price_BC, symbol_CA, price_CA
        ))

        curB_amount = self.trade(symbol_BA, 'buy', volume_BA, price_BA)
        time.sleep(1)

        curC_amount = self.trade(symbol_BC, 'sell', curB_amount, price_BC)
        time.sleep(1)

        curA_amount = self.trade(symbol_CA, 'sell', curC_amount, price_CA)
        return curA_amount

    def exec_reverse_trade(self, symbol_BA, symbol_BC, symbol_CA, volume_CA,
                           price_BA, price_BC, price_CA):
        Slack.send_message('start REVERSE trade, detected prices:\n{}: {}\n{}: {}\n{}: {}'.format(
            symbol_BA, price_BA, symbol_BC, price_BC, symbol_CA, price_CA
        ))

        curC_amount = self.trade(symbol_CA, 'buy', volume_CA, price_CA)
        time.sleep(1)

        volume_BC = curC_amount / price_BC
        decrease_step = volume_BC * 0.004
        # 若價格瞬間上漲，curC_amount 可能不夠買 volume_BC，就減少 volume_BC，買到為止
        while 1:
            try:
                curB_amount = self.trade(symbol_BC, 'buy', volume_BC, price_BC)
                break
            except InsufficientFundsException:
                Slack.send_message('Insufficient funds.\nDecrease volume by {}'.format(decrease_step))
                volume_BC = volume_BC - decrease_step
        time.sleep(1)

        curA_amount = self.trade(symbol_BA, 'sell', curB_amount, price_BA)
        return curA_amount

    def trade(self, pair_symbol, side, amount, price):
        Slack.send_message('Trade start: {0}\n{1} volume: {2:.8f}'.format(pair_symbol, side, amount))
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
            raise TradeSkippedException(msg)
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
            except:
                order = exchange_adapter.fetch_orders(pair_symbol)[-1]
                if order['id'] != order_id:
                    time.sleep(0.5)
                    continue

            if 'closed' != order['status']:
                current_timestamp = time.time()
                if (current_timestamp - tmp_timestamp > 1800):
                    Slack.send_message('The trade is still uncompleted...')
                    tmp_timestamp = current_timestamp
                time.sleep(0.5)
                continue

            #print(order)
            # TODO: use adapter.fetch_trade()
            if 'buy' == side:
                try:
                    fee = order['fee']['cost']
                except Exception as e:
                    #print(e)
                    fee = order['filled'] * exchange_adapter.taker_fee_rate
                got_amount = order['filled'] - fee
            else:
                fee = order['cost'] * exchange_adapter.taker_fee_rate
                got_amount = order['cost'] - fee
            Slack.send_message('Trade complete: {0}\ngot amount: {1:.8f}'.format(pair_symbol, got_amount))
            return got_amount


class TradeSkippedException(Exception):
    pass


class InsufficientFundsException(TradeSkippedException):
    pass
