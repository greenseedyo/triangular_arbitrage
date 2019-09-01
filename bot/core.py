# -*- coding: utf-8 -*-

from bot.helpers import swing_helpers

import time
import logging
import matplotlib.pyplot as plt
import pandas
from pprint import pprint
import bot.helpers.utils as utils


logging.basicConfig(filename='logs/error.log')


def plot():
    names = ['time', 'forward', 'reverse']
    data = pandas.read_csv('logs/ratio-TWD-USDT-USD-max-bitfinex.log', header=None, names=names)
    plt.plot(data.time, data.forward)
    plt.plot(data.time, data.reverse)
    plt.axhline(y=0.9975, color='r', linestyle='-')
    plt.axhline(y=1.0025, color='r', linestyle='-')
    plt.show()


def check():
    first_currency = 'TWD'
    bridge_currency = 'ETH'
    second_currency = 'USDT'
    primary_exchange = 'max'
    secondary_exchange = 'binance'
    config = {
        'real_rate_handler': 'get_real_rate_in_primary_exchange',
        'bridge_currency': bridge_currency,
        'first_currency': first_currency,
        'second_currency': second_currency,
        'max_first_currency_trade_amount': 1000,
        'min_bridge_currency_trade_amount': 0.05,
        'threshold_forward': 0.997,  # 順向
        'threshold_reverse': 1.003,  # 逆向
        'primary_exchange': primary_exchange,
        'secondary_exchange': secondary_exchange,
        'mode': 'test_trade',
    }
    try:
        run_one(config)
        # trader = swing_helpers.Trader(config)
        # amount = trader.get_bridge_currency_amount_in_primary_exchange()
        # pprint(amount)
        # amount = trader.get_bridge_currency_amount_in_secondary_exchange()
        # pprint(amount)
    except Exception as e:
        print(e)
    #print(trader.get_bridge_currency_amount_in_secondary_exchange())
    #print(trader.get_real_rate())
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #print(trader.secondary_exchange_adapter.markets['ETH/USDT'])
    #trader.secondary_exchange_adapter.create_market_sell_order('ETH/USDT', 0.05, {'type': 'market'})
    #trader.exec_forward_trade(0.05)
    #trader.exec_reverse_trade(0.05)
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #trader.sell_bridge_currency_from_primary_exchange(0.1)
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #trader.sell_bridge_currency_from_secondary_exchange(0.05)
    #print(trader.fetch_primary_orders())
    #print(trader.fetch_secondary_orders()[-1])
    pprint('done.')


def explore():
    # 幣種設定
    first_currency = 'TWD'
    bridge_currency = 'USDT'
    second_currency = 'USD'

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.9975  # 順向
    threshold_reverse = 1.0025  # 逆向

    # 交易所設定
    primary_exchange = 'max'
    secondary_exchange = 'bitfinex'

    while 1:
        # 取得銀行匯率 (時間, 現金買入, 現金賣出, 即期買入, 即期賣出)
        config = {
            'real_rate_handler': 'get_usdtwd_by_twder',
            'bridge_currency': bridge_currency,
            'first_currency': first_currency,
            'second_currency': second_currency,
            'max_first_currency_trade_amount': 0,
            'min_bridge_currency_trade_amount': 0,
            'threshold_forward': threshold_forward,  # 順向
            'threshold_reverse': threshold_reverse,  # 逆向
            'primary_exchange': primary_exchange,
            'secondary_exchange': secondary_exchange,
            'mode': 'explore',
        }
        try:
            run_one(config)
        except Exception as e:
            print(e)
            logging.exception(e)
        time.sleep(30)


def swing():
    # enabled_bridge_currencies = ['BTC', 'ETH', 'LTC', 'BCH', 'MITH', 'USDT', 'TRX', 'EOS', 'BAT', 'ZRX', 'GNT', 'OMG', 'KNC', 'XRP']
    enabled_bridge_currencies = ['ETH']

    first_currency = 'TWD'
    second_currency = 'USDT'
    real_rate_handler = 'get_usdtwd_by_twder'

    # 交易金額上限設定
    max_first_currency_trade_amount = 10000
    # 交易量下限設定
    min_bridge_currency_trade_amount = 0.05

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.9975  # 順向
    threshold_reverse = 1.0025  # 逆向

    # 交易所設定
    primary_exchange = 'max'
    secondary_exchange = 'binance'

    while 1:
        for bridge_currency in enabled_bridge_currencies:
            config = {
                'real_rate_handler': real_rate_handler,
                'bridge_currency': bridge_currency,
                'first_currency': first_currency,
                'second_currency': second_currency,
                'max_first_currency_trade_amount': max_first_currency_trade_amount,
                'min_bridge_currency_trade_amount': min_bridge_currency_trade_amount,
                'threshold_forward': threshold_forward,  # 順向
                'threshold_reverse': threshold_reverse,  # 逆向
                'primary_exchange': primary_exchange,
                'secondary_exchange': secondary_exchange,
                'mode': 'production',
            }
            try:
                run_one(config)
            except Exception as e:
                print(e)
                logging.exception(e)
            time.sleep(30)


def run_one(config):
    first_currency = config['first_currency']
    bridge_currency = config['bridge_currency']
    second_currency = config['second_currency']

    print('[{}]'.format(time.strftime('%c')))
    print('{} - {} - {}'.format(first_currency, bridge_currency, second_currency))

    trader = swing_helpers.Trader(config)
    config['real_rate'] = trader.get_real_rate()
    thinker = swing_helpers.Thinker(config)

    # 取得第一交易所的加密貨幣報價
    primary_order_book = trader.get_primary_order_book(1)
    primary_lowest_ask_price = float(primary_order_book['asks'][0][0])
    primary_highest_bid_price = float(primary_order_book['bids'][0][0])

    # 取得第二交易所的加密貨幣報價
    secondary_order_book = trader.get_secondary_order_book(1)
    secondary_lowest_ask_price = float(secondary_order_book['asks'][0][0])
    secondary_highest_bid_price = float(secondary_order_book['bids'][0][0])

    # 計算操作匯率
    forward_ratio = thinker.get_op_ratio(primary_lowest_ask_price, secondary_highest_bid_price)
    reverse_ratio = thinker.get_op_ratio(primary_highest_bid_price, secondary_lowest_ask_price)
    ratio_log = '{},{},{}'.format(int(time.time()), forward_ratio, reverse_ratio)

    log_name_suffix = '-{}-{}-{}-{}-{}'.format(first_currency, bridge_currency, second_currency, config['primary_exchange'], config['secondary_exchange'])

    # TODO: 分日期
    write_log('ratio{}'.format(log_name_suffix), ratio_log)

    mode = config['mode']

    def exec_trade(direction, buy_side_order_book, sell_side_order_book):
        buy_side_lowest_ask_price = buy_side_order_book['asks'][0][0]
        buy_side_lowest_ask_volume = buy_side_order_book['asks'][0][1]
        sell_side_highest_bid_volume = sell_side_order_book['bids'][0][1]
        trade_method = 'exec_test_trade'

        if 'forward' == direction:
            buy_side_currency_amount = trader.get_first_currency_amount()
            sell_side_currency_amount = trader.get_bridge_currency_amount_in_secondary_exchange()
            if 'production' == mode or 'test_real_trade' == mode:
                trade_method = 'exec_forward_trade'
        elif 'reverse' == direction:
            buy_side_currency_amount = trader.get_second_currency_amount()
            sell_side_currency_amount = trader.get_bridge_currency_amount_in_primary_exchange()
            if 'production' == mode or 'test_real_trade' == mode:
                trade_method = 'exec_reverse_trade'
        else:
            raise ValueError('direction must be forward or reverse')

        # 計算買進/賣出量
        take_volume = thinker.get_valid_volume(direction,
                                                     buy_side_currency_amount=buy_side_currency_amount,
                                                     buy_side_lowest_ask_price=buy_side_lowest_ask_price,
                                                     buy_side_lowest_ask_volume=buy_side_lowest_ask_volume,
                                                     sell_side_currency_amount=sell_side_currency_amount,
                                                     sell_side_highest_bid_volume=sell_side_highest_bid_volume)
        print('take volume: {}'.format(take_volume))
        if take_volume > 0:
            log_trade(time.strftime('%c'), direction, first_currency, bridge_currency,
                      second_currency, take_volume, forward_ratio)
            try:
                method = getattr(trader, trade_method)
                method(take_volume)
            except swing_helpers.TradeSkippedException as e:
                logging.exception(e)
            # 取得最新結餘資訊
            log_balance(trader)

    def log_opportunity(direction, buy_side_order_book, sell_side_order_book):
        buy_side_lowest_ask_price = buy_side_order_book['asks'][0][0]
        buy_side_lowest_ask_volume = buy_side_order_book['asks'][0][1]
        sell_side_highest_bid_price= sell_side_order_book['bids'][0][0]
        sell_side_highest_bid_volume = sell_side_order_book['bids'][0][1]
        if 'forward' == direction:
            ratio = thinker.get_op_ratio(buy_side_lowest_ask_price, sell_side_highest_bid_price)
        elif 'reverse' == direction:
            ratio = thinker.get_op_ratio(sell_side_highest_bid_price, buy_side_lowest_ask_price)
        else:
            raise ValueError('direction must be forward or reverse')
        possible_volume = min(buy_side_lowest_ask_volume, sell_side_highest_bid_volume)
        msg = '[{}] {} OPPORTUNITY: {} possible volume: {}, ratio: {}'.format(
            time.strftime('%c'), direction.upper(), bridge_currency, possible_volume, ratio)
        print(msg)
        write_log('opportunity{}'.format(log_name_suffix), msg)

    if 'test_trade' == mode or 'test_real_trade' == mode:
        #exec_trade('forward', primary_order_book, secondary_order_book)
        exec_trade('reverse', secondary_order_book, primary_order_book)
        return

    # 檢查是否可順向操作 (台幣買入加密貨幣、外幣賣出加密貨幣)
    forward_opportunity = thinker.check_forward_opportunity(primary_lowest_ask_price, secondary_highest_bid_price)
    if forward_opportunity:
        log_opportunity('forward', primary_order_book, secondary_order_book)
        if 'explore' != mode:
            exec_trade('forward', primary_order_book, secondary_order_book)

    # 檢查是否可反向操作 (外幣買入加密貨幣、台幣賣出加密貨幣)
    reverse_opportunity = thinker.check_reverse_opportunity(secondary_lowest_ask_price, primary_highest_bid_price)
    if reverse_opportunity:
        log_opportunity('reverse', secondary_order_book, primary_order_book)
        if 'explore' != mode:
            exec_trade('reverse', secondary_order_book, primary_order_book)


def log_trade(formatted_time, direction, first_currency, bridge_currency, second_currency, take_volume, ratio):
    trade_msg = '{}, {}, {}, {}, {}, {}, {}'.format(formatted_time, direction, first_currency, bridge_currency,
                                                    second_currency, take_volume, ratio)
    print(trade_msg)
    write_log('trade', trade_msg)
    utils.log_to_slack(trade_msg)


def log_balance(trader):
    info = trader.get_balance_info()
    balance_msg = "\n".join(info)
    print('[NEW BALANCE INFO]')
    print(balance_msg)
    write_log('balance', balance_msg)
    utils.log_to_slack(balance_msg)


def write_log(log_name, msg):
    log_file = 'logs/{}.log'.format(log_name)
    with open(log_file, 'a') as the_file:
        the_file.write(msg)
        the_file.write('\n')
