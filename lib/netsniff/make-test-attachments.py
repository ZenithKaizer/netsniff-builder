#!/usr/bin/python3

import colorlog
import logging
import os
import random
import sys
import time


DIR = '/home/pptruser/attachments'
PATTERN = '%A-%d-%B-%T.test'


def setup_logging():
    formatter = colorlog.ColoredFormatter(
        f'%(asctime)s,%(msecs)03d %(log_color)s%(levelname)s%(reset)s'
        ' [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        log_colors={'INFO': 'green', 'ERROR': 'red'}
    )
    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    return log


logger = setup_logging()

try:
    os.chdir(DIR)
except FileNotFoundError:
    logger.error('directory not found.')
    sys.exit()

while True:
    try:
        name = time.strftime(PATTERN).lower()
        try:
            with open(name, 'w'):
                pass
        except OSError as error:
            seconds = 60
            logger.error(error)
        else:
            logger.info(f'"{name}" created')
            seconds = random.randint(1, 24) ** 2
        time.sleep(seconds)
    except KeyboardInterrupt:
        logger.info('exit.')
