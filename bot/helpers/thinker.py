# -*- coding: utf-8 -*-

import sys
import math


def get_exchange_adapter(exchange_name):
    exchange_adapter_module_name = 'bot.adapters.{}'.format(exchange_name)
    __import__(exchange_adapter_module_name)
    module = sys.modules[exchange_adapter_module_name]
    adapter_name = '{}Adapter'.format(exchange_name.capitalize())
    adapter = getattr(module, adapter_name)()
    return adapter


class Thinker:
    def __init__(self, config):
        self.exchange = config['exchange']
        self.exchange_adapter = get_exchange_adapter(config['exchange'])
        self.threshold_forward = config['threshold_forward']
        self.threshold_reverse = config['threshold_reverse']

    def check_forward_opportunity(self, ask_price_BA, bid_price_BC, bid_price_CA):
        ratio = self.get_op_ratio(ask_price_BA, bid_price_BC, bid_price_CA)
        #print('forward ratio: {}'.format(ratio))
        # 若比值小於 1，表示可以用較低的價格用 curA 透過 curB 換到 curC
        if ratio <= self.threshold_forward:
            return True
        else:
            return False

    def check_reverse_opportunity(self, bid_price_BA, ask_price_BC, ask_price_CA):
        ratio = self.get_op_ratio(bid_price_BA, ask_price_BC, ask_price_CA)
        #print('reverse ratio: {}'.format(ratio))
        # 若比值大於 1，表示可以用較高的價格用 curC 透過 curB 換到 curA
        if ratio >= self.threshold_reverse:
            return True
        else:
            return False

    def get_op_ratio(self, primary_price, secondary_price, real_price):
        # 計算操作匯率
        op_rate = primary_price / secondary_price
        # 計算比值
        ratio = op_rate / real_price
        return ratio

    def get_valid_forward_volume(self, max_curA_amount, min_curA_trade_volume_limit, min_curB_trade_volume_limit,
                                 min_curC_trade_volume_limit, curA_amount, price_BA, ask_volume_BA,
                                 bid_price_BC, bid_volume_BC, bid_volume_CA):
        # max_buy_side_currency_trade_amount: 買進最大金額上限 (config 設定)
        # min_order_volume: 買進最小成交量。需先把手續費加上去，避免賣出時的吃單量低於最小成交量限制
        # 例：MAX 交易所的 ETH 最低交易量為 0.05，手續費為 0.15%
        # 若買進 0.05，實際上只買到 0.049925，未達最低交易量，就沒辦法再賣出)
        min_curB_trade_volume = min_curB_trade_volume_limit / (1 - self.exchange_adapter.taker_fee_rate)

        # curA 可用金額
        valid_curA_amount = min(max_curA_amount, curA_amount)
        # curA 可用金額換算可買的 curB
        curB_possible_volume = valid_curA_amount / price_BA
        # 最多就是 B/A 掛單上的量
        valid_volume_BA = min(curB_possible_volume, ask_volume_BA)
        # 扣手續費後可拿到的 curB
        real_valid_volume_curB = valid_volume_BA * (1 - self.exchange_adapter.taker_fee_rate)

        # 拿到的 curB 可以換到多少 curC
        possible_curC_volume = real_valid_volume_curB * bid_price_BC
        # B/C 可吃單的量
        valid_BC_volume = min(possible_curC_volume, bid_volume_BC)
        # 實際上可以拿到的 curC
        real_valid_curC_amount = (valid_BC_volume * bid_price_BC) * (1 - self.exchange_adapter.taker_fee_rate)

        # 可以吃下 C/A 的量
        valid_CA_volume = min(bid_volume_CA, real_valid_curC_amount)
        # 要吃掉 C/A 的量需要多少 curC 才夠
        needed_curC_amount = valid_CA_volume / (1 - self.exchange_adapter.taker_fee_rate)
        # 換算需要買多少 curB 才夠
        needed_curB_amount = (needed_curC_amount / bid_price_BC) / (1 - self.exchange_adapter.taker_fee_rate)
        # 換算需要多少 curA 才夠
        needed_curA_amount = (valid_volume_BA * price_BA) / (1 - self.exchange_adapter.taker_fee_rate)

        # 取到小數點第 8 位
        floored_needed_curA_amount = self.get_floored_amount(needed_curA_amount)
        floored_needed_curB_amount = self.get_floored_amount(needed_curB_amount)
        floored_needed_curC_amount = self.get_floored_amount(needed_curC_amount)

        print('valid_curA_amount', valid_curA_amount)
        print('curB_possible_volume', curB_possible_volume)
        print('valid_volume_BA', valid_volume_BA)
        print('real_valid_volume_curB', real_valid_volume_curB)
        print('possible_curC_volume', possible_curC_volume)
        print('valid_BC_volume', valid_BC_volume)
        print('valid_CA_volume', valid_CA_volume)
        print('needed_curC_amount', needed_curC_amount)
        print('needed_curB_amount', needed_curB_amount)
        print('needed_curA_amount', needed_curA_amount)

        # 是否達最小交易量
        if floored_needed_curA_amount < min_curA_trade_volume_limit:
            return 0
        elif floored_needed_curB_amount < min_curB_trade_volume_limit:
            return 0
        elif floored_needed_curC_amount < min_curC_trade_volume_limit:
            return 0
        else:
            return floored_needed_curB_amount

    @staticmethod
    def get_floored_amount(amount):
        return math.floor(amount * 100000000) / 100000000

    def get_valid_reverse_volume(self, max_curA_amount, min_curA_trade_volume_limit, min_curB_trade_volume_limit,
                                 min_curC_trade_volume_limit, curA_amount, price_CA, ask_volume_CA,
                                 ask_price_BC, ask_volume_BC, bid_volume_BA):
        # max_buy_side_currency_trade_amount: 買進最大金額上限 (config 設定)
        # min_order_volume: 買進最小成交量。需先把手續費加上去，避免賣出時的吃單量低於最小成交量限制
        # 例：MAX 交易所的 ETH 最低交易量為 0.05，手續費為 0.15%
        # 若買進 0.05，實際上只買到 0.049925，未達最低交易量，就沒辦法再賣出)
        min_curC_trade_volume = min_curC_trade_volume_limit / (1 - self.exchange_adapter.taker_fee_rate)

        # curA 可用金額
        valid_curA_amount = min(max_curA_amount, curA_amount)
        # curA 可用金額換算可買到的 curC
        possible_curC_volume = valid_curA_amount / price_CA
        # 最多就是 C/A 掛單上的量
        valid_volume_CA = min(possible_curC_volume, ask_volume_CA)
        # 實際上可拿到的 curC
        real_valid_volume_curC = valid_volume_CA * (1 - self.exchange_adapter.taker_fee_rate)

        # 拿到的 curC 可以換到多少 curB
        possible_curB_volume = real_valid_volume_curC / ask_price_BC
        # B/C 可吃單的量
        valid_BC_volume = min(possible_curB_volume, ask_volume_BC)
        # 實際上可以拿到的 curB
        real_valid_curB_amount = valid_BC_volume * (1 - self.exchange_adapter.taker_fee_rate)

        # 可以吃下 B/A 的量
        valid_BA_volume = min(bid_volume_BA, real_valid_curB_amount)
        # 要吃掉 B/A 的量需要多少 curB 才夠
        needed_curB_amount = valid_BA_volume / (1 - self.exchange_adapter.taker_fee_rate)
        # 換算需要買多少 curC 才夠
        needed_curC_amount = (needed_curB_amount * ask_price_BC) / (1 - self.exchange_adapter.taker_fee_rate)
        # 換算需要多少 curA 才夠
        needed_curA_amount = (valid_volume_CA * price_CA) / (1 - self.exchange_adapter.taker_fee_rate)


        # 取到小數點第 8 位
        floored_needed_curA_amount = self.get_floored_amount(needed_curA_amount)
        floored_needed_curB_amount = self.get_floored_amount(needed_curB_amount)
        floored_needed_curC_amount = self.get_floored_amount(needed_curC_amount)

        print('valid_curA_amount', valid_curA_amount)
        print('possible_curC_volume', possible_curC_volume)
        print('real_valid_volume_curC', real_valid_volume_curC)
        print('possible_curB_volume', possible_curB_volume)
        print('valid_BC_volume', valid_BC_volume)
        print('real_valid_curB_amount', real_valid_curB_amount)
        print('valid_BA_volume', valid_BA_volume)
        print('needed_curB_amount', needed_curB_amount)
        print('needed_curC_amount', needed_curC_amount)
        print('needed_curA_amount', needed_curA_amount)

        # 是否達最小交易量
        if floored_needed_curA_amount < min_curA_trade_volume_limit:
            return 0
        elif floored_needed_curB_amount < min_curB_trade_volume_limit:
            return 0
        elif floored_needed_curC_amount < min_curC_trade_volume_limit:
            return 0
        else:
            return floored_needed_curC_amount
