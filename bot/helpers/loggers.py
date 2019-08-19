# -*- coding: utf-8 -*-

import os
import sys
import logging
from logging import handlers


class Loggers:
    __single = None
    loggers = None

    def __new__(cls):
        if not Loggers.__single:
            Loggers.__single = object.__new__(cls)
        return Loggers.__single

    def __init__(self):
        if self.loggers is None:
            self.loggers = {}

    def get(self, log_name):
        if log_name in self.loggers:
            return self.loggers[log_name]
        else:
            return None

    def set(self, log_name):
        logger = logging.getLogger(log_name)
        self.loggers[log_name] = logger

    def get_rotate_info_logger(self, log_name, exchange):
        logger = self.get(log_name)
        if logger is None:
            logger = RotateInfoLogger(log_name, exchange)
            self.loggers[log_name] = logger
        return logger


class RotateInfoLogger:
    def __init__(self, log_name, log_path):
        # 檔案路徑
        log_path_dir = os.path.dirname(os.path.realpath(log_path))
        if not os.path.exists(log_path_dir):
            os.makedirs(log_path_dir)

        logger = logging.getLogger(log_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        formatter = logging.Formatter(fmt="[%(asctime)s] %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S")
        # 輸出至檔案
        file_time_rotating = handlers.TimedRotatingFileHandler(log_path, when="midnight", interval=1, backupCount=30)
        file_time_rotating.suffix = "%Y-%m-%d"
        file_time_rotating.setFormatter(formatter)
        logger.addHandler(file_time_rotating)
        # 輸出至 console
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
        self.logger = logger

    def log(self, msg):
        self.logger.info(msg)
