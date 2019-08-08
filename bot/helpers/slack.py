# -*- coding: utf-8 -*-

import json
import requests
from secrets import SLACK_WEBHOOK


class Slack:
    @staticmethod
    def send_message(message):
        dict_headers = {'Content-type': 'application/json'}
        dict_payload = {"text": message}
        json_payload = json.dumps(dict_payload)
        rtn = requests.post(SLACK_WEBHOOK, data=json_payload, headers=dict_headers)
        #print(rtn.text)
        return rtn
