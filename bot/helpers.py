# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))

from max.client import Client
from secrets import MAX_KEY, MAX_SECRET


def get_max_client():
    client = Client(MAX_KEY, MAX_SECRET)
    return client
