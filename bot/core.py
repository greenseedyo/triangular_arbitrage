# -*- coding: utf-8 -*-

from . import helpers
import twder

def run():
    # 取得銀行匯率 (時間, 現金買入, 現金賣出, 即期買入, 即期賣出)
    bank_rate = 32#float(twder.now('USD')[4])
    print('bank rate:')
    print(bank_rate)

    # 每次交易上限金額
    max_local_fiat = 10000
    max_foreign_fiat = max_local_fiat / bank_rate


    # 取得台灣交易所的加密貨幣報價
    local_exchange_info = helpers.get_local_exchange_info('ETHTWD', 1)
    local_lowest_buy_price = float(local_exchange_info['asks'][0]['price'])
    local_lowest_buy_volume = float(local_exchange_info['asks'][0]['volume'])
    local_highest_sell_price = float(local_exchange_info['bids'][0]['price'])
    local_highest_sell_volume = float(local_exchange_info['bids'][0]['volume'])

    # 取得外國交易所的加密貨幣報價
    foreign_exchange_info = helpers.get_foreign_exchange_info('ETH/USD', 1)
    foreign_lowest_buy_price = float(foreign_exchange_info['asks'][0]['price'])
    foreign_lowest_buy_volume = float(foreign_exchange_info['asks'][0]['volume'])
    foreign_highest_sell_price = float(foreign_exchange_info['bids'][0]['price'])
    foreign_highest_sell_volume = float(foreign_exchange_info['bids'][0]['volume'])

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.985  # 順向
    threshold_reverse = 1.015  # 逆向

    # 檢查是否可順向操作 (台幣買入加密貨幣、外幣賣出加密貨幣)
    forward_opportunity = check_forward_opportunity(local_lowest_buy_price, foreign_highest_sell_price, bank_rate, threshold_forward)
    if forward_opportunity:
        print('execute forward operation...')
        valid_volume = get_valid_volume(max_local_fiat, local_lowest_buy_price, local_lowest_buy_volume,
                             max_foreign_fiat, foreign_highest_sell_price, foreign_highest_sell_volume)
        exec_forward_trade(valid_volume)

    # 檢查是否可逆向操作 (外幣買入加密貨幣、台幣賣出加密貨幣)
    reverse_opportunity = check_reverse_opportunity(foreign_lowest_buy_price, local_highest_sell_price, bank_rate, threshold_reverse)
    if reverse_opportunity:
        print('execute reverse operation.')
        valid_volume = get_valid_volume(max_local_fiat, local_highest_sell_price, local_highest_sell_volume,
                             max_foreign_fiat, foreign_lowest_buy_price, foreign_lowest_buy_volume)
        exec_reverse_trade(valid_volume)


def get_valid_volume(max_buy_fiat, buy_price, buy_volume,
                     max_sell_fiat, sell_price, sell_volume):
    valid_buy_volume = min(max_buy_fiat / buy_price, buy_volume)
    valid_sell_volume = min(max_sell_fiat / sell_price, sell_volume)
    valid_volume = min(valid_buy_volume, valid_sell_volume)
    print('valid buy volume: {}'.format(valid_buy_volume))
    print('valid sell volume: {}'.format(valid_sell_volume))
    print('valid volume: {}'.format(valid_volume))
    return valid_volume

def check_forward_opportunity(local_lowest_buy_price, foreign_highest_sell_price, bank_rate, threshold_forward):
    # 計算順向操作匯率 (台灣換外幣)
    forward_op_rate = local_lowest_buy_price / foreign_highest_sell_price
    print('forward operation rate:')
    print(forward_op_rate)
    ratio = forward_op_rate / bank_rate
    print('forward ratio:')
    print(ratio)
    # 若比值小於 1，表示可以用較銀行低的價錢用台幣換到外幣
    if ratio <= threshold_forward:
        return True
    else:
        return False

def check_reverse_opportunity(foreign_lowest_buy_price, local_highest_sell_price, bank_rate, threshold_reverse):
    # 計算逆向操作匯率 (外幣換台幣)
    reverse_op_rate = local_highest_sell_price / foreign_lowest_buy_price
    print('reverse operation rate:')
    print(reverse_op_rate)
    ratio = reverse_op_rate / bank_rate
    print('reverse ratio:')
    print(ratio)
    # 若比值大於 1，表示可以用較銀行高的價錢用外幣換到台幣
    if ratio >= threshold_reverse:
        return True
    else:
        return False

def exec_forward_trade(volume):
    # 成本 = 用台幣買入加密貨幣的吃單手續費 + 將加密貨幣賣掉換美元的吃單手續費
    return

def exec_reverse_trade(volume):
    return
