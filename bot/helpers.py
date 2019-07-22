# -*- coding: utf-8 -*-

import sys
import time


class Trader:
    def __init__(self, config):
        self.cryptocurrency = config['cryptocurrency']
        self.local_fiat = config['local_fiat']
        self.foreign_fiat = config['foreign_fiat']
        self.local_exchange_adapter = self.get_exchange_adapter(config['local_exchange'])
        self.foreign_exchange_adapter = self.get_exchange_adapter(config['foreign_exchange'])

    @staticmethod
    def get_exchange_adapter(exchange_name):
        local_exchange_adapter_module_name = 'bot.adapters.{}'.format(exchange_name)
        __import__(local_exchange_adapter_module_name)
        module = sys.modules[local_exchange_adapter_module_name]
        adapter_name = '{}Adapter'.format(exchange_name.capitalize())
        adapter = getattr(module, adapter_name)()
        return adapter

    def get_local_order_book(self, limit):
        adapter = self.local_exchange_adapter
        symbol = '{}/{}'.format(self.cryptocurrency, self.local_fiat)
        while 1:
            try:
                order_book = adapter.fetch_order_book(symbol, limit)
            except Exception as e:
                print(e)
                time.sleep(10)
            else:
                break

        #print(f"local exchagne order book: \n    {orderbook}\n")
        return order_book

    def get_foreign_order_book(self, limit):
        adapter = self.foreign_exchange_adapter
        symbol = '{}/{}'.format(self.cryptocurrency, self.foreign_fiat)
        while 1:
            try:
                order_book = adapter.client.fetch_order_book(symbol, limit=limit)
            except Exception as e:
                print(e)
                time.sleep(10)
            else:
                break

        #print(f"foreign exchagne order book: \n    {orderbook}\n")
        return order_book

    def exec_forward_trade(self, volume):
        self.buy_cryptocurrency_from_local_exchange()
        self.sell_cryptocurrency_from_foreign_exchange()
        return

    def exec_reverse_trade(self, volume):
        self.buy_cryptocurrency_from_foreign_exchange()
        self.sell_cryptocurrency_from_local_exchange()
        return

    def buy_cryptocurrency_from_local_exchange(self):
        return

    def sell_cryptocurrency_from_local_exchange(self):
        return

    def buy_cryptocurrency_from_foreign_exchange(self):
        return

    def sell_cryptocurrency_from_foreign_exchange(self):
        return


class Thinker:
    def __init__(self, config):
        self.max_local_fiat = config['max_local_fiat']
        self.bank_rate = config['bank_rate']
        self.threshold_forward = config['threshold_forward']
        self.threshold_reverse = config['threshold_reverse']

    def check_forward_opportunity(self, local_lowest_buy_price, foreign_highest_sell_price):
        # 計算順向操作匯率 (台灣換外幣)
        forward_op_rate = local_lowest_buy_price / foreign_highest_sell_price
        ratio = forward_op_rate / self.bank_rate
        print('forward operation rate: {}, ratio: {}'.format(forward_op_rate, ratio))
        # 若比值小於 1，表示可以用較銀行低的價錢用台幣換到外幣
        if ratio <= self.threshold_forward:
            return True
        else:
            return False

    def check_reverse_opportunity(self, foreign_lowest_buy_price, local_highest_sell_price):
        # 計算逆向操作匯率 (外幣換台幣)
        reverse_op_rate = local_highest_sell_price / foreign_lowest_buy_price
        ratio = reverse_op_rate / self.bank_rate
        print('reverse operation rate: {}, ratio: {}'.format(reverse_op_rate, ratio))
        # 若比值大於 1，表示可以用較銀行高的價錢用外幣換到台幣
        if ratio >= self.threshold_reverse:
            return True
        else:
            return False

    def get_valid_volume(self, local_price, local_volume, foreign_price, foreign_volume):
        max_local_fiat = self.max_local_fiat
        max_foreign_fiat = self.get_max_foreign_fiat()
        valid_local_volume = min(max_local_fiat / local_price, local_volume)
        valid_foreign_volume = min(max_foreign_fiat / foreign_price, foreign_volume)
        valid_volume = min(valid_local_volume, valid_foreign_volume)
        #print('valid buy volume: {}'.format(valid_buy_volume))
        #print('valid sell volume: {}'.format(valid_sell_volume))
        print('valid volume: {}'.format(valid_volume))
        return valid_volume

    def get_max_foreign_fiat(self):
        return self.max_local_fiat / self.bank_rate
