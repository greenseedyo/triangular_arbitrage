# -*- coding: utf-8 -*-

import math


def get_floored_amount(amount, digits=8):
    multiple = math.pow(10, digits)
    return math.floor(amount * multiple) / multiple
