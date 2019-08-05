# -*- coding: utf-8 -*-

import sys
import time
import ccxt


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

    def get_balance_info(self, symbols):
        info = []
        info.append('[{}]'.format(time.strftime('%c')))
        info.append('exchange: {}'.format(self.exchange))
        for symbol in symbols:
            amount = self.get_currency_amount(symbol)
            info.append('{}: {}'.format(symbol, amount))
        return info

    def get_order_book(self, pair_symbol, limit):
        adapter = self.exchange_adapter
        while 1:
            try:
                order_book = adapter.fetch_order_book(pair_symbol, limit=limit)
            except Exception as e:
                # TODO: raise exception
                print(e)
                time.sleep(10)
            else:
                break
        print(order_book)
        return order_book

    def get_currency_amount(self, symbol):
        response = self.exchange_adapter.fetch_balance()
        try:
            return response['free'][symbol]
        except (TypeError, KeyError):
            return 0

    def exec_test_trade(self, symbol_BA, symbol_BC, symbol_CA, volume, price_BC=None):
        print('test trade {}-{}-{}, volume: {}'.format(symbol_BA, symbol_BC, symbol_CA, volume))
        return

    def exec_forward_trade(self, symbol_BA, symbol_BC, symbol_CA, volume_BA, price_BC=None):
        curB_amount = self.trade(symbol_BA, 'buy', volume_BA)
        curC_amount = self.trade(symbol_BC, 'sell', curB_amount)
        curA_amount = self.trade(symbol_CA, 'sell', curC_amount)
        return curA_amount

    def exec_reverse_trade(self, symbol_BA, symbol_BC, symbol_CA, volume_CA, price_BC):
        curC_amount = self.trade(symbol_CA, 'buy', volume_CA)
        volume_BC = curC_amount / price_BC
        curB_amount = self.trade(symbol_BC, 'buy', volume_BC)
        curA_amount = self.trade(symbol_BA, 'sell', curB_amount)
        return curA_amount

    def trade(self, pair_symbol, side, amount):
        exchange_adapter = self.exchange_adapter
        response = {}
        try:
            if 'buy' == side:
                response = exchange_adapter.create_market_buy_order(pair_symbol, amount)
            elif 'sell' == side:
                response = exchange_adapter.create_market_sell_order(pair_symbol, amount)
        except ccxt.InvalidOrder as e:
            msg = 'TRADE SKIPPED - invalid order: {}'.format(str(e))
            raise TradeSkippedException(msg)
        except ccxt.InsufficientFunds:
            msg = 'TRADE SKIPPED - insufficient balance'
            raise TradeSkippedException(msg)
        except Exception as e:
            raise TradeSkippedException('unknown error taker_fee: {}'. format(str(e)))

        order_id = response['id']
        while 1:
            try:
                order = exchange_adapter.fetch_order(order_id, pair_symbol)
            except:
                order = exchange_adapter.fetch_orders(pair_symbol)[-1]
                if order['id'] != order_id:
                    time.sleep(0.5)
                    continue

            if 'closed' != order['status']:
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
                fee = order['filled'] * exchange_adapter.taker_fee_rate
                got_amount = order['cost'] - fee
            return got_amount


class TradeSkippedException(Exception):
    pass
