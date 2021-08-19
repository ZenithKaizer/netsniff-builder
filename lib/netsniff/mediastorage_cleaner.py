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
        old_date = datetime.now() - timedelta(days=31)
        return old_date.isoformat()


def run(ext_vars):
    ext_vars.logger.info(f'Process start')

    ms_obj = mediastorage.MediaStorage(ext_vars)

    oldest_limit = get_old_date_or_exit(arg_date=ext_vars.cli_args.date,
                                        error_logger=ext_vars.logger.error)

    ms_obj.swift_connection_initiate()

    objects_references = ms_obj.get_objects_references()

    old_objects_references = ms_obj.get_old_objects_references(objects_references, oldest_limit)

    ms_obj.delete_objects(old_objects_references)

    ext_vars.logger.info(f'Process end')


PARSER = argparse.ArgumentParser()
PARSER.add_argument('-d', '--date', type=str,
                    help='oldest date allowed for attachments: yyyy-mm-dd[Thh:mm[:ss]]')
PARSER.add_argument('-n', '--dry-run', action='store_true',
                    help='show how many objects would be deleted')
PARSER.add_argument('-v', '--verbose', action='store_true',
                    help='run the script in verbose mode (print DEBUG messages)')
ARGS = PARSER.parse_args()

logger = common.setup_logging(log_simple=ARGS.date != '',
                              log_level=logging.DEBUG if ARGS.verbose else logging.INFO)

variables.max_del_errors = MAX_DELETE_ERRORS
variables.cli_args = ARGS
variables.logger = logger

try:
    run(variables)

except KeyboardInterrupt:
    logger.error('\nManual interruption !')
