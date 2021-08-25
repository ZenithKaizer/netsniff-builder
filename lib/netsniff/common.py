#!/usr/bin/python3
# -*- coding: utf-8 -*-

import colorlog
import logging

from datetime import datetime

HUMAN_DATE_FORMAT = '%b %_d %T'


def human_bytes(size):
    if size < 1024:
        string = f'{size} bytes'
    elif size < 1024**2:
        string = f'{size/1024:.1f} KB'
    elif size < 1024**3:
        string = f'{size/1024**2:.1f} MB'
    else:
        string = f'{size/1024**3:.1f} GB'
    return string


def human_date(date_time):
    return date_time.strftime(HUMAN_DATE_FORMAT)


def posix_to_date(date_string):
    date_time = datetime.strptime(date_string[:19], '%Y-%m-%dT%H:%M:%S')
    return human_date(date_time)


def pretty_duration(secs):
    if secs < 60:
        return f'{secs:.1f} seconds'
    if type(secs) != int:
        secs = int(secs)
    if secs < 3600:
        string = ''
    else:
        string = f'{secs // 3600}h'
        secs = secs % 3600
    if secs >= 60 or (string and secs):
        if string:
            string += f' {secs // 60:02}m'
        else:
            string = f'{secs // 60}m'
        secs = secs % 60
    if secs:
        string += f' {secs:02}s'
    return string


def seconds_to_date(timestamp):
    date_time = datetime.fromtimestamp(timestamp)
    return human_date(date_time)


def setup_logging(level=logging.INFO, simple=False):
    """Set up the logging."""
    date_format = '%Y-%m-%d:%H:%M:%S'
    log_format = f'%(asctime)s %(log_color)s%(levelname)s%(reset)s %(message)s' if simple else \
        f'%(asctime)s,%(msecs)03d %(log_color)s%(levelname)s%(reset)s' \
        ' [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s'
    formatter = colorlog.ColoredFormatter(
        log_format,
        datefmt=date_format,
        log_colors={'DEBUG': 'cyan', 'INFO': 'green', 'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'red'}
    )
    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger
