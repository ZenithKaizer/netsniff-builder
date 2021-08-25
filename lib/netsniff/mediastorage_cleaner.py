#!/usr/bin/python3
# -*- coding: utf-8 -*-

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
    if arg_date:
        if re.match(DATETIME_REGEXP, arg_date):
            return arg_date
        else:
            error_logger('Incorrect date provided')
            sys.exit()
    else:
        limit_stamp = datetime.now() - timedelta(MAX_DAYS)
        # keep only the date part of the datetime stamp
        limit_date = limit_stamp.isoformat()[:10]
        return limit_date


def run(extended_variables):

    log = extended_variables.logger

    log.info(f'Process start')

    ms_obj = mediastorage.MediaStorage(extended_variables)

    try:
        limit_date = get_old_date_or_exit(arg_date=extended_variables.cli_args.date,
                                          error_logger=log.error)

        ms_obj.swift_connection_initiate()

        objects_references = ms_obj.get_objects_references()

        old_objects_references = ms_obj.get_old_objects_references(objects_references, limit_date)

        ms_obj.delete_objects(old_objects_references)

    except KeyboardInterrupt:
        log.error('\nManual interruption !')

    finally:
        ms_obj.swift_connection_close()
        log.info(f'Process end')


PARSER = argparse.ArgumentParser()
PARSER.add_argument('-d', '--date', type=str,
                    help='oldest date allowed for attachments: yyyy-mm-dd[Thh:mm[:ss]]')
PARSER.add_argument('-n', '--dry-run', action='store_true',
                    help='show how many objects would be deleted')
PARSER.add_argument('-v', '--verbose', action='store_true',
                    help='run the script in verbose mode (print DEBUG messages)')
ARGS = PARSER.parse_args()

level = logging.DEBUG if ARGS.verbose else logging.INFO
manual = ARGS.dry_run or ARGS.date is not None

logger = common.setup_logging(level=level, simple=manual)

variables.max_del_errors = MAX_DELETE_ERRORS
variables.cli_args = ARGS
variables.logger = logger

run(variables)
