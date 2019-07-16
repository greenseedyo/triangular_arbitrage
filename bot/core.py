# -*- coding: utf-8 -*-

from . import helpers

def run():
    client = helpers.get_max_client()
    result = client.get_public_all_currencies()
    print(f"[I] Invoked get_public_all_currencies() API Result: \n    {result}\n")
