# -*- coding: utf-8 -*-

import sys
import bot.helpers.utils as utils


class Thinker:
    exchange = None
    exchange_adapter = None
    threshold_forward = None
    threshold_reverse = None

    def __init__(self, exchange):
        self.exchange = exchange
        self.exchange_adapter = utils.get_exchange_adapter(exchange)
        threshold_forward = self.get_default_threshold('forward')
        threshold_reverse = self.get_default_threshold('reverse')
        self.set_thresholds(threshold_forward, threshold_reverse)

    def set_thresholds(self, threshold_forward, threshold_reverse):
        self.threshold_forward = threshold_forward
        self.threshold_reverse = threshold_reverse

    def get_fee_rate(self, side):
        # side: taker/maker
        return self.exchange_adapter.fees['trading'][side]

    def get_default_threshold(self, direction):
        taker_fee_rate = self.get_fee_rate('taker')
        # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
        if 'forward' == direction:
            return 1 - (taker_fee_rate * 3 + 0.0005)  # 順向
        if 'reverse' == direction:
            return 1 + (taker_fee_rate * 3 + 0.0005)  # 逆向

    def get_all_valid_combinations(self):
        markets = self.exchange_adapter.fetch_markets()
        # 應該有更好的做法
        def find_valid_curB(curA, curC):
            candidates = {}
            valid_ones = {}
            for m in markets:
                candidate = m['base']
                if candidate == curA or candidate == curC or (candidate in valid_ones):
                    continue
                if m['quote'] == curA or m['quote'] == curC:
                    if candidate in candidates:  # 若已存在表示兩者皆有
                        valid_ones[candidate] = True
                    else:
                        candidates[candidate] = True
            return valid_ones
    
        combinations = {}
        for market in markets:
            if market['active'] == False:
                continue
            curA = market['quote']
            curC = market['base']
            valid_curB = find_valid_curB(curA, curC)
            for curB in valid_curB:
                key = '{}-{}-{}'.format(curA, curB, curC)
                combinations[key] = [curA, curB, curC]
        return combinations

    @staticmethod
    def get_market_symbols_of_combinations(combinations):
        symbols = {}
        for key in combinations:
            combination = combinations[key]
            curA, curB, curC = combination
            symbol_BA = '{}/{}'.format(curB, curA)
            symbol_BC = '{}/{}'.format(curB, curC)
            symbol_CA = '{}/{}'.format(curC, curA)
            symbols[symbol_BA] = True
            symbols[symbol_BC] = True
            symbols[symbol_CA] = True
        return symbols.keys()

    def get_target_combinations(self, curA_targets):
        valid_combinations = self.get_all_valid_combinations()
        target_combinations = {}
        for curA_target in curA_targets:
            for key in valid_combinations:
                combination = valid_combinations[key]
                curA, curB, curC = combination
                if curA != curA_target:
                    continue
                target_combinations[key] = combination
        return target_combinations

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

    def get_valid_forward_volume(self, max_curA_amount, limits_BA, limits_BC, limits_CA,
                                 curA_amount, ask_price_BA, ask_volume_BA,
                                 bid_price_BC, bid_volume_BC, bid_price_CA, bid_volume_CA):
        taker_fee_rate = self.get_fee_rate('taker')
        print('input: ', locals())
        # curA 可用金額
        valid_curA_amount = min(max_curA_amount, curA_amount)
        # curA 可用金額換算可買的 curB
        curB_possible_volume = valid_curA_amount / ask_price_BA
        # 最多就是 B/A 掛單上的量
        valid_BA_volume = min(curB_possible_volume, ask_volume_BA)
        # 扣手續費後可拿到的 curB
        real_valid_volume_curB = valid_BA_volume * (1 - taker_fee_rate)

        # B/C 可吃單的量
        valid_BC_volume = min(real_valid_volume_curB, bid_volume_BC)
        # 實際上可以拿到的 curC
        real_valid_curC_amount = (valid_BC_volume * bid_price_BC) * (1 - taker_fee_rate)

        # 可以吃下 C/A 的量
        valid_CA_volume = min(bid_volume_CA, real_valid_curC_amount)
        # 要吃掉 C/A 的量需要多少 curC 才夠
        needed_curC_amount = valid_CA_volume / (1 - taker_fee_rate)
        # 換算需要買多少 curB 才夠
        needed_curB_amount = (needed_curC_amount / bid_price_BC) / (1 - taker_fee_rate)
        # 換算需要多少 curA 才夠
        needed_curA_amount = (needed_curB_amount * ask_price_BA) / (1 - taker_fee_rate)

        # 取到小數點第 8 位
        floored_needed_curA_amount = utils.get_floored_amount(needed_curA_amount)
        floored_needed_curB_amount = utils.get_floored_amount(needed_curB_amount)
        floored_needed_curC_amount = utils.get_floored_amount(needed_curC_amount)

        print('valid_curA_amount', valid_curA_amount)
        print('curB_possible_volume', curB_possible_volume)
        print('valid_BA_volume', valid_BA_volume)
        print('real_valid_volume_curB', real_valid_volume_curB)
        print('valid_BC_volume', valid_BC_volume)
        print('real_valid_curC_amount', real_valid_curC_amount)
        print('valid_CA_volume', valid_CA_volume)
        print('needed_curC_amount', needed_curC_amount)
        print('needed_curB_amount', needed_curB_amount)
        print('needed_curA_amount', needed_curA_amount)

        # 是否達最小交易量
        if floored_needed_curA_amount < limits_BA['cost']['min']:
            return 0
        elif floored_needed_curA_amount / ask_price_BA < limits_BA['amount']['min']:
            return 0
        elif floored_needed_curB_amount < limits_BC['amount']['min']:
            return 0
        elif floored_needed_curB_amount * bid_price_BC < limits_BC['cost']['min']:
            return 0
        elif floored_needed_curC_amount < limits_CA['amount']['min']:
            return 0
        elif floored_needed_curC_amount * bid_price_CA < limits_CA['cost']['min']:
            return 0
        else:
            return floored_needed_curB_amount

    def get_valid_reverse_volume(self, max_curA_amount, limits_BA, limits_BC, limits_CA,
                                 curA_amount, ask_price_CA, ask_volume_CA,
                                 ask_price_BC, ask_volume_BC, bid_price_BA, bid_volume_BA):
        taker_fee_rate = self.get_fee_rate('taker')
        print('input: ', locals())
        # curA 可用金額
        valid_curA_amount = min(max_curA_amount, curA_amount)
        # curA 可用金額換算可買到的 curC
        possible_curC_volume = valid_curA_amount / ask_price_CA
        # 最多就是 C/A 掛單上的量
        valid_volume_CA = min(possible_curC_volume, ask_volume_CA)
        # 實際上可拿到的 curC
        real_valid_volume_curC = valid_volume_CA * (1 - taker_fee_rate)

        # 拿到的 curC 可以換到多少 curB
        possible_curB_volume = real_valid_volume_curC / ask_price_BC
        # B/C 可吃單的量
        valid_BC_volume = min(possible_curB_volume, ask_volume_BC)
        # 實際上可以拿到的 curB
        real_valid_curB_amount = valid_BC_volume * (1 - taker_fee_rate)

        # 可以吃下 B/A 的量
        valid_BA_volume = min(bid_volume_BA, real_valid_curB_amount)
        # 要吃掉 B/A 的量需要多少 curB 才夠
        needed_curB_amount = valid_BA_volume / (1 - taker_fee_rate)
        # 換算需要買多少 curC 才夠
        needed_curC_amount = (needed_curB_amount * ask_price_BC) / (1 - taker_fee_rate)
        # 換算需要多少 curA 才夠
        needed_curA_amount = (needed_curC_amount * ask_price_CA) / (1 - taker_fee_rate)


        # 取到小數點第 8 位
        floored_needed_curA_amount = utils.get_floored_amount(needed_curA_amount)
        floored_needed_curB_amount = utils.get_floored_amount(needed_curB_amount)
        floored_needed_curC_amount = utils.get_floored_amount(needed_curC_amount)

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
        if floored_needed_curA_amount < limits_CA['cost']['min']:
            return 0
        elif (floored_needed_curA_amount / ask_price_CA) < limits_CA['amount']['min']:
            return 0
        elif floored_needed_curC_amount < limits_BC['cost']['min']:
            return 0
        elif (floored_needed_curC_amount / ask_price_BC) < limits_BC['amount']['min']:
            return 0
        elif floored_needed_curB_amount < limits_BA['amount']['min']:
            return 0
        elif (floored_needed_curB_amount * bid_price_BA) < limits_BA['cost']['min']:
            return 0
        else:
            return floored_needed_curC_amount
