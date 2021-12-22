#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
    Delete attachment files older than N hours
"""

import argparse
import os
import sys

from datetime import datetime, timedelta
from os.path import getmtime

# adding path /etc/netsniff to import config variables and common functions
sys.path.append('/etc/netsniff/')
import common         # noqa: E402
import variables      # noqa: E402

MAX_HOURS = 6


def set_limit(max_hours):
    """ Set the limit as a timestamp: everything before must be deleted.
        Return that timestamp calculated from the number of hours provided.

    :param max_hours: number
    :return: timestamp limit
    """
    limit = datetime.now() - timedelta(hours=max_hours)
    return int(limit.timestamp())


def delete_old_files(directory, max_hours, log):
    """ Delete "old" files older than 'max_hours' in 'directory', oldest first

    :param directory: attachments directory
    :param max_hours: lifetime allowed
    :param log: logger object
    """
    try:
        os.chdir(directory)
    except FileNotFoundError:
        log.error(f'Attachments directory "{directory}" not found.')
    else:
        # make timestamp from number of hours
        limit = set_limit(max_hours)
        to_delete = [(getmtime(name), name)
                     for name in os.listdir('.')
                     if getmtime(name) < limit]
        logger.info(f'Files to delete: {len(to_delete)}')
        for number, (modified, name) in enumerate(sorted(to_delete)):
            log.info(f'delete ({common.seconds_to_date(modified)}) {name}')
            try:
                os.remove(name)
            except IsADirectoryError:
                log.error(f'"{name}" is a directory !')


PARSER = argparse.ArgumentParser()
PARSER.add_argument('-l', '--logged', action='store_true', help='set log format for script output')
ARGS = PARSER.parse_args()

logger = common.setup_logging(simple=not ARGS.logged)

logger.info(f'Script start')

delete_old_files(variables.ATTACHMENTS_DIR, MAX_HOURS, logger)

logger.info(f'Script end')
