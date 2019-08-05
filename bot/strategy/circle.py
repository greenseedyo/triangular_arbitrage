# -*- coding: utf-8 -*-

from bot.helpers.trader import Trader
from bot.helpers.trader import TradeSkippedException
from bot.helpers.thinker import Thinker
import time
import logging
import matplotlib.pyplot as plt
import pandas
from pprint import pprint


logging.basicConfig(filename='logs/error.log')


def plot():
    names = ['time', 'forward', 'reverse']
    data = pandas.read_csv('logs/ratio-TWD-ETH-USDT-max-binance.log', header=None, names=names)
    plt.plot(data.time, data.forward)
    plt.plot(data.time, data.reverse)
    plt.axhline(y=0.995, color='r', linestyle='-')
    plt.axhline(y=1.005, color='r', linestyle='-')
    plt.show()


def check():
    # enabled_curB_candidates = ['BTC', 'ETH', 'LTC', 'BCH', 'MITH', 'USDT', 'TRX', 'EOS', 'BAT', 'ZRX', 'GNT', 'OMG', 'KNC', 'XRP']

    curA = 'TWD'
    curB = 'XRP'
    curC = 'USDT'

    # 交易金額上限設定 (測試時可設定較少金額)
    max_curA_trade_amount = 1000

    # 交易量下限設定 (看交易所規定)
    min_curA_trade_volume_limit = 250
    min_curB_trade_volume_limit = 27
    min_curC_trade_volume_limit = 8

    exchange = 'max'
    config = {
        'curA': curA,
        'curB': curB,
        'curC': curC,
        'max_curA_trade_amount': max_curA_trade_amount,
        'min_curA_trade_volume_limit': min_curA_trade_volume_limit,
        'min_curB_trade_volume_limit': min_curB_trade_volume_limit,
        'min_curC_trade_volume_limit': min_curC_trade_volume_limit,
        'threshold_forward': 0.995,  # 順向
        'threshold_reverse': 1.005,  # 逆向
        'exchange': exchange,
        'mode': 'test_trade',
    }
    try:
        run_one(config)
    except Exception as e:
        print(e)
    #trader = Trader(config)
    #print(trader.get_curB_amount())
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #print(trader.exchange_adapter.markets['ETH/USDT'])
    #trader.exchange_adapter.create_market_sell_order('ETH/USDT', 0.05, {'type': 'market'})
    #trader.exec_forward_trade(0.05)
    #trader.exec_reverse_trade(0.05)
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #trader.sell_curB_from_exchange(0.1)
    #info = trader.get_balance_info()
    #print("\n".join(info))
    #trader.sell_curB(0.05)
    #print(trader.fetch_primary_orders())
    #print(trader.fetch_secondary_orders()[-1])


def explore():
    # 幣種設定
    curA = 'TWD'
    curB = 'ETH'
    curC = 'BTC'

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.995  # 順向
    threshold_reverse = 1.005  # 逆向

    # 交易所設定
    exchange = 'max'

    while 1:
        # 取得銀行匯率 (時間, 現金買入, 現金賣出, 即期買入, 即期賣出)
        config = {
            'curA': curA,
            'curB': curB,
            'curC': curC,
            'threshold_forward': 0.995,  # 順向
            'threshold_reverse': 1.005,  # 逆向
            'exchange': exchange,
            'mode': 'explore',
        }
        try:
            run_one(config)
        except Exception as e:
            print(e)
            logging.exception(e)
        time.sleep(30)


def run():
    # enabled_curB_candidates = ['BTC', 'ETH', 'LTC', 'BCH', 'MITH', 'USDT', 'TRX', 'EOS', 'BAT', 'ZRX', 'GNT', 'OMG', 'KNC', 'XRP']
    # enabled_curB_candidates = ['ETH']

    curA = 'TWD'
    curB = 'ETH'
    curC = 'BTC'

    # 交易金額上限設定 (測試時可設定較少金額)
    max_curA_trade_amount = 1000

    # 交易量下限設定 (看交易所規定)
    min_curA_trade_volume_limit = 1000
    min_curB_trade_volume_limit = 0.05
    min_curC_trade_volume_limit = 0.0015

    # 可執行交易的 (操作匯率 / 銀行匯率) 閥值設定
    threshold_forward = 0.995  # 順向
    threshold_reverse = 1.005  # 逆向

    # 交易所設定
    exchange = 'max'

    while 1:
        config = {
            'curA': curA,
            'curB': curB,
            'curC': curC,
            'max_curA_trade_amount': max_curA_trade_amount,
            'min_curA_trade_volume_limit': min_curA_trade_volume_limit,
            'min_curB_trade_volume_limit': min_curB_trade_volume_limit,
            'min_curC_trade_volume_limit': min_curC_trade_volume_limit,
            'threshold_forward': threshold_forward,  # 順向
            'threshold_reverse': threshold_reverse,  # 逆向
            'exchange': exchange,
            'mode': 'production',
        }
        try:
            run_one(config)
        except Exception as e:
            print(e)
            logging.exception(e)
        time.sleep(30)


def run_one(config):
    curA = config['curA']
    curB = config['curB']
    curC = config['curC']
    max_curA_trade_amount = config['max_curA_trade_amount']
    min_curB_trade_volume_limit = config['min_curB_trade_volume_limit']
    min_curC_trade_volume_limit = config['min_curC_trade_volume_limit']

    print('[{}]'.format(time.strftime('%c')))
    print('{} - {} - {}'.format(curA, curB, curC))

    trader = Trader(config)
    thinker = Thinker(config)

    #pprint(trader.exchange_adapter.fetch_orders('USDT/TWD', limit=1))
    #return

    symbol_BA = '{}/{}'.format(curB, curA)
    symbol_BC = '{}/{}'.format(curB, curC)
    symbol_CA = '{}/{}'.format(curC, curA)

    # 取得 B/A 交易對報價
    order_book_BA = trader.get_order_book(symbol_BA, 1)
    lowest_ask_price_BA = float(order_book_BA['asks'][0][0])
    lowest_ask_volume_BA = float(order_book_BA['asks'][0][1])
    highest_bid_price_BA = float(order_book_BA['bids'][0][0])
    highest_bid_volume_BA = float(order_book_BA['bids'][0][1])

    # 取得 B/C 交易對報價
    order_book_BC = trader.get_order_book(symbol_BC, 1)
    lowest_ask_price_BC = float(order_book_BC['asks'][0][0])
    lowest_ask_volume_BC = float(order_book_BC['asks'][0][1])
    highest_bid_price_BC = float(order_book_BC['bids'][0][0])
    highest_bid_volume_BC = float(order_book_BC['bids'][0][1])

    # 取得 C/A 交易對報價
    #order_book_CA = {'bids': [[360010.0, 0.0083331]], 'asks': [[362997.9, 0.11266379]], 'timestamp': None, 'datetime': None, 'nonce': None}
    order_book_CA = trader.get_order_book(symbol_CA, 1)
    lowest_ask_price_CA = float(order_book_CA['asks'][0][0])
    lowest_ask_volume_CA = float(order_book_CA['asks'][0][1])
    highest_bid_price_CA = float(order_book_CA['bids'][0][0])
    highest_bid_volume_CA = float(order_book_CA['bids'][0][1])

    # 計算操作匯率
    forward_ratio = thinker.get_op_ratio(lowest_ask_price_BA, highest_bid_price_BC, highest_bid_price_CA)
    reverse_ratio = thinker.get_op_ratio(highest_bid_price_BA, lowest_ask_price_BC, lowest_ask_price_CA)
    print('forward ratio: {}'.format(forward_ratio))
    print('reverse ratio: {}'.format(reverse_ratio))
    ratio_log = '{},{},{}'.format(int(time.time()), forward_ratio, reverse_ratio)

    log_name_suffix = '-{}-{}-{}-{}'.format(curA, curB, curC, config['exchange'])

    # TODO: 分日期
    write_log('ratio{}'.format(log_name_suffix), ratio_log)

    mode = config['mode']

    def exec_trade(direction):
        trade_method = 'exec_test_trade'
        price_BC = None
        if 'forward' == direction:
            ratio = forward_ratio
            curA_amount = trader.get_currency_amount(curA)
            take_volume = thinker.get_valid_forward_volume(max_curA_amount=max_curA_trade_amount,
                                                           min_curB_trade_volume_limit=min_curB_trade_volume_limit,
                                                           curA_amount=curA_amount,
                                                           price_BA=lowest_ask_price_BA,
                                                           ask_volume_BA=lowest_ask_volume_BA,
                                                           bid_price_BC=highest_bid_price_BC,
                                                           bid_volume_BC=highest_bid_volume_BC,
                                                           bid_volume_CA=highest_bid_volume_CA)
            print('take volume: {}{}'.format(take_volume, curB))
            if 'production' == mode:
                trade_method = 'exec_forward_trade'
        elif 'reverse' == direction:
            ratio = reverse_ratio
            price_BC = lowest_ask_price_BC
            curA_amount = trader.get_currency_amount(curA)
            take_volume = thinker.get_valid_reverse_volume(max_curA_amount=max_curA_trade_amount,
                                                           min_curC_trade_volume_limit=min_curC_trade_volume_limit,
                                                           curA_amount=curA_amount,
                                                           price_CA=lowest_ask_price_CA,
                                                           ask_volume_CA=lowest_ask_volume_CA,
                                                           ask_price_BC=lowest_ask_price_BC,
                                                           ask_volume_BC=lowest_ask_volume_BC,
                                                           bid_volume_BA=highest_bid_volume_BA)
            print('take volume: {}{}'.format(take_volume, curC))
            if 'production' == mode or 'test_real_trade' == mode:
                trade_method = 'exec_reverse_trade'
        else:
            raise ValueError('direction must be forward or reverse')

        if take_volume > 0:
            log_trade(time.strftime('%c'), direction, curA, curB,
                      curC, take_volume, ratio)
            try:
                method = getattr(trader, trade_method)
                method(symbol_BA, symbol_BC, symbol_CA, take_volume, price_BC)
            except TradeSkippedException as e:
                logging.exception(e)
            # 取得最新結餘資訊
            time.sleep(1)
            log_balance(trader, [curA, curB, curC])

    if 'test_trade' == mode or 'test_real_trade' == mode:
        exec_trade('reverse')
        return

    # 檢查是否可順向操作
    forward_opportunity = thinker.check_forward_opportunity(lowest_ask_price_BA, highest_bid_price_BC, highest_bid_price_CA)
    if forward_opportunity:
        volume = min(lowest_ask_price_BA, highest_bid_price_BC)
        log_opportunity(log_name_suffix, 'forward', volume, curB, forward_ratio)
        if 'explore' != mode:
            exec_trade('forward')

    # 檢查是否可反向操作 (外幣買入加密貨幣、台幣賣出加密貨幣)
    reverse_opportunity = thinker.check_reverse_opportunity(highest_bid_price_BA, lowest_ask_price_BC, lowest_ask_price_CA)
    if reverse_opportunity:
        volume = min(highest_bid_price_BA, lowest_ask_price_BC)
        log_opportunity(log_name_suffix, 'reverse', volume, curB, reverse_ratio)
        if 'explore' != mode:
            exec_trade('reverse')


def log_opportunity(log_name_suffix, direction, volume, cur, ratio):
    msg = '[{}] {} OPPORTUNITY: possible volume: {}{}, ratio: {}'.format(
        time.strftime('%c'), direction.upper(), volume, cur, ratio)
    print(msg)
    write_log('opportunity{}'.format(log_name_suffix), msg)


def log_trade(formatted_time, direction, curA, curB, curC, take_volume, ratio):
    if 'forward' == direction:
        start_cur = curB
    elif 'reverse' == direction:
        start_cur = curC
    else:
        raise ValueError('direction must be forward or reverse')
    trade_msg = '{}, {}, {}-{}-{}, {}{}, {}'.format(formatted_time, direction, curA, curB,
                                                    curC, take_volume, start_cur, ratio)
    print(trade_msg)
    write_log('trade', trade_msg)


def log_balance(trader, symbols):
    info = trader.get_balance_info(symbols)
    balance_msg = "\n".join(info)
    print('[NEW BALANCE INFO]')
    print(balance_msg)
    write_log('balance', balance_msg)


def write_log(log_name, msg):
    log_file = 'logs/{}.log'.format(log_name)
    with open(log_file, 'a') as the_file:
        the_file.write(msg)
        the_file.write('\n')
