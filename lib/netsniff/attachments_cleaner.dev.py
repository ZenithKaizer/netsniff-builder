#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import logging
import re
import socket
import sys
import time

from datetime import datetime, timedelta
from colorlog import ColoredFormatter
from swiftclient.client import Connection
from swiftclient.exceptions import ClientException
# from swiftclient.service import SwiftService

# adding path /etc/netsniff to import variables
sys.path.append('/etc/netsniff/')
import variables  # noqa: E402

DATETIME_REGEXP = r'^20\d\d-[01]\d(-[0-3]\d(T[0-2]\d:[0-5]\d(:[0-5]\d)?)?)?$'


def setup_logging(log_level=logging.INFO):
    """Set up the logging."""
    date_format = '%Y-%m-%d:%H:%M:%S'
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)s'
                               '[%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s',
                        datefmt=date_format,
                        level=log_level)
    color_format = '%(asctime)s,%(msecs)d %(log_color)s%(levelname)s%(reset)s' \
                   ' [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s'
    if color_format:
        logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
            color_format,
            datefmt=date_format,
            reset=True,
            log_colors={'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red'}
        ))
    set_up_logger = logging.getLogger(__name__)
    set_up_logger.setLevel(log_level)
    return set_up_logger


def attempt_or_wait_socket(attempts, secs, message):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except socket.timeout:
                    time.sleep(secs)
            else:
                logger.error(message)
                sys.exit()
        return wrapper
    return decorator


def delete_or_wait_socket(attempts, secs, message):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except socket.timeout:
                    time.sleep(secs)
            else:
                logger.debug(message)
                return False
        return wrapper
    return decorator


@attempt_or_wait_socket(15, 1, 'No Swift client connection after 15 attempts.')
def swift_init_conn():
    # Connect to Media Storage
    # Create session
    authurl = variables.KEYSTONE_AUTH_URL
    auth_version = variables.KEYSTONE_AUTH_VERSION
    user = variables.KEYSTONE_USERNAME
    key = variables.KEYSTONE_PASSWORD
    os_options = {'user_domain_name': variables.KEYSTONE_USER_DOMAIN_NAME,
                  'project_domain_name': variables.KEYSTONE_PROJECT_DOMAIN_NAME,
                  'project_name': variables.KEYSTONE_PROJECT_NAME,
                  'endpoint_type': variables.CONST_OS_ENDPOINT_TYPE}
    try:
        return Connection(authurl=authurl,
                          user=user,
                          key=key,
                          os_options=os_options,
                          auth_version=auth_version,
                          insecure=True,
                          timeout=5,
                          retries=3)
    except ClientException as error:
        logger.error('Swift client connection error')
        logger.exception(error)
        raise


def get_old_date(args_date):
    if args_date:
        if not re.match(DATETIME_REGEXP, args_date):
            print('Date limit should be more sensible')
            sys.exit()
        return args_date
    else:
        old_date = datetime.now() - timedelta(days=31)
        return old_date.isoformat()


@attempt_or_wait_socket(15, 1, 'Still no objects list after 15 attempts.')
def get_objects(swift_conn):
    try:
        resp_headers, all_containers = swift_conn.get_account()
        containers_found = [container for container in all_containers
                            if container['name'] == variables.CONTAINER_NAME]
        if containers_found:
            return swift_conn.get_container(variables.CONTAINER_NAME)[1]
        else:
            logger.info(f'Container {variables.CONTAINER_NAME} does not exist - Will do nothing.')
            return None
    except ClientException as error:
        logger.error('Swift client operation error at getting objects stage.')
        logger.exception(error)
        raise


@delete_or_wait_socket(5, .1, 'Object not deleted after 5 attempts.')
def delete_object(current_object, swift_conn, number):
    try:
        name = current_object['name']
        modified = current_object['last_modified']
        print(f'{number:5}: {modified}')
        logger.debug(f"deletion of object {number:5}: {name} with timestamp '{modified}'")
    except ClientException as error:
        logger.debug(error)
        return False
    else:
        return True


def delete_old_objects(swift_conn, all_objects, oldest_allowed, dry_run):
    old_objects = [obj for obj in all_objects if obj['last_modified'] < oldest_allowed]
    if dry_run:
        sorted_dates = sorted([obj['last_modified'] for obj in all_objects])
        print(f"Objects to delete: {len(old_objects)}\n"
              f"from {sorted_dates[0]}\nup to {sorted_dates[-1]}")
    else:
        deleted_count = 0
        errors = 0
        for number, obj in enumerate(old_objects[:10], start=1):
            success = delete_object(obj, swift_conn, number)
            if success:
                deleted_count += 1
            else:
                errors += 1
        logger.info(f'Deleted objects: {deleted_count}')
        if errors:
            logger.error(f'Deletion errors: {errors}')


if __name__ != '__main__':

    logger = setup_logging(logging.INFO)

else:

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('-d', '--date', type=str,
                        help='oldest date allowed for attachments: yyyy-mm-dd[Thh:mm[:ss]]')
    PARSER.add_argument('-n', '--dry-run', action='store_true',
                        help='show how many objects would be deleted')
    PARSER.add_argument('-v', '--verbose', action='store_true',
                        help='run the script in verbose mode (print DEBUG messages)')
    ARGS = PARSER.parse_args()

    logger = setup_logging(logging.DEBUG if ARGS.verbose else logging.INFO)

    swift_connection = swift_init_conn()

    container_objects = get_objects(swift_connection)

    oldest_limit = get_old_date(ARGS.date)

    delete_old_objects(swift_connection, container_objects, oldest_limit, ARGS.dry_run)
