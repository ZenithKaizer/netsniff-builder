#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
    script to interact with MediaStorage from Netsniff Python scripts
"""

import argparse
import logging
import re
import sys

from datetime import datetime, timedelta

# adding path /etc/netsniff to import config variables, common functions and MediaStorage class
sys.path.append('/etc/netsniff/')
import common         # noqa: E402
import mediastorage   # noqa: E402
import variables      # noqa: E402

MAX_DAYS = 31
MAX_DELETE_ERRORS = 1000
DATETIME_REGEXP = r'^20\d\d-[01]\d(-[0-3]\d(T[0-2]\d:[0-5]\d(:[0-5]\d)?)?)?$'


def get_old_date_or_exit(arg_date, error_logger):
    """ provide date-stamp string that will be used to select container contents to delete

    :param arg_date: optional CLI parameter provided date string
    :param error_logger: imported logger error handler
    :return: validated date string
    """
    if arg_date:
        if re.match(DATETIME_REGEXP, arg_date):
            return arg_date
        else:
            error_logger('Incorrect date provided')
            sys.exit()
    else:
        limit = datetime.now() - timedelta(MAX_DAYS)
        # keep only the date part of the datetime stamp
        return limit.isoformat()[:10]


def run(extended_variables):
    """ Sequence of main operations

    :param extended_variables: constants, variables and CLI parameters
    """

    common_logger = extended_variables.logger

    common_logger.info(f'Process start')

    ms_obj = mediastorage.MediaStorage(extended_variables)

    try:
        limit_date = get_old_date_or_exit(arg_date=extended_variables.cli_args.date,
                                          error_logger=common_logger.error)

        ms_obj.swift_connection_initiate()

        objects_references = ms_obj.get_objects_references()

        old_objects_references = ms_obj.get_old_objects_references(objects_references, limit_date)

        ms_obj.delete_objects(old_objects_references)

    except KeyboardInterrupt:
        print('\r', end='')
        common_logger.error('Manual interruption !')

    finally:
        ms_obj.swift_connection_close()
        common_logger.info(f'Process end')


PARSER = argparse.ArgumentParser()
PARSER.add_argument('-d', '--date', type=str, help='oldest date allowed for attachments: yyyy-mm-dd[Thh:mm[:ss]]')
PARSER.add_argument('-n', '--dry-run', action='store_true', help='show how many objects would be deleted')
PARSER.add_argument('-v', '--verbose', action='store_true', help='run the script in verbose mode (print DEBUG messages)')
ARGS = PARSER.parse_args()

level = logging.DEBUG if ARGS.verbose else logging.INFO
manual = ARGS.dry_run or ARGS.date is not None

logger = common.setup_logging(level=level, simple=manual)

# temporary local deletion log
day = datetime.now().strftime('%a')
del_name = f'deletions.{day}.log'
try:
    del_file, del_file_error = open(del_name, 'w'), None
except IOError as error:
    del_file, del_file_error = None, error
    logger.error(f'failed to write-open "{del_name}":\n{error}')

variables.max_days = MAX_DAYS
variables.max_del_errors = MAX_DELETE_ERRORS
variables.logger = logger
variables.manual = manual
variables.cli_args = ARGS
variables.del_file = del_file

run(variables)

# temporary local deletion log
if del_file:
    try:
        del_file.close()
    except IOError:
        pass
else:
    logger.error(f'deletion log file "{del_name}" was not write-open:\n{del_file_error}')
