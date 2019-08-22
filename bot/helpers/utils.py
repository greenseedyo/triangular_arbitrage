# -*- coding: utf-8 -*-

import sys
import math
from bot.helpers.slack import Slack


def get_floored_amount(amount, digits=8):
    multiple = math.pow(10, digits)
    return math.floor(amount * multiple) / multiple


def get_rounded_amount(amount, digits=8):
    return round(amount, digits)


def get_exchange_adapter(exchange_name):
    exchange_adapter_module_name = 'bot.adapters.{}'.format(exchange_name)
    try:
        __import__(exchange_adapter_module_name)
        module = sys.modules[exchange_adapter_module_name]
        adapter_name = '{}Adapter'.format(exchange_name.capitalize())
        adapter = getattr(module, adapter_name)()
    except ImportError:
        import bot.adapters.general
        module = sys.modules['bot.adapters.general']
        adapter_name = 'GeneralAdapter'
        adapter = getattr(module, adapter_name)(exchange_name)
    return adapter


def log_to_slack(msg):
    Slack.send_message(msg)
