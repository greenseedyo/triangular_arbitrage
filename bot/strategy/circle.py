# -*- coding: utf-8 -*-

from bot.helpers.trader import Trader
from bot.helpers.trader import TradeSkippedException, NoMarketSymbolException
from bot.helpers.thinker import Thinker
from bot.helpers.loggers import Loggers
import bot.helpers.utils as utils
import time
import logging
import matplotlib.pyplot as plt
import pandas
import os
import threading
import asyncio
from pprint import pprint
import sys


ROOT_DIR = os.path.realpath('{}/../../../'.format(os.path.abspath(__file__)))


def set_error_logger():
    logger = logging.getLogger('error')
    logger.setLevel(logging.ERROR)
    file_handler = logging.FileHandler("logs/error.log")
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(fmt="[%(asctime)s] %(filename)s[line:%(lineno)d]%(levelname)s - %(message)s\n",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


set_error_logger()


def test():
    curA_targets = ['ETH', 'BTC', 'USDT']
    exchange = 'binance'
    threshold_forward = 0.996
    threshold_reverse = 1.004
    max_curA_trade_amount = 10000
    config = {
        'threshold_forward': threshold_forward,  # 順向
        'threshold_reverse': threshold_reverse,  # 逆向
        'exchange': exchange,
    }
    thinker = Thinker(config)
    trader = Trader(config)
    target_combinations = thinker.get_target_combinations(curA_targets)
    print(len(target_combinations))
    market_symbols = thinker.get_market_symbols_of_combinations(target_combinations)
    t = threading.Thread(target=stream_order_books, args=(trader, market_symbols,))
    t.start()
    #time.sleep(5)
    #print(utils.order_books)

    while 1:
        for key in target_combinations:
            combination = target_combinations[key]
            curA, curB, curC = combination
            config = {
                'curA': curA,
                'curB': curB,
                'curC': curC,
                'threshold_forward': threshold_forward,  # 順向
                'threshold_reverse': threshold_reverse,  # 逆向
                'max_curA_trade_amount': max_curA_trade_amount,
                'exchange': exchange,
                'mode': 'explore',
            }
            try:
                run_one(config)
            except Exception as e:
                print(e)
                logging.getLogger('error').exception(e)
            time.sleep(0.2)


def stream_order_books(trader, markets):
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(trader.stream_order_books(markets))


def check():
    # enabled_curB_candidates = ['BTC', 'ETH', 'LTC', 'BCH', 'MITH', 'USDT', 'TRX', 'EOS', 'BAT', 'ZRX', 'GNT', 'OMG', 'KNC', 'XRP']

    curA = 'TWD'
    curB = 'ETH'
    curC = 'USDT'

    # 交易金額上限設定 (測試時可設定較少金額)
    max_curA_trade_amount = 1000

    exchange = 'max'
    config = {
        'curA': curA,
        'curB': curB,
        'curC': curC,
        'max_curA_trade_amount': max_curA_trade_amount,
        'threshold_forward': 0.996,  # 順向
        'threshold_reverse': 1.004,  # 逆向
        'exchange': exchange,
        'mode': 'test_trade',
    }
    try:
        run_one(config)
        #trader = Trader(config)
        #amounts = trader.get_currencies_amounts([curA, curB, curC])
        #pprint(amounts)
    except Exception as e:
        print(e)


def explore():
    # 交易所設定
    exchange = 'binance'

    curA_candidates = ['ETH']
    curB_candidates = ['BTC', 'ETH', 'LINK', 'XRP', 'SBE', 'DOGE', 'MAR', 'LTC', 'XMR', 'WAVES', 'JDC', 'TRX', 'BCH', 'TELOS', 'CGEN',
                       'POP', 'VLU', 'OK', 'JDC', 'ILC']
    curC_candidates = ['USDT', 'BTC', 'ETH']

    # 交易金額上限設定 (測試時可設定較少金額)
    max_curA_trade_amount = 1000

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.9965  # 順向
    threshold_reverse = 1.0035  # 逆向

    skip_check = {}
    while 1:
        for curA in curA_candidates:
            for curB in curB_candidates:
                for curC in curC_candidates:
                    if curA == curB or curB == curC or curA == curC:
                        continue
                    key = '{}-{}-{}'.format(curA, curB, curC)
                    if key in skip_check:
                        continue

                    config = {
                        'curA': curA,
                        'curB': curB,
                        'curC': curC,
                        'threshold_forward': threshold_forward,  # 順向
                        'threshold_reverse': threshold_reverse,  # 逆向
                        'max_curA_trade_amount': max_curA_trade_amount,
                        'exchange': exchange,
                        'mode': 'explore',
                    }
                    try:
                        run_one(config)
                    except NoMarketSymbolException:
                        skip_check[key] = True
                    except Exception as e:
                        print(e)
                        logging.getLogger('error').exception(e)
                    time.sleep(1)
            #time.sleep(10)
        print('---------------------------------------------------------------------')


def run():
    # 交易所
    exchange = sys.argv[1]

    # 想賺的幣別
    curA_targets = sys.argv[2].split(',')

    # 交易金額上限設定 (測試時可設定較少金額)
    max_curA_trade_amount = 30000

    exchange_adapter = utils.get_exchange_adapter(exchange)
    taker_fee_rate = exchange_adapter.taker_fee_rate

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 1 - (taker_fee_rate * 3 + 0.0005)  # 順向
    threshold_reverse = 1 + (taker_fee_rate * 3 + 0.0005)  # 逆向

    config = {
        'threshold_forward': threshold_forward,  # 順向
        'threshold_reverse': threshold_reverse,  # 逆向
        'exchange': exchange,
    }
    thinker = Thinker(config)
    trader = Trader(config)
    target_combinations = thinker.get_target_combinations(curA_targets)
    market_symbols = thinker.get_market_symbols_of_combinations(target_combinations)
    if trader.has_websocket():
        t = threading.Thread(target=stream_order_books, args=(trader, market_symbols,))
        t.start()

    while 1:
        for key in target_combinations:
            combination = target_combinations[key]
            curA, curB, curC = combination
            config = {
                'curA': curA,
                'curB': curB,
                'curC': curC,
                'threshold_forward': threshold_forward,  # 順向
                'threshold_reverse': threshold_reverse,  # 逆向
                'max_curA_trade_amount': max_curA_trade_amount,
                'exchange': exchange,
                'mode': 'production',
            }
            try:
                t = threading.Thread(target=run_one, args=(config,))
                t.start()
                #run_one(config)
            except Exception as e:
                print(e)
                logging.getLogger('error').exception(e)
            time.sleep(1)
        #time.sleep(10)
        print('---------------------------------------------------------------------')


def run_one(config):
    curA = config['curA']
    curB = config['curB']
    curC = config['curC']
    exchange = config['exchange']
    max_curA_trade_amount = config['max_curA_trade_amount']

    print('[{}]'.format(time.strftime('%c')))
    print('{} - {} - {}'.format(curA, curB, curC))

    trader = Trader(config)
    thinker = Thinker(config)

    #pprint(trader.exchange_adapter.fetch_orders('USDT/TWD', limit=1))
    #return

    # 交易量下限 (上限先不管)
    symbol_BA = '{}/{}'.format(curB, curA)
    symbol_BC = '{}/{}'.format(curB, curC)
    symbol_CA = '{}/{}'.format(curC, curA)
    limits_BA = trader.exchange_adapter.fetch_trading_limits(symbol_BA)
    limits_BC = trader.exchange_adapter.fetch_trading_limits(symbol_BC)
    limits_CA = trader.exchange_adapter.fetch_trading_limits(symbol_CA)

    # 取得交易對報價
    order_book_BA = trader.get_order_book(symbol_BA, 1)
    order_book_BC = trader.get_order_book(symbol_BC, 1)
    order_book_CA = trader.get_order_book(symbol_CA, 1)

    if (order_book_BA is None) or (order_book_BC is None) or (order_book_CA is None):
        return

    try:
        lowest_ask_price_BA = float(order_book_BA['asks'][0][0])
        lowest_ask_volume_BA = float(order_book_BA['asks'][0][1])
        highest_bid_price_BA = float(order_book_BA['bids'][0][0])
        highest_bid_volume_BA = float(order_book_BA['bids'][0][1])

        lowest_ask_price_BC = float(order_book_BC['asks'][0][0])
        lowest_ask_volume_BC = float(order_book_BC['asks'][0][1])
        highest_bid_price_BC = float(order_book_BC['bids'][0][0])
        highest_bid_volume_BC = float(order_book_BC['bids'][0][1])

        lowest_ask_price_CA = float(order_book_CA['asks'][0][0])
        lowest_ask_volume_CA = float(order_book_CA['asks'][0][1])
        highest_bid_price_CA = float(order_book_CA['bids'][0][0])
        highest_bid_volume_CA = float(order_book_CA['bids'][0][1])
    except IndexError:
        return

    # 計算操作匯率
    forward_ratio = thinker.get_op_ratio(lowest_ask_price_BA, highest_bid_price_BC, highest_bid_price_CA)
    reverse_ratio = thinker.get_op_ratio(highest_bid_price_BA, lowest_ask_price_BC, lowest_ask_price_CA)
    print('Forward ratio: {0:.8f}'.format(forward_ratio))
    print('Reverse ratio: {0:.8f}'.format(reverse_ratio))

    combination = '{}-{}-{}'.format(curA, curB, curC)
    #log_ratio(exchange, combination, forward_ratio, reverse_ratio)

    mode = config['mode']

    def exec_trade(direction):
        trade_method = 'exec_test_trade'
        if 'forward' == direction:
            ratio = forward_ratio
            curA_amount = trader.get_currency_amount(curA)
            price_BA = lowest_ask_price_BA
            price_BC = highest_bid_price_BC
            price_CA = highest_bid_price_CA
            take_volume = thinker.get_valid_forward_volume(max_curA_amount=max_curA_trade_amount,
                                                           limits_BA=limits_BA,
                                                           limits_BC=limits_BC,
                                                           limits_CA=limits_CA,
                                                           curA_amount=curA_amount,
                                                           ask_price_BA=lowest_ask_price_BA,
                                                           ask_volume_BA=lowest_ask_volume_BA,
                                                           bid_price_BC=highest_bid_price_BC,
                                                           bid_volume_BC=highest_bid_volume_BC,
                                                           bid_price_CA=highest_bid_price_CA,
                                                           bid_volume_CA=highest_bid_volume_CA)
            print('take volume: {}{}'.format(take_volume, curB))
            if 'production' == mode or 'test_real_trade' == mode:
                trade_method = 'exec_forward_trade'
        elif 'reverse' == direction:
            ratio = reverse_ratio
            price_BA = highest_bid_price_BA
            price_BC = lowest_ask_price_BC
            price_CA = lowest_ask_price_CA
            curA_amount = trader.get_currency_amount(curA)
            take_volume = thinker.get_valid_reverse_volume(max_curA_amount=max_curA_trade_amount,
                                                           limits_BA=limits_BA,
                                                           limits_BC=limits_BC,
                                                           limits_CA=limits_CA,
                                                           curA_amount=curA_amount,
                                                           ask_price_CA=lowest_ask_price_CA,
                                                           ask_volume_CA=lowest_ask_volume_CA,
                                                           ask_price_BC=lowest_ask_price_BC,
                                                           ask_volume_BC=lowest_ask_volume_BC,
                                                           bid_price_BA=highest_bid_price_BA,
                                                           bid_volume_BA=highest_bid_volume_BA)
            print('take volume: {}{}'.format(take_volume, curC))
            if 'production' == mode or 'test_real_trade' == mode:
                trade_method = 'exec_reverse_trade'
        else:
            raise ValueError('direction must be forward or reverse')

        if 'test_trade' == mode:
            take_volume = take_volume if take_volume > 0 else 1

        if take_volume > 0:
            amounts_before = trader.get_currencies_amounts([curA, curB, curC])
            log_trade(time.strftime('%c'), direction, curA, curB,
                      curC, take_volume, ratio)
            try:
                method = getattr(trader, trade_method)
                method(symbol_BA, symbol_BC, symbol_CA, take_volume, price_BA, price_BC, price_CA)
            except TradeSkippedException as e:
                logging.getLogger('error').exception(e)
            # 取得最新結餘資訊
            time.sleep(2)
            amounts_after = trader.get_currencies_amounts([curA, curB, curC])
            log_balance(exchange, amounts=amounts_after, amounts_before=amounts_before)

    if 'test_trade' == mode or 'test_real_trade' == mode:
        exec_trade('forward')
        return

    # 檢查是否可順向操作
    forward_opportunity = thinker.check_forward_opportunity(lowest_ask_price_BA, highest_bid_price_BC, highest_bid_price_CA)
    if forward_opportunity:
        volume = min(lowest_ask_volume_BA, highest_bid_volume_BC)
        log_opportunity(exchange, combination, 'forward', volume, curB, forward_ratio)
        if 'explore' != mode:
            exec_trade('forward')

    # 檢查是否可反向操作 (外幣買入加密貨幣、台幣賣出加密貨幣)
    reverse_opportunity = thinker.check_reverse_opportunity(highest_bid_price_BA, lowest_ask_price_BC, lowest_ask_price_CA)
    if reverse_opportunity:
        volume = min(highest_bid_volume_BA, lowest_ask_volume_BC)
        log_opportunity(exchange, combination, 'reverse', volume, curB, reverse_ratio)
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


def log_trade(formatted_time, direction, curA, curB, curC, take_volume, ratio):
    if 'forward' == direction:
        start_cur = curB
    elif 'reverse' == direction:
        start_cur = curC
    else:
        raise ValueError('direction must be forward or reverse')
    trade_msg = '[{0}]\n{1}: {2}-{3}-{4}\nVolume: {5:.8f}{6}\nRatio: {7:.8f}'.format(formatted_time, direction.upper(), curA, curB,
                                                    curC, take_volume, start_cur, ratio)
    print(trade_msg)
    utils.log_to_slack(trade_msg)
    write_log('trade', trade_msg)


def log_balance(exchange, amounts, amounts_before=None):
    info = []
    info.append('[{}]'.format(time.strftime('%c')))
    info.append('Exchange: {}'.format(exchange))
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
