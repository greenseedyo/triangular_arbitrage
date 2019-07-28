# -*- coding: utf-8 -*-

from . import helpers
import time
import twder
import logging


logging.basicConfig(filename='logs/error.log', level=logging.DEBUG)


def check():
    local_fiat = 'TWD'
    foreign_fiat = 'USDT'
    cryptocurrency = 'ETH'
    local_exchange = 'max'
    foreign_exchange = 'binance'
    config = {
        'bank_rate': 31,
        'local_fiat': local_fiat,
        'foreign_fiat': foreign_fiat,
        'cryptocurrency': cryptocurrency,
        'local_exchange': local_exchange,
        'foreign_exchange': foreign_exchange,
    }
    trader = helpers.Trader(config)
    info = trader.get_balance_info()
    print("\n".join(info))
    #trader.exec_forward_trade(0.05)
    #trader.exec_reverse_trade(0.05)
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #trader.sell_cryptocurrency_from_local_exchange(0.1)
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #trader.sell_cryptocurrency_from_foreign_exchange(0.05)
    #print(trader.fetch_local_orders())
    #print(trader.fetch_foreign_orders())


def run():
    # 幣種設定
    # enabled_cryptocurrencies = ['BTC', 'ETH', 'LTC', 'BCH', 'MITH', 'USDT', 'TRX', 'EOS', 'BAT', 'ZRX', 'GNT', 'OMG', 'KNC', 'XRP']
    enabled_cryptocurrencies = ['ETH']

    # 交易金額上限設定
    max_local_fiat_trade_amount = 10000
    # 交易量下限設定
    min_cryptocurrency_trade_amount = 0.05

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.995  # 順向
    threshold_reverse = 1.005  # 逆向

    # 交易所設定
    local_exchange = 'max'
    foreign_exchange = 'binance'

    while 1:
        for cryptocurrency in enabled_cryptocurrencies:
            # 取得銀行匯率 (時間, 現金買入, 現金賣出, 即期買入, 即期賣出)
            while 1:
                try:
                    bank_rate = float(twder.now('USD')[4])
                except:
                    time.sleep(10)
                else:
                    break
            print('bank rate: {}'.format(bank_rate))
            config = {
                'bank_rate': bank_rate,
                'cryptocurrency': cryptocurrency,
                'local_fiat': 'TWD',
                'foreign_fiat': 'USDT',
                'max_local_fiat_trade_amount': max_local_fiat_trade_amount,
                'min_cryptocurrency_trade_amount': min_cryptocurrency_trade_amount,
                'threshold_forward': threshold_forward,  # 順向
                'threshold_reverse': threshold_reverse,  # 逆向
                'local_exchange': local_exchange,
                'foreign_exchange': foreign_exchange,
            }
            run_one(config)
            time.sleep(30)


def run_one(config):
    cryptocurrency = config['cryptocurrency']
    local_fiat = config['local_fiat']
    foreign_fiat = config['foreign_fiat']

    print('[{}]'.format(time.strftime('%c')))
    print('{} - {} - {}'.format(cryptocurrency, local_fiat, foreign_fiat))

    trader = helpers.Trader(config)
    thinker = helpers.Thinker(config)

    # 取得台灣交易所的加密貨幣報價
    local_book = trader.get_local_order_book(1)
    local_lowest_ask_price = float(local_book['asks'][0][0])
    local_lowest_ask_volume = float(local_book['asks'][0][1])
    local_highest_bid_price = float(local_book['bids'][0][0])
    local_highest_bid_volume = float(local_book['bids'][0][1])

    # 取得外國交易所的加密貨幣報價
    foreign_book = trader.get_foreign_order_book(1)
    foreign_lowest_ask_price = float(foreign_book['asks'][0][0])
    foreign_lowest_ask_volume = float(foreign_book['asks'][0][1])
    foreign_highest_bid_price = float(foreign_book['bids'][0][0])
    foreign_highest_bid_volume = float(foreign_book['bids'][0][1])

    # 計算操作匯率
    forward_ratio = thinker.get_op_ratio(local_lowest_ask_price, foreign_highest_bid_price)
    reverse_ratio = thinker.get_op_ratio(local_highest_bid_price, foreign_lowest_ask_price)
    ratio_log = '{},{},{}'.format(int(time.time()), forward_ratio, reverse_ratio)
    write_log('ratio', ratio_log)

    # 檢查是否可順向操作 (台幣買入加密貨幣、外幣賣出加密貨幣)
    forward_opportunity = thinker.check_forward_opportunity(local_lowest_ask_price, foreign_highest_bid_price)
    if forward_opportunity:
        possible_volume = min(local_lowest_ask_volume, foreign_highest_bid_volume)
        msg = '[{}] FORWARD OPPORTUNITY: {} possible volume: {}, ratio: {}'.format(
            time.strftime('%c'), cryptocurrency, possible_volume, forward_ratio)
        print(msg)
        write_log('opportunity', msg)
        #return
        # 計算買進/賣出量
        local_fiat_amount = trader.get_local_fiat_amount()
        foreign_cryptocurrency_amount = trader.get_foreign_cryptocurrency_amount()
        take_volume = thinker.get_valid_forward_volume(buy_side_fiat_amount=local_fiat_amount,
                                                       buy_side_lowest_ask_price=local_lowest_ask_price,
                                                       buy_side_lowest_ask_volume=local_lowest_ask_volume,
                                                       sell_side_cryptocurrency_amount=foreign_cryptocurrency_amount,
                                                       sell_side_highest_bid_volume=foreign_highest_bid_volume)
        if 0 == take_volume:
            return

        log_trade(time.strftime('%c'), cryptocurrency, take_volume, forward_ratio)
        try:
            trader.exec_forward_trade(take_volume)
        except helpers.TradeSkippedException as e:
            logging.exception(e)
        # 取得最新結餘資訊
        log_balance(trader)

    # 檢查是否可反向操作 (外幣買入加密貨幣、台幣賣出加密貨幣)
    reverse_opportunity = thinker.check_reverse_opportunity(foreign_lowest_ask_price, local_highest_bid_price)
    if reverse_opportunity:
        possible_volume = min(local_highest_bid_volume, foreign_lowest_ask_volume)
        msg = '[{}] REVERSE OPPORTUNITY: {} possible volume: {}, ratio: {}'.format(
            time.strftime('%c'), cryptocurrency, possible_volume, reverse_ratio)
        print(msg)
        write_log('opportunity', msg)
        #return
        # 計算買進/賣出量
        foreign_fiat_amount = trader.get_foreign_fiat_amount()
        local_cryptocurrency_amount = trader.get_local_cryptocurrency_amount()
        take_volume = thinker.get_valid_reverse_volume(buy_side_fiat_amount=foreign_fiat_amount,
                                                       buy_side_lowest_ask_price=foreign_lowest_ask_price,
                                                       buy_side_lowest_ask_volume=foreign_lowest_ask_volume,
                                                       sell_side_cryptocurrency_amount=local_cryptocurrency_amount,
                                                       sell_side_highest_bid_volume=local_highest_bid_volume)
        if 0 == take_volume:
            return

        log_trade(time.strftime('%c'), cryptocurrency, take_volume, forward_ratio)
        try:
            trader.exec_forward_trade(take_volume)
        except helpers.TradeSkippedException as e:
            logging.exception(e)
        # 取得最新結餘資訊
        log_balance(trader)


def log_trade(time, cryptocurrency, take_volume, forward_ratio):
    trade_msg = '{},{},{},{}'.format(time, cryptocurrency, take_volume, forward_ratio)
    print(trade_msg)
    write_log('trade', trade_msg)


def log_balance(trader):
    info = trader.get_balance_info()
    balance_msg = "\n".join(info)
    print('[NEW BALANCE INFO]')
    print(balance_msg)
    write_log('balance', balance_msg)


def write_log(log_name, msg):
    log_file = 'logs/{}.log'.format(log_name)
    with open(log_file, 'a') as the_file:
        the_file.write(msg)
        the_file.write('\n')
