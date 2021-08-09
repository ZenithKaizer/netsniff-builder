#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import logging
import re
import socket
import sys
import time
import urllib3

from datetime import datetime, timedelta
from colorlog import ColoredFormatter
from swiftclient.client import Connection
from swiftclient.exceptions import ClientException
# from swiftclient.service import SwiftService

# adding path /etc/netsniff to import variables
sys.path.append('/etc/netsniff/')
import variables  # noqa: E402


DATETIME_REGEXP = r'^20\d\d-[01]\d(-[0-3]\d(T[0-2]\d:[0-5]\d(:[0-5]\d)?)?)?$'
MAX_DELETE_ERRORS = 1000

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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


def attempt_or_wait_socket(attempts, delay, failure_message, connection=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = ''
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except ClientException as error:
                    last_error = error
                    time.sleep(delay)
                except socket.timeout:
                    time.sleep(delay)
            else:
                if connection:
                    connection.close()
                if last_error:
                    logger.error(f'{failure_message} ({attempts} attempts).')
                    logger.exception(last_error)
                else:
                    logger.error(f'Socket always in timeout ({attempts} attempts).')
                sys.exit()
        return wrapper
    return decorator


def delete_or_wait_socket(attempts, delay):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = ''
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except ClientException as error:
                    last_error = error
                    time.sleep(delay)
                except socket.timeout:
                    time.sleep(delay)
            else:
                if last_error:
                    logger.debug(f'error (last after {attempts} attempts): {last_error}')
                return False
        return wrapper
    return decorator


@attempt_or_wait_socket(15, 1, 'Swift client connection error')
def swift_initiate_connection():
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
    return Connection(authurl=authurl,
                      user=user,
                      key=key,
                      os_options=os_options,
                      auth_version=auth_version,
                      insecure=True,
                      timeout=5,
                      retries=3)


def pretty_date(date_string):
    return datetime.strptime(date_string[:19], '%Y-%m-%dT%H:%M:%S').strftime('%b %_d %T')


def get_old_date(args_date):
    if args_date:
        if not re.match(DATETIME_REGEXP, args_date):
            print('Date limit should be more sensible')
            sys.exit()
        return args_date
    else:
        old_date = datetime.now() - timedelta(days=31)
        return old_date.isoformat()


@attempt_or_wait_socket(15, 1, 'Swift client error - objects could not be loaded')
def get_objects(swift_conn):
    resp_headers, all_containers = swift_conn.get_account()
    containers_found = [container for container in all_containers
                        if container['name'] == variables.CONTAINER_NAME]
    if containers_found:
        return swift_conn.get_container(variables.CONTAINER_NAME)[1]
    else:
        logger.info(f'Container {variables.CONTAINER_NAME} does not exist - Will do nothing.')
        return None


@delete_or_wait_socket(5, .1)
def delete_object(swift_conn, curr_obj, number):
    obj_name = curr_obj['name']
    modified = curr_obj['last_modified']
    print(f'{number:5}  {pretty_date(modified)}  {obj_name}')
    logger.debug(f'deletion of object {number:5}: {obj_name} - {pretty_date}  ({modified})')
    swift_conn.delete_object(variables.CONTAINER_NAME, obj_name)
    return True


def delete_old_objects(swift_conn, all_objects, oldest_allowed, dry_run):
    old_objects = [obj for obj in all_objects if obj['last_modified'] < oldest_allowed]
    old_objects.sort(key=lambda obj: obj['last_modified'])
    if dry_run:
        first_name, first_date = old_objects[0]['name'], old_objects[0]['last_modified']
        last_name, last_date = old_objects[-1]['name'], old_objects[-1]['last_modified']
        print(f'Objects to delete: {len(old_objects)}\n'
              f'from  "{first_name}" {pretty_date(first_date)}  ({first_date})\n'
              f'up to "{last_name}" {pretty_date(last_date)}  ({last_date})')
    else:
        logger.info(f'Objects to delete: {len(old_objects)}')
        deleted_count = 0
        errors = 0
        for number, curr_obj in enumerate(old_objects[:10], start=1):
            success = delete_object(swift_conn, curr_obj, number)
            if success:
                deleted_count += 1
            else:
                if errors >= MAX_DELETE_ERRORS:
                    break
                errors += 1
        logger.info(f'Deleted objects: {deleted_count}')
        if errors:
            if errors > MAX_DELETE_ERRORS:
                logger.error(f'Aborted after over {MAX_DELETE_ERRORS} deletion errors !')
            else:
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

    # Dev
    if not ARGS.date:
        print('date!')
        sys.exit()

    logger = setup_logging(logging.DEBUG if ARGS.verbose else logging.INFO)

    swift_connection = swift_initiate_connection()

    container_objects = get_objects(swift_connection)

    oldest_limit = get_old_date(ARGS.date)

    delete_old_objects(swift_connection, container_objects, oldest_limit, ARGS.dry_run)

    swift_connection.close()
