#!/usr/bin/python3
# -*- coding: utf-8 -*-

import colorlog
import datetime
import logging


def pretty_date(date_string):
    return datetime.datetime.strptime(date_string[:19], '%Y-%m-%dT%H:%M:%S').strftime('%b %_d %T')


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


def setup_logging(log_simple, log_level):
    """Set up the logging."""
    date_format = '%Y-%m-%d:%H:%M:%S'
    if log_simple:
        log_format = '%(asctime)s %(levelname)s %(message)s'
        color_format = '%(asctime)s %(log_color)s%(levelname)s%(reset)s %(message)s'
    else:
        log_format = '%(asctime)s,%(msecs)d %(levelname)s' \
                     ' [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s'
        color_format = '%(asctime)s,%(msecs)d %(log_color)s%(levelname)s%(reset)s' \
                       ' [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s'
    logging.basicConfig(format=log_format,
                        datefmt=date_format,
                        level=log_level)
    logging.getLogger().handlers[0].setFormatter(
        colorlog.ColoredFormatter(
            color_format,
            datefmt=date_format,
            reset=True,
            log_colors={'DEBUG': 'cyan', 'INFO': 'green', 'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'red'}
        )
    )
    set_up_logger = logging.getLogger(__name__)
    set_up_logger.setLevel(log_level)
    return set_up_logger
