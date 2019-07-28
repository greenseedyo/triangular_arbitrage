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
        self.bank_rate = config['bank_rate']
        self.cryptocurrency = config['cryptocurrency']
        self.local_fiat = config['local_fiat']
        self.foreign_fiat = config['foreign_fiat']
        self.local_exchange = config['local_exchange']
        self.foreign_exchange = config['foreign_exchange']
        self.local_exchange_adapter = get_exchange_adapter(config['local_exchange'])
        self.foreign_exchange_adapter = get_exchange_adapter(config['foreign_exchange'])
        self.local_pair_symbol = '{}/{}'.format(self.cryptocurrency, self.local_fiat)
        self.foreign_pair_symbol = '{}/{}'.format(self.cryptocurrency, self.foreign_fiat)

    def get_balance_info(self):
        local_fiat_amount = self.get_local_fiat_amount()
        foreign_fiat_amount = self.get_foreign_fiat_amount()
        local_cryptocurrency_amount = self.get_local_cryptocurrency_amount()
        foreign_cryptocurrency_amount = self.get_foreign_cryptocurrency_amount()
        info = []
        info.append('[{}]'.format(time.strftime('%c')))
        info.append('{}: {}{}, {}{}'.format(self.local_exchange, local_fiat_amount, self.local_fiat, local_cryptocurrency_amount, self.cryptocurrency))
        info.append('{}: {}{}, {}{}'.format(self.foreign_exchange, foreign_fiat_amount, self.foreign_fiat, foreign_cryptocurrency_amount, self.cryptocurrency))
        sum = local_cryptocurrency_amount + foreign_cryptocurrency_amount
        info.append('cryptocurrency sum: {}{}'.format(sum, self.cryptocurrency))
        fiat_value = local_fiat_amount + foreign_fiat_amount * self.bank_rate
        info.append('fiat value: {}{}'.format(fiat_value, self.local_fiat))
        return info

    def get_local_order_book(self, limit):
        adapter = self.local_exchange_adapter
        while 1:
            try:
                order_book = adapter.fetch_order_book(self.local_pair_symbol, limit=limit)
            except Exception as e:
                # TODO: raise exception
                print(e)
                time.sleep(10)
            else:
                break
        #print(f"local exchagne order book: \n    {orderbook}\n")
        return order_book

    def get_foreign_order_book(self, limit):
        adapter = self.foreign_exchange_adapter
        while 1:
            try:
                order_book = adapter.fetch_order_book(self.foreign_pair_symbol, limit=limit)
            except Exception as e:
                # TODO: raise exception
                time.sleep(10)
            else:
                break
        #print(f"foreign exchagne order book: \n    {orderbook}\n")
        return order_book

    def get_local_fiat_amount(self):
        response = self.local_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.local_fiat]
        except (TypeError, KeyError):
            return 0

    def get_foreign_fiat_amount(self):
        response = self.foreign_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.foreign_fiat]
        except (TypeError, KeyError):
            return 0

    def get_local_cryptocurrency_amount(self):
        response = self.local_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.cryptocurrency]
        except (TypeError, KeyError):
            return 0

    def get_foreign_cryptocurrency_amount(self):
        response = self.foreign_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.cryptocurrency]
        except (TypeError, KeyError):
            return 0

    def exec_forward_trade(self, take_volume):
        local_got_volume = self.buy_cryptocurrency_from_local_exchange(take_volume)
        foreign_sold_amount = self.sell_cryptocurrency_from_foreign_exchange(local_got_volume)
        return foreign_sold_amount

    def exec_reverse_trade(self, take_volume):
        foreign_got_volume = self.buy_cryptocurrency_from_foreign_exchange(take_volume)
        local_sold_amount = self.sell_cryptocurrency_from_local_exchange(foreign_got_volume)
        return local_sold_amount

    def buy_cryptocurrency_from_local_exchange(self, take_volume):
        return self.trade_cryptocurrency('local', 'buy', take_volume)

    def sell_cryptocurrency_from_local_exchange(self, take_volume):
        return self.trade_cryptocurrency('local', 'sell', take_volume)

    def buy_cryptocurrency_from_foreign_exchange(self, take_volume):
        return self.trade_cryptocurrency('foreign', 'buy', take_volume)

    def sell_cryptocurrency_from_foreign_exchange(self, take_volume):
        return self.trade_cryptocurrency('foreign', 'sell', take_volume)

    def trade_cryptocurrency(self, exchange_type, side, amount):
        exchange_adapter = None
        pair_symbol = None
        if 'local' == exchange_type:
            exchange_adapter = self.local_exchange_adapter
            pair_symbol = self.local_pair_symbol
        elif 'foreign' == exchange_type:
            exchange_adapter = self.foreign_exchange_adapter
            pair_symbol = self.foreign_pair_symbol

        #print('{} {}: {} {}'.format(exchange_type, pair_symbol, side, amount))

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
            response = exchange_adapter.fetch_order(order_id, pair_symbol)
            if 'open' == response['status']:
                time.sleep(0.5)
                continue

            #print(response)
            fee = 0
            if 'buy' == side:
                try:
                    fee = response['fee']['cost']
                except Exception as e:
                    print(e)
                    fee = response['filled'] * exchange_adapter.taker_fee_rate

            traded_amount = response['filled'] - fee
            return traded_amount

    def fetch_local_orders(self):
        return self.local_exchange_adapter.fetch_orders(self.local_pair_symbol)

    def fetch_foreign_orders(self):
        return self.foreign_exchange_adapter.fetch_orders(self.foreign_pair_symbol)


class Thinker:
    def __init__(self, config):
        self.max_local_fiat_trade_amount = config['max_local_fiat_trade_amount']
        self.min_cryptocurrency_trade_amount = config['min_cryptocurrency_trade_amount']
        self.bank_rate = config['bank_rate']
        self.local_exchange_adapter = get_exchange_adapter(config['local_exchange'])
        self.foreign_exchange_adapter = get_exchange_adapter(config['foreign_exchange'])
        self.threshold_forward = config['threshold_forward']
        self.threshold_reverse = config['threshold_reverse']

    def check_forward_opportunity(self, local_lowest_ask_price, foreign_highest_bid_price):
        ratio = self.get_op_ratio(local_lowest_ask_price, foreign_highest_bid_price)
        print('forward ratio: {}'.format(ratio))
        # 若比值小於 1，表示可以用較銀行低的價錢用台幣換到外幣
        if ratio <= self.threshold_forward:
            return True
        else:
            return False

    def check_reverse_opportunity(self, foreign_lowest_ask_price, local_highest_bid_price):
        ratio = self.get_op_ratio(local_highest_bid_price, foreign_lowest_ask_price)
        print('reverse ratio: {}'.format(ratio))
        # 若比值大於 1，表示可以用較銀行高的價錢用外幣換到台幣
        if ratio >= self.threshold_reverse:
            return True
        else:
            return False

    def get_op_ratio(self, local_price, foreign_price):
        # 計算操作匯率 (台灣/外幣)
        op_rate = local_price / foreign_price
        ratio = op_rate / self.bank_rate
        return ratio

    def get_valid_forward_volume(self, buy_side_fiat_amount, buy_side_lowest_ask_price, buy_side_lowest_ask_volume,
                                 sell_side_cryptocurrency_amount, sell_side_highest_bid_volume):
        return self.get_valid_volume('forward', buy_side_fiat_amount, buy_side_lowest_ask_price, buy_side_lowest_ask_volume,
                                     sell_side_cryptocurrency_amount, sell_side_highest_bid_volume)

    def get_valid_reverse_volume(self, buy_side_fiat_amount, buy_side_lowest_ask_price, buy_side_lowest_ask_volume,
                                 sell_side_cryptocurrency_amount, sell_side_highest_bid_volume):
        return self.get_valid_volume('reverse', buy_side_fiat_amount, buy_side_lowest_ask_price, buy_side_lowest_ask_volume,
                                     sell_side_cryptocurrency_amount, sell_side_highest_bid_volume)

    def get_valid_volume(self, direction, buy_side_fiat_amount, buy_side_lowest_ask_price, buy_side_lowest_ask_volume,
                         sell_side_cryptocurrency_amount, sell_side_highest_bid_volume):
        # max_buy_side_fiat_trade_amount: 買進最大金額上限 (config 設定)
        # min_order_volume: 買進最小成交量。需先把手續費加上去，避免賣出時的吃單量低於最小成交量限制
        # 例：max 交易所的 ETH 最低交易量為 0.05，binance 手續費為 0.1%
        # 若在 binance 買進 0.05，實際上只買到 0.04995，未達 max 的最低交易量)
        if 'forward' == direction:
            max_buy_side_fiat_trade_amount = self.max_local_fiat_trade_amount
            min_order_volume = self.min_cryptocurrency_trade_amount / (1 - self.local_exchange_adapter.taker_fee_rate)
        elif 'reverse' == direction:
            max_buy_side_fiat_trade_amount = self.get_max_foreign_fiat_trade_amount()
            min_order_volume = self.min_cryptocurrency_trade_amount / (1 - self.foreign_exchange_adapter.taker_fee_rate)
        else:
            raise ValueError('direction must be forward or reverse')

        # 買進金額
        valid_buy_side_fiat_amount = min(max_buy_side_fiat_trade_amount, buy_side_fiat_amount)
        # 買進金額換算可買的加密貨幣量
        buy_side_fiat_ability_volume = valid_buy_side_fiat_amount / buy_side_lowest_ask_price
        # 掛單上的量
        buy_side_valid_volume = min(buy_side_fiat_ability_volume, buy_side_lowest_ask_volume)
        # 實際可吃單的量
        valid_take_volume = min(buy_side_valid_volume, sell_side_cryptocurrency_amount, sell_side_highest_bid_volume)
        # 取到小數點第 6 位
        rounded_valid_take_volume = round(valid_take_volume, 6)

        # 實際要交易的量
        if rounded_valid_take_volume < min_order_volume:
            # 未達最小交易量設定
            return 0
        else:
            return rounded_valid_take_volume

    def get_max_foreign_fiat_trade_amount(self):
        return self.max_local_fiat_trade_amount / self.bank_rate


class TradeSkippedException(Exception):
    pass
