# -*- coding: utf-8 -*-

from . import helpers
import time
import twder


def run():
    # 幣種設定
    # enabled_cryptocurrencies = ['BTC', 'ETH', 'LTC', 'BCH', 'MITH', 'USDT', 'TRX', 'EOS', 'BAT', 'ZRX', 'GNT', 'OMG', 'KNC', 'XRP']
    enabled_cryptocurrencies = ['BTC', 'ETH', 'LTC']

    # 交易金額上限設定
    max_local_fiat = 10000

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.996  # 順向
    threshold_reverse = 1.007  # 逆向

    # 交易所設定
    local_exchange = 'max'
    local_exchange_fee_rate = 0.0015
    foreign_exchange = 'bitfinex'
    foreign_exchange_fee_rate = 0.002

    while 1:
        for cryptocurrency in enabled_cryptocurrencies:
            # 取得銀行匯率 (時間, 現金買入, 現金賣出, 即期買入, 即期賣出)
            bank_rate = float(twder.now('USD')[4])
            print('bank rate: {}'.format(bank_rate))
            config = {
                'bank_rate': bank_rate,
                'cryptocurrency': cryptocurrency,
                'local_fiat': 'TWD',
                'foreign_fiat': 'USD',
                'max_local_fiat': max_local_fiat,
                'threshold_forward': threshold_forward,  # 順向
                'threshold_reverse': threshold_reverse,  # 逆向
                'local_exchange': local_exchange,
                'local_exchange_fee_rate': local_exchange_fee_rate,
                'foreign_exchange': foreign_exchange,
                'foreign_exchange_fee_rate': foreign_exchange_fee_rate,
            }
            run_one(config)
            time.sleep(20)


def run_one(config):
    cryptocurrency = config['cryptocurrency']
    local_fiat = config['local_fiat']
    foreign_fiat = config['foreign_fiat']

    print('[{}]'.format(time.strftime('%c')))
    print('{} - {} - {}'.format(cryptocurrency, local_fiat, foreign_fiat))

    # 每次交易上限金額
    bank_rate = config['bank_rate']
    max_local_fiat = config['max_local_fiat']
    max_foreign_fiat = max_local_fiat / bank_rate

    trader = helpers.Trader(config)
    thinker = helpers.Thinker(config)

    # 取得台灣交易所的加密貨幣報價
    local_book = trader.get_local_order_book(1)
    local_lowest_buy_price = float(local_book['asks'][0][0])
    local_lowest_buy_volume = float(local_book['asks'][0][1])
    local_highest_sell_price = float(local_book['bids'][0][0])
    local_highest_sell_volume = float(local_book['bids'][0][1])

    # 取得外國交易所的加密貨幣報價
    foreign_book = trader.get_foreign_order_book(1)
    foreign_lowest_buy_price = float(foreign_book['asks'][0][0])
    foreign_lowest_buy_volume = float(foreign_book['asks'][0][1])
    foreign_highest_sell_price = float(foreign_book['bids'][0][0])
    foreign_highest_sell_volume = float(foreign_book['bids'][0][1])

    # 檢查是否可順向操作 (台幣買入加密貨幣、外幣賣出加密貨幣)
    forward_opportunity = thinker.check_forward_opportunity(local_lowest_buy_price, foreign_highest_sell_price)
    if forward_opportunity:
        possible_volume = min(local_lowest_buy_volume, foreign_highest_sell_volume)
        msg = '[{}] EXECUTE FORWARD OPERATION: {} possible volume: {}'.format(
            time.strftime('%c'), cryptocurrency, possible_volume)
        print(msg)
        write_exec_log(msg)
        valid_volume = thinker.get_valid_volume(local_lowest_buy_price, local_lowest_buy_volume,
                                                foreign_highest_sell_price, foreign_highest_sell_volume)
        trader.exec_forward_trade(valid_volume)

    # 檢查是否可逆向操作 (外幣買入加密貨幣、台幣賣出加密貨幣)
    reverse_opportunity = thinker.check_reverse_opportunity(foreign_lowest_buy_price, local_highest_sell_price)
    if reverse_opportunity:
        possible_volume = min(local_highest_sell_volume, foreign_lowest_buy_volume)
        msg = '[{}] EXECUTE REVERSE OPERATION: {} possible volume: {}'.format(
            time.strftime('%c'), cryptocurrency, possible_volume)
        print(msg)
        write_exec_log(msg)
        valid_volume = thinker.get_valid_volume(local_highest_sell_price, local_highest_sell_volume,
                                                foreign_lowest_buy_price, foreign_lowest_buy_volume)
        trader.exec_reverse_trade(valid_volume)


def write_exec_log(msg):
    with open('logs/exec_log.txt', 'a') as the_file:
        the_file.write(msg)
        the_file.write('\n')
