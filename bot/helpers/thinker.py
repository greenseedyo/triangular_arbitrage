# -*- coding: utf-8 -*-

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
        def find_valid_cur2(tmp_cur1, tmp_cur3):
            candidates = {}
            valid_ones = {}
            for m in markets:
                candidate = m['base']
                if candidate == tmp_cur1 or candidate == tmp_cur3 or (candidate in valid_ones):
                    continue
                if m['quote'] == tmp_cur1 or m['quote'] == tmp_cur3:
                    if candidate in candidates:  # 若已存在表示兩者皆有
                        valid_ones[candidate] = True
                    else:
                        candidates[candidate] = True
            return valid_ones
    
        combinations = {}
        for market in markets:
            if not market['active']:
                continue
            cur1 = market['quote']
            cur3 = market['base']
            valid_cur2 = find_valid_cur2(cur1, cur3)
            for cur2 in valid_cur2:
                key = '{}-{}-{}'.format(cur1, cur2, cur3)
                combinations[key] = [cur1, cur2, cur3]
        return combinations

    @staticmethod
    def get_market_symbols_of_combinations(combinations):
        symbols = {}
        for key in combinations:
            combination = combinations[key]
            cur1, cur2, cur3 = combination
            symbol_21 = '{}/{}'.format(cur2, cur1)
            symbol_23 = '{}/{}'.format(cur2, cur3)
            symbol_31 = '{}/{}'.format(cur3, cur1)
            symbols[symbol_21] = True
            symbols[symbol_23] = True
            symbols[symbol_31] = True
        return symbols.keys()

    def get_target_combinations(self, cur1_targets):
        valid_combinations = self.get_all_valid_combinations()
        target_combinations = {}
        for cur1_target in cur1_targets:
            for key in valid_combinations:
                combination = valid_combinations[key]
                cur1, cur2, cur3 = combination
                if cur1 != cur1_target:
                    continue
                target_combinations[key] = combination
        return target_combinations

    def check_forward_opportunity(self, ask_price_21, bid_price_23, bid_price_31):
        ratio = self.get_op_ratio(ask_price_21, bid_price_23, bid_price_31)
        # 若比值小於 1，表示可以用較低的價格用 cur1 透過 cur2 換到 cur3
        if ratio <= self.threshold_forward:
            return True
        else:
            return False

    def check_reverse_opportunity(self, bid_price_21, ask_price_23, ask_price_31):
        ratio = self.get_op_ratio(bid_price_21, ask_price_23, ask_price_31)
        # 若比值大於 1，表示可以用較高的價格用 cur3 透過 cur2 換到 cur1
        if ratio >= self.threshold_reverse:
            return True
        else:
            return False

    @staticmethod
    def get_op_ratio(primary_price, secondary_price, real_price):
        # 計算操作匯率
        op_rate = primary_price / secondary_price
        # 計算比值
        ratio = op_rate / real_price
        return ratio

    def get_valid_forward_volume(self, max_cur1_amount, limits_21, limits_23, limits_31,
                                 cur1_amount, ask_price_21, ask_volume_21,
                                 bid_price_23, bid_volume_23, bid_price_31, bid_volume_31):
        taker_fee_rate = self.get_fee_rate('taker')
        print('input: ', locals())
        # cur1 可用金額
        valid_cur1_amount = min(max_cur1_amount, cur1_amount)
        # cur1 可用金額換算可買的 cur2
        cur2_possible_volume = valid_cur1_amount / ask_price_21
        # 最多就是 B/A 掛單上的量
        valid_21_volume = min(cur2_possible_volume, ask_volume_21)
        # 扣手續費後可拿到的 cur2
        real_valid_volume_cur2 = valid_21_volume * (1 - taker_fee_rate)

        # B/C 可吃單的量
        valid_23_volume = min(real_valid_volume_cur2, bid_volume_23)
        # 實際上可以拿到的 cur3
        real_valid_cur3_amount = (valid_23_volume * bid_price_23) * (1 - taker_fee_rate)

        # 可以吃下 C/A 的量
        valid_31_volume = min(bid_volume_31, real_valid_cur3_amount)
        # 要吃掉 C/A 的量需要多少 cur3 才夠
        needed_cur3_amount = valid_31_volume / (1 - taker_fee_rate)
        # 換算需要買多少 cur2 才夠
        needed_cur2_amount = (needed_cur3_amount / bid_price_23) / (1 - taker_fee_rate)
        # 換算需要多少 cur1 才夠
        needed_cur1_amount = (needed_cur2_amount * ask_price_21) / (1 - taker_fee_rate)

        # 取到小數點第 8 位
        floored_needed_cur1_amount = utils.get_floored_amount(needed_cur1_amount)
        floored_needed_cur2_amount = utils.get_floored_amount(needed_cur2_amount)
        floored_needed_cur3_amount = utils.get_floored_amount(needed_cur3_amount)

        print('valid_cur1_amount', valid_cur1_amount)
        print('cur2_possible_volume', cur2_possible_volume)
        print('valid_21_volume', valid_21_volume)
        print('real_valid_volume_cur2', real_valid_volume_cur2)
        print('valid_23_volume', valid_23_volume)
        print('real_valid_cur3_amount', real_valid_cur3_amount)
        print('valid_31_volume', valid_31_volume)
        print('needed_cur3_amount', needed_cur3_amount)
        print('needed_cur2_amount', needed_cur2_amount)
        print('needed_cur1_amount', needed_cur1_amount)

        # 是否達最小交易量
        if floored_needed_cur1_amount < limits_21['cost']['min']:
            return 0
        elif floored_needed_cur1_amount / ask_price_21 < limits_21['amount']['min']:
            return 0
        elif floored_needed_cur2_amount < limits_23['amount']['min']:
            return 0
        elif floored_needed_cur2_amount * bid_price_23 < limits_23['cost']['min']:
            return 0
        elif floored_needed_cur3_amount < limits_31['amount']['min']:
            return 0
        elif floored_needed_cur3_amount * bid_price_31 < limits_31['cost']['min']:
            return 0
        else:
            return floored_needed_cur2_amount

    def get_valid_reverse_volume(self, max_cur1_amount, limits_21, limits_23, limits_31,
                                 cur1_amount, ask_price_31, ask_volume_31,
                                 ask_price_23, ask_volume_23, bid_price_21, bid_volume_21):
        taker_fee_rate = self.get_fee_rate('taker')
        print('input: ', locals())
        # cur1 可用金額
        valid_cur1_amount = min(max_cur1_amount, cur1_amount)
        # cur1 可用金額換算可買到的 cur3
        possible_cur3_volume = valid_cur1_amount / ask_price_31
        # 最多就是 C/A 掛單上的量
        valid_volume_31 = min(possible_cur3_volume, ask_volume_31)
        # 實際上可拿到的 cur3
        real_valid_volume_cur3 = valid_volume_31 * (1 - taker_fee_rate)

        # 拿到的 cur3 可以換到多少 cur2
        possible_cur2_volume = real_valid_volume_cur3 / ask_price_23
        # B/C 可吃單的量
        valid_23_volume = min(possible_cur2_volume, ask_volume_23)
        # 實際上可以拿到的 cur2
        real_valid_cur2_amount = valid_23_volume * (1 - taker_fee_rate)

        # 可以吃下 B/A 的量
        valid_21_volume = min(bid_volume_21, real_valid_cur2_amount)
        # 要吃掉 B/A 的量需要多少 cur2 才夠
        needed_cur2_amount = valid_21_volume / (1 - taker_fee_rate)
        # 換算需要買多少 cur3 才夠
        needed_cur3_amount = (needed_cur2_amount * ask_price_23) / (1 - taker_fee_rate)
        # 換算需要多少 cur1 才夠
        needed_cur1_amount = (needed_cur3_amount * ask_price_31) / (1 - taker_fee_rate)

        # 取到小數點第 8 位
        floored_needed_cur1_amount = utils.get_floored_amount(needed_cur1_amount)
        floored_needed_cur2_amount = utils.get_floored_amount(needed_cur2_amount)
        floored_needed_cur3_amount = utils.get_floored_amount(needed_cur3_amount)

        print('valid_cur1_amount', valid_cur1_amount)
        print('possible_cur3_volume', possible_cur3_volume)
        print('real_valid_volume_cur3', real_valid_volume_cur3)
        print('possible_cur2_volume', possible_cur2_volume)
        print('valid_23_volume', valid_23_volume)
        print('real_valid_cur2_amount', real_valid_cur2_amount)
        print('valid_21_volume', valid_21_volume)
        print('needed_cur2_amount', needed_cur2_amount)
        print('needed_cur3_amount', needed_cur3_amount)
        print('needed_cur1_amount', needed_cur1_amount)

        # 是否達最小交易量
        if floored_needed_cur1_amount < limits_31['cost']['min']:
            return 0
        elif (floored_needed_cur1_amount / ask_price_31) < limits_31['amount']['min']:
            return 0
        elif floored_needed_cur3_amount < limits_23['cost']['min']:
            return 0
        elif (floored_needed_cur3_amount / ask_price_23) < limits_23['amount']['min']:
            return 0
        elif floored_needed_cur2_amount < limits_21['amount']['min']:
            return 0
        elif (floored_needed_cur2_amount * bid_price_21) < limits_21['cost']['min']:
            return 0
        else:
            return floored_needed_cur3_amount
