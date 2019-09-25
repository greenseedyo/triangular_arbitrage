# -*- coding: utf-8 -*-

import sys
import time
import ccxt
import twder
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
        self.real_rate_handler = config['real_rate_handler']
        self.bridge_currency = config['bridge_currency']
        self.first_currency = config['first_currency']
        self.second_currency = config['second_currency']
        self.primary_exchange = config['primary_exchange']
        self.secondary_exchange = config['secondary_exchange']
        self.primary_exchange_adapter = get_exchange_adapter(config['primary_exchange'])
        self.secondary_exchange_adapter = get_exchange_adapter(config['secondary_exchange'])
        self.primary_pair_symbol = '{}/{}'.format(self.bridge_currency, self.first_currency)
        self.secondary_pair_symbol = '{}/{}'.format(self.bridge_currency, self.second_currency)
        self.real_rate = None
        self.real_pair_symbol = '{}/{}'.format(self.second_currency, self.first_currency)

    def get_real_rate_handler(self, handler_name):
        handler = getattr(self, handler_name)
        return handler

    def get_real_rate(self, direction=None):
        handler = self.get_real_rate_handler(self.real_rate_handler)
        while 1:
            try:
                real_rate = handler(direction)
            except Exception as e:
                print(e)
                time.sleep(10)
            else:
                break
        print('real rate: {}'.format(real_rate))
        real_rate = float(real_rate)
        self.real_rate = real_rate
        return real_rate

    def get_usdtwd_by_twder(self, direction):
        real_rate = float(twder.now('USD')[4])
        return real_rate

    def get_real_rate_in_primary_exchange(self, direction):
        ticker = self.primary_exchange_adapter.fetch_ticker(self.real_pair_symbol)
        #print(ticker)
        if 'forward' == direction:
            real_rate = ticker['bid']
        elif 'reverse' == direction:
            real_rate = ticker['ask']
        else:
            real_rate = ticker['last']
        return float(real_rate)

    def get_balance_info(self):
        real_rate = self.get_real_rate()
        first_currency_amount = self.get_first_currency_amount()
        second_currency_amount = self.get_second_currency_amount()
        primary_bridge_currency_amount = self.get_bridge_currency_amount_in_primary_exchange()
        secondary_bridge_currency_amount = self.get_bridge_currency_amount_in_secondary_exchange()
        info = []
        info.append('[{}]'.format(time.strftime('%c')))
        info.append('{}: {}{}, {}{}'.format(self.primary_exchange, first_currency_amount, self.first_currency, primary_bridge_currency_amount, self.bridge_currency))
        info.append('{}: {}{}, {}{}'.format(self.secondary_exchange, second_currency_amount, self.second_currency, secondary_bridge_currency_amount, self.bridge_currency))
        sum = primary_bridge_currency_amount + secondary_bridge_currency_amount
        info.append('bridge_currency sum: {}{}'.format(sum, self.bridge_currency))
        currency_value = first_currency_amount + second_currency_amount * real_rate
        info.append('currency value: {}{}'.format(currency_value, self.first_currency))
        return info

    def get_primary_order_book(self, limit):
        adapter = self.primary_exchange_adapter
        while 1:
            try:
                order_book = adapter.fetch_order_book(self.primary_pair_symbol, limit=limit)
            except Exception as e:
                # TODO: raise exception
                print(e)
                time.sleep(10)
            else:
                break
        #print(f"primary exchagne order book: \n    {orderbook}\n")
        return order_book

    def get_secondary_order_book(self, limit):
        adapter = self.secondary_exchange_adapter
        while 1:
            try:
                order_book = adapter.fetch_order_book(self.secondary_pair_symbol, limit=limit)
            except Exception as e:
                # TODO: raise exception
                print(e)
                time.sleep(10)
            else:
                break
        #print(f"secondary exchagne order book: \n    {orderbook}\n")
        return order_book

    def get_first_currency_amount(self):
        response = self.primary_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.first_currency]
        except (TypeError, KeyError):
            return 0

    def get_second_currency_amount(self):
        response = self.secondary_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.second_currency]
        except (TypeError, KeyError):
            return 0

    def get_bridge_currency_amount_in_primary_exchange(self):
        response = self.primary_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.bridge_currency]
        except (TypeError, KeyError):
            return 0

    def get_bridge_currency_amount_in_secondary_exchange(self):
        response = self.secondary_exchange_adapter.fetch_balance()
        try:
            return response['free'][self.bridge_currency]
        except (TypeError, KeyError):
            return 0

    def get_equivalent_bridge_currency_bid_amount_by_second_currency(self):
        real_pair_order_book = self.secondary_exchange_adapter.fetch_order_book(self.real_pair_symbol)
        secondary_pair_order_book = self.secondary_exchange_adapter.fetch_order_book(self.secondary_pair_symbol)
        # second currency / first currency 的 bid 掛單量
        volume = float(real_pair_order_book['bids'][0][1])
        # bridge currency / second currency 的 bid 價格
        rate = float(secondary_pair_order_book['bids'][0][0])
        equivalent_bridge_currency_amount = volume / rate
        needed_bridge_currency_amount = equivalent_bridge_currency_amount / (1 - self.secondary_exchange_adapter.taker_fee_rate)
        return needed_bridge_currency_amount

    def exec_test_trade(self, take_volume):
        print('test trade volume: {}'.format(take_volume))
        return

    def exec_forward_trade(self, take_volume):
        primary_got_volume = self.buy_bridge_currency_from_primary_exchange(take_volume)
        secondary_sold_amount = self.sell_bridge_currency_from_secondary_exchange(primary_got_volume)
        return secondary_sold_amount

    def exec_reverse_trade(self, take_volume):
        secondary_got_volume = self.buy_bridge_currency_from_secondary_exchange(take_volume)
        primary_sold_amount = self.sell_bridge_currency_from_primary_exchange(secondary_got_volume)
        return primary_sold_amount

    def buy_bridge_currency_from_primary_exchange(self, take_volume):
        return self.trade_bridge_currency('primary', 'buy', take_volume)

    def sell_bridge_currency_from_primary_exchange(self, take_volume):
        return self.trade_bridge_currency('primary', 'sell', take_volume)

    def buy_bridge_currency_from_secondary_exchange(self, take_volume):
        return self.trade_bridge_currency('secondary', 'buy', take_volume)

    def sell_bridge_currency_from_secondary_exchange(self, take_volume):
        return self.trade_bridge_currency('secondary', 'sell', take_volume)

    def trade_bridge_currency(self, exchange_type, side, amount):
        exchange_adapter = None
        pair_symbol = None
        if 'primary' == exchange_type:
            exchange_adapter = self.primary_exchange_adapter
            pair_symbol = self.primary_pair_symbol
        elif 'secondary' == exchange_type:
            exchange_adapter = self.secondary_exchange_adapter
            pair_symbol = self.secondary_pair_symbol

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
            try:
                order = exchange_adapter.fetch_order(order_id, pair_symbol)
            except:
                order = exchange_adapter.fetch_orders(pair_symbol)[-1]
                if order['id'] != order_id:
                    time.sleep(0.5)
                    continue

            if 'open' == order['status']:
                time.sleep(0.5)
                continue

            #print(response)
            fee = 0
            if 'buy' == side:
                try:
                    fee = order['fee']['cost']
                except Exception as e:
                    #print(e)
                    fee = order['filled'] * exchange_adapter.taker_fee_rate

            traded_amount = order['filled'] - fee
            return traded_amount

    def fetch_primary_orders(self):
        return self.primary_exchange_adapter.fetch_orders(self.primary_pair_symbol)

    def fetch_secondary_orders(self):
        return self.secondary_exchange_adapter.fetch_orders(self.secondary_pair_symbol)


class Thinker:
    def __init__(self, config):
        self.max_first_currency_trade_amount = config['max_first_currency_trade_amount']
        self.min_first_currency_trade_amount = config['min_first_currency_trade_amount']
        self.min_secondary_currency_trade_amount = config['min_secondary_currency_trade_amount']
        self.min_bridge_currency_trade_amount = config['min_bridge_currency_trade_amount']
        self.real_rate = config['real_rate']
        self.primary_exchange = config['primary_exchange']
        self.secondary_exchange = config['secondary_exchange']
        self.primary_exchange_adapter = get_exchange_adapter(config['primary_exchange'])
        self.secondary_exchange_adapter = get_exchange_adapter(config['secondary_exchange'])
        self.threshold_forward = config['threshold_forward']
        self.threshold_reverse = config['threshold_reverse']

    def check_forward_opportunity(self, primary_lowest_ask_price, secondary_highest_bid_price):
        ratio = self.get_op_ratio(primary_lowest_ask_price, secondary_highest_bid_price)
        print('forward ratio: {}'.format(ratio))
        # 若比值小於 1，表示可以用較銀行低的價錢用台幣換到外幣
        if ratio <= self.threshold_forward:
            return True
        else:
            return False

    def check_reverse_opportunity(self, secondary_lowest_ask_price, primary_highest_bid_price):
        ratio = self.get_op_ratio(primary_highest_bid_price, secondary_lowest_ask_price)
        print('reverse ratio: {}'.format(ratio))
        # 若比值大於 1，表示可以用較銀行高的價錢用外幣換到台幣
        if ratio >= self.threshold_reverse:
            return True
        else:
            return False

    def get_op_ratio(self, primary_price, secondary_price):
        # 計算操作匯率 (台灣/外幣)
        op_rate = primary_price / secondary_price
        ratio = op_rate / self.real_rate
        return ratio

    def get_valid_volume(self, direction, buy_side_currency_amount, buy_side_lowest_ask_price, buy_side_lowest_ask_volume,
                         sell_side_currency_amount, sell_side_highest_bid_price, sell_side_highest_bid_volume):
        print('input: ', locals())
        # max_buy_side_currency_trade_amount: 買進最大金額上限 (config 設定)
        # min_order_volume: 買進最小成交量。需先把手續費加上去，避免賣出時的吃單量低於最小成交量限制
        # 例：MAX 交易所的 ETH 最低交易量為 0.05，binance 手續費為 0.1%
        # 若在 Binance 買進 0.05，實際上只買到 0.04995，未達 MAX 的最低交易量)
        if 'forward' == direction:
            max_buy_side_currency_trade_amount = self.max_first_currency_trade_amount
            min_order_volume = self.min_bridge_currency_trade_amount / (1 - self.primary_exchange_adapter.taker_fee_rate)
            min_buy_side_trade_amount = self.min_first_currency_trade_amount
            min_sell_side_trade_amount = self.min_secondary_currency_trade_amount
        elif 'reverse' == direction:
            max_buy_side_currency_trade_amount = self.get_max_second_currency_trade_amount()
            min_order_volume = self.min_bridge_currency_trade_amount / (1 - self.secondary_exchange_adapter.taker_fee_rate)
            min_buy_side_trade_amount = self.min_secondary_currency_trade_amount
            min_sell_side_trade_amount = self.min_first_currency_trade_amount
        else:
            raise ValueError('direction must be forward or reverse')

        # 買進金額
        valid_buy_side_currency_amount = min(max_buy_side_currency_trade_amount, buy_side_currency_amount)
        # 買進金額換算可買的貨幣量
        buy_side_currency_ability_volume = valid_buy_side_currency_amount / buy_side_lowest_ask_price
        # 掛單上的量
        buy_side_valid_volume = min(buy_side_currency_ability_volume, buy_side_lowest_ask_volume)
        # 實際可吃單的量
        valid_take_volume = min(buy_side_valid_volume, sell_side_highest_bid_volume, sell_side_currency_amount)
        # 取到小數點第 6 位
        rounded_valid_take_volume = round(valid_take_volume, 6)

        # 實際買進成本
        buy_side_cost = rounded_valid_take_volume * buy_side_lowest_ask_price
        # 實際賣出收款
        sell_side_income = rounded_valid_take_volume * sell_side_highest_bid_price

        msgs = []
        msgs.append('max_buy_side_currency_trade_amount: {}'.format(max_buy_side_currency_trade_amount))
        msgs.append('min_order_volume: {}'.format(min_order_volume))
        msgs.append('min_buy_side_trade_amount: {}'.format(min_buy_side_trade_amount))
        msgs.append('min_sell_side_trade_amount: {}'.format(min_sell_side_trade_amount))
        msgs.append('valid_buy_side_currency_amount: {}'.format(valid_buy_side_currency_amount))
        msgs.append('buy_side_currency_ability_volume: {}'.format(buy_side_currency_ability_volume))
        msgs.append('buy_side_valid_volume: {}'.format(buy_side_valid_volume))
        msgs.append('valid_take_volume: {}'.format(valid_take_volume))
        msgs.append('rounded_valid_take_volume: {}'.format(rounded_valid_take_volume))
        msgs.append('buy_side_cost: {}'.format(buy_side_cost))
        msgs.append('sell_side_income: {}'.format(sell_side_income))
        msg = "\n".join(msgs)
        print(msg)
        #utils.log_to_slack(msg)

        # 實際要交易的量
        if rounded_valid_take_volume < min_order_volume:
            return 0
        elif buy_side_cost < min_buy_side_trade_amount:
            return 0
        elif sell_side_income < min_sell_side_trade_amount:
            return 0
        else:
            return rounded_valid_take_volume

    def get_max_second_currency_trade_amount(self):
        return self.max_first_currency_trade_amount / self.real_rate


class TradeSkippedException(Exception):
    pass
