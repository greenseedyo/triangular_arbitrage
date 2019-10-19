# -*- coding: utf-8 -*-

from bot.helpers.trader import Trader
from bot.helpers.trader import TradeSkippedException, BadMarketSymbolException
from bot.helpers.thinker import Thinker
from bot.helpers.loggers import Loggers
import bot.helpers.utils as utils
import time
import logging
import matplotlib.pyplot as plt
import pandas
import os
from pprint import pprint
import sys
import threading



ROOT_DIR = os.path.realpath('{}/../../../'.format(os.path.abspath(__file__)))


def set_error_logger(name):
    logger = logging.getLogger('error')
    logger.setLevel(logging.ERROR)
    file_handler = logging.FileHandler("logs/errors/{}.log".format(name))
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(fmt="[%(asctime)s] %(filename)s[line:%(lineno)d]%(levelname)s - %(message)s\n",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def check():
    mode = 'test_trade'
    exchange = 'max'

    # error_log 設定
    error_log_name = 'circle-{}-{}'.format(mode, exchange)
    set_error_logger(error_log_name)

    # enabled_cur2_candidates = ['BTC', 'ETH', 'LTC', 'BCH', 'MITH', 'USDT', 'TRX', 'EOS', 'BAT', 'ZRX', 'GNT', 'OMG', 'KNC', 'XRP']
    cur1 = 'TWD'
    cur2 = 'ETH'
    cur3 = 'USDT'

    # 交易金額上限設定 (測試時可設定較少金額)
    max_cur1_trade_amount = 1000

    thinker = Thinker(exchange)
    trader = Trader(exchange)

    config = {
        'cur1': cur1,
        'cur2': cur2,
        'cur3': cur3,
        'max_cur1_trade_amount': max_cur1_trade_amount,
        'exchange': exchange,
        'thinker': thinker,
        'trader': trader,
        'mode': mode,
    }
    try:
        run_one(config)
    except Exception as e:
        print(e)


def run():
    run_loop('production')


def explore():
    run_loop('explore')


def run_loop(mode):
    # 交易所
    exchange = sys.argv[1]

    # error_log 設定
    error_log_name = 'circle-{}-{}'.format(mode, exchange)
    set_error_logger(error_log_name)

    # 想賺的幣別
    cur1_targets = sys.argv[2].split(',')

    # 交易金額上限設定 (測試時可設定較少金額)
    max_cur1_trade_amount = 30000

    # 輪詢間隔
    interval = int(sys.argv[3]) if len(sys.argv) >= 3 else 1

    # helpers
    thinker = Thinker(exchange)
    trader = Trader(exchange)

    # 尋找可行的 triangular arbitrage 組合
    target_combinations = thinker.get_target_combinations(cur1_targets)

    # 若有 websocket 就開另一個 thread 做 streaming
    if utils.has_websocket(exchange):
        market_symbols = thinker.get_market_symbols_of_combinations(target_combinations)
        trader.thread_stream_order_books(market_symbols)

    print('Exchange: {}'.format(exchange))
    print('Thresholds: {} / {}'.format(thinker.threshold_forward, thinker.threshold_reverse))
    print('Targets: {}'.format(sys.argv[2]))
    print('Combinations: {}'.format(len(target_combinations)))
    print("\n")

    while 1:
        for key in target_combinations:
            if key in utils.cross_threads_variables['invalid_combinations']:
                continue
            combination = target_combinations[key]
            cur1, cur2, cur3 = combination
            config = {
                'cur1': cur1,
                'cur2': cur2,
                'cur3': cur3,
                'max_cur1_trade_amount': max_cur1_trade_amount,
                'exchange': exchange,
                'thinker': thinker,
                'trader': trader,
                'mode': mode,
            }
            t = threading.Thread(target=run_one, args=(config,))
            t.start()

            if utils.cross_threads_variables['stream_started']:
                time.sleep(0.1)
            else:
                time.sleep(interval)
        print('---------------------------------------------------------------------')


def run_one(config):
    cur1 = config['cur1']
    cur2 = config['cur2']
    cur3 = config['cur3']
    exchange = config['exchange']
    max_cur1_trade_amount = config['max_cur1_trade_amount']

    print('[{}]'.format(time.strftime('%c')))
    print('{} - {} - {}'.format(cur1, cur2, cur3))

    trader = config['trader']
    thinker = config['thinker']

    # 交易量下限 (上限先不管)
    symbol_21 = '{}/{}'.format(cur2, cur1)
    symbol_23 = '{}/{}'.format(cur2, cur3)
    symbol_31 = '{}/{}'.format(cur3, cur1)
    limits_21 = trader.exchange_adapter.fetch_trading_limits(symbol_21)
    limits_23 = trader.exchange_adapter.fetch_trading_limits(symbol_23)
    limits_31 = trader.exchange_adapter.fetch_trading_limits(symbol_31)

    # 取得交易對報價
    try:
        order_book_21 = trader.get_order_book(symbol_21, 1)
        order_book_23 = trader.get_order_book(symbol_23, 1)
        order_book_31 = trader.get_order_book(symbol_31, 1)
    except BadMarketSymbolException:
        key = '{}-{}-{}'.format(cur1, cur2, cur3)
        print('record invalid combination: {}'.format(key))
        utils.cross_threads_variables['invalid_combinations'][key] = True
        return
    except ConnectionAbortedError as e:
        print(e)
        logging.getLogger('error').exception(e)
        sys.exit(0)
    except Exception as e:
        print(e)
        logging.getLogger('error').exception(e)
        return

    if (order_book_21 is None) or (order_book_23 is None) or (order_book_31 is None):
        return

    try:
        lowest_ask_price_21 = float(order_book_21['asks'][0][0])
        lowest_ask_volume_21 = float(order_book_21['asks'][0][1])
        highest_bid_price_21 = float(order_book_21['bids'][0][0])
        highest_bid_volume_21 = float(order_book_21['bids'][0][1])

        lowest_ask_price_23 = float(order_book_23['asks'][0][0])
        lowest_ask_volume_23 = float(order_book_23['asks'][0][1])
        highest_bid_price_23 = float(order_book_23['bids'][0][0])
        highest_bid_volume_23 = float(order_book_23['bids'][0][1])

        lowest_ask_price_31 = float(order_book_31['asks'][0][0])
        lowest_ask_volume_31 = float(order_book_31['asks'][0][1])
        highest_bid_price_31 = float(order_book_31['bids'][0][0])
        highest_bid_volume_31 = float(order_book_31['bids'][0][1])
    except IndexError:
        return

    # 計算操作匯率
    forward_ratio = thinker.get_op_ratio(lowest_ask_price_21, highest_bid_price_23, highest_bid_price_31)
    reverse_ratio = thinker.get_op_ratio(highest_bid_price_21, lowest_ask_price_23, lowest_ask_price_31)
    print('Forward ratio: {0:.8f}'.format(forward_ratio))
    print('Reverse ratio: {0:.8f}'.format(reverse_ratio))

    combination = '{}-{}-{}'.format(cur1, cur2, cur3)
    # log_ratio(exchange, combination, forward_ratio, reverse_ratio)

    mode = config['mode']

    def exec_trade(direction):
        trade_method = 'exec_test_trade'
        if 'forward' == direction:
            ratio = forward_ratio
            cur1_amount = trader.get_currency_amount(cur1)
            price_21 = lowest_ask_price_21
            price_23 = highest_bid_price_23
            price_31 = highest_bid_price_31
            take_volume = thinker.get_valid_forward_volume(max_cur1_amount=max_cur1_trade_amount,
                                                           limits_21=limits_21,
                                                           limits_23=limits_23,
                                                           limits_31=limits_31,
                                                           cur1_amount=cur1_amount,
                                                           ask_price_21=lowest_ask_price_21,
                                                           ask_volume_21=lowest_ask_volume_21,
                                                           bid_price_23=highest_bid_price_23,
                                                           bid_volume_23=highest_bid_volume_23,
                                                           bid_price_31=highest_bid_price_31,
                                                           bid_volume_31=highest_bid_volume_31)
            print('take volume: {}{}'.format(take_volume, cur2))
            if 'production' == mode or 'test_real_trade' == mode:
                trade_method = 'exec_forward_trade'
        elif 'reverse' == direction:
            ratio = reverse_ratio
            price_21 = highest_bid_price_21
            price_23 = lowest_ask_price_23
            price_31 = lowest_ask_price_31
            cur1_amount = trader.get_currency_amount(cur1)
            take_volume = thinker.get_valid_reverse_volume(max_cur1_amount=max_cur1_trade_amount,
                                                           limits_21=limits_21,
                                                           limits_23=limits_23,
                                                           limits_31=limits_31,
                                                           cur1_amount=cur1_amount,
                                                           ask_price_31=lowest_ask_price_31,
                                                           ask_volume_31=lowest_ask_volume_31,
                                                           ask_price_23=lowest_ask_price_23,
                                                           ask_volume_23=lowest_ask_volume_23,
                                                           bid_price_21=highest_bid_price_21,
                                                           bid_volume_21=highest_bid_volume_21)
            print('take volume: {}{}'.format(take_volume, cur3))
            if 'production' == mode or 'test_real_trade' == mode:
                trade_method = 'exec_reverse_trade'
        else:
            raise ValueError('direction must be forward or reverse')

        if 'test_trade' == mode:
            take_volume = take_volume if take_volume > 0 else 1

        if take_volume > 0:
            amounts_before = trader.get_currencies_amounts([cur1, cur2, cur3])
            log_trade(time.strftime('%c'), direction, cur1, cur2,
                      cur3, take_volume, ratio)
            try:
                method = getattr(trader, trade_method)
                method(symbol_21, symbol_23, symbol_31, take_volume, price_21, price_23, price_31)
            except TradeSkippedException as ex:
                logging.getLogger('error').exception(ex)
            # 取得最新結餘資訊
            time.sleep(2)
            amounts_after = trader.get_currencies_amounts([cur1, cur2, cur3])
            log_balance(exchange, amounts=amounts_after, amounts_before=amounts_before)

    if 'test_trade' == mode or 'test_real_trade' == mode:
        exec_trade('forward')
        return

    # 檢查是否可順向操作
    forward_opportunity = thinker.check_forward_opportunity(lowest_ask_price_21, highest_bid_price_23, highest_bid_price_31)
    if forward_opportunity:
        volume = min(lowest_ask_volume_21, highest_bid_volume_23)
        log_opportunity(exchange, combination, 'forward', volume, cur2, forward_ratio)
        if 'explore' != mode:
            exec_trade('forward')

    # 檢查是否可反向操作 (外幣買入加密貨幣、台幣賣出加密貨幣)
    reverse_opportunity = thinker.check_reverse_opportunity(highest_bid_price_21, lowest_ask_price_23, lowest_ask_price_31)
    if reverse_opportunity:
        volume = min(highest_bid_volume_21, lowest_ask_volume_23)
        log_opportunity(exchange, combination, 'reverse', volume, cur2, reverse_ratio)
        if 'explore' != mode:
            exec_trade('reverse')


def log_ratio(exchange, combination, forward_ratio, reverse_ratio):
    msg = '{},{},{}'.format(combination, forward_ratio, reverse_ratio)

    log_name = 'ratio'
    log_dir = '{}/logs'.format(ROOT_DIR)
    log_path = '{}/{}/{}/{}.log'.format(log_dir, log_name, exchange, log_name)

    logger = Loggers().get_rotate_info_logger(log_name, log_path)
    logger.log(msg)


def log_opportunity(exchange, combination, direction, volume, cur, ratio):
    msg = '{0} OPPORTUNITY {1}: possible volume: {2:.8f}{3}, ratio: {4:.8f}'.format(
        direction.upper(), combination, volume, cur, ratio
    )

    log_name = 'opportunity'
    log_dir = '{}/logs'.format(ROOT_DIR)
    log_path = '{}/{}/{}/{}.log'.format(log_dir, log_name, exchange, log_name)

    logger = Loggers().get_rotate_info_logger(log_name, log_path)
    logger.log(msg)


def log_trade(formatted_time, direction, cur1, cur2, cur3, take_volume, ratio):
    if 'forward' == direction:
        start_cur = cur2
    elif 'reverse' == direction:
        start_cur = cur3
    else:
        raise ValueError('direction must be forward or reverse')
    trade_msg = '[{0}]\n{1}: {2}-{3}-{4}\nVolume: {5:.8f}{6}\nRatio: {7:.8f}'.format(
        formatted_time, direction.upper(), cur1, cur2, cur3, take_volume, start_cur, ratio)
    print(trade_msg)
    utils.log_to_slack(trade_msg)
    write_log('trade', trade_msg)


def log_balance(exchange, amounts, amounts_before=None):
    info = [] \
        .append('[{}]'.format(time.strftime('%c'))) \
        .append('Exchange: {}'.format(exchange))
    for symbol in amounts:
        amount = amounts[symbol]
        if isinstance(amounts_before, dict):
            amount_before = amounts_before[symbol]
            diff = amount - amount_before
            info.append('{0}: {1:.8f} ({2:.8f})'.format(symbol, amount, diff))
        else:
            info.append('{0}: {1:.8f}'.format(symbol, amount))
    msg = "\n".join(info)
    print('[NEW BALANCE INFO]')
    print(msg)
    utils.log_to_slack(msg)
    write_log('balance', msg)


def write_log(log_name, msg):
    log_file = 'logs/{}.log'.format(log_name)
    dir_path = os.path.dirname(os.path.realpath(log_file))
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(log_file, 'a') as the_file:
        the_file.write(msg)
        the_file.write('\n')


def plot():
    names = ['time', 'forward', 'reverse']
    data = pandas.read_csv('logs/ratio-TWD-ETH-USDT-max-binance.log', header=None, names=names)
    plt.plot(data.time, data.forward)
    plt.plot(data.time, data.reverse)
    plt.axhline(y=0.995, color='r', linestyle='-')
    plt.axhline(y=1.005, color='r', linestyle='-')
    plt.show()
