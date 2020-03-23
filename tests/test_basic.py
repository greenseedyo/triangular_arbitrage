# -*- coding: utf-8 -*-

from .context import bot
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib-dev')))

import unittest
from unittest.mock import patch
from max.client import Client


class BasicTestSuite(unittest.TestCase):
    @patch('bot.helpers.get_max_client')
    def test_get_bid_depth(self):
        result = bot.helpers.get_buy_info('ethtwd', 2)


if __name__ == '__main__':
    unittest.main()
