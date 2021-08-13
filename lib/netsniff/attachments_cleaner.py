#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import logging
import re
import socket
import sys
import time
import urllib3

from colorlog import ColoredFormatter
from datetime import datetime, timedelta
from swiftclient.client import Connection
from swiftclient.exceptions import ClientException

# adding path /etc/netsniff to import variables
sys.path.append('/etc/netsniff/')
import variables  # noqa: E402


DATETIME_REGEXP = r'^20\d\d-[01]\d(-[0-3]\d(T[0-2]\d:[0-5]\d(:[0-5]\d)?)?)?$'
MAX_DELETE_ERRORS = 1000

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def pretty_date(date_string):
    return datetime.strptime(date_string[:19], '%Y-%m-%dT%H:%M:%S').strftime('%b %_d %T')


def pretty_duration(secs):
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
        if string:
            string += f' {secs:02}s'
        else:
            string = f'{secs} seconds'
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
    logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
        color_format,
        datefmt=date_format,
        reset=True,
        log_colors={'DEBUG': 'cyan', 'INFO': 'green', 'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'red'}
    ))
    set_up_logger = logging.getLogger(__name__)
    set_up_logger.setLevel(log_level)
    return set_up_logger


def attempt_or_wait_socket(attempts, delay, failure_message):
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
                    logger.error(f'{failure_message} ({attempts} attempts).')
                    logger.exception(last_error, exc_info=logger.getEffectiveLevel() == logging.DEBUG)
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
def get_connection(connection_data):
    # Create session
    return Connection(**connection_data)


def swift_connection_initiate():
    # Connect to Media Storage
    authurl = variables.KEYSTONE_AUTH_URL
    auth_version = variables.KEYSTONE_AUTH_VERSION
    user = variables.KEYSTONE_USERNAME
    key = variables.KEYSTONE_PASSWORD
    os_options = {'user_domain_name': variables.KEYSTONE_USER_DOMAIN_NAME,
                  'project_domain_name': variables.KEYSTONE_PROJECT_DOMAIN_NAME,
                  'project_name': variables.KEYSTONE_PROJECT_NAME,
                  'endpoint_type': variables.CONST_OS_ENDPOINT_TYPE}
    connection_data = {'authurl': authurl,
                       'user': user,
                       'key': key,
                       'os_options': os_options,
                       'auth_version': auth_version,
                       'insecure': True,
                       'timeout': 5,
                       'retries': 3}
    return get_connection(connection_data)


def swift_connection_close(connection):
    try:
        connection.close()
    except (ClientException, socket.timeout):
        pass


def get_old_date(args_date):
    if args_date:
        if re.match(DATETIME_REGEXP, args_date):
            return args_date
        else:
            logger.error('Incorrect date provided')
            sys.exit()
    else:
        old_date = datetime.now() - timedelta(days=31)
        return old_date.isoformat()


@attempt_or_wait_socket(15, 1, 'Swift client error - account could not be loaded')
def get_account(swift_conn):
    return swift_conn.get_account()


@attempt_or_wait_socket(15, 1, 'Swift client error - objects could not be loaded')
def get_container(swift_conn, name):
    return swift_conn.get_container(name)


def get_objects(swift_conn, name):
    resp_headers, all_containers = get_account(swift_conn)
    containers_found = [container for container in all_containers
                        if container['name'] == name]
    if containers_found:
        container_data = get_container(swift_conn, name)
        objects_count = container_data[0]['x-container-object-count']
        logger.info(f'Objects in container: {objects_count}')
        return container_data[1]
    else:
        logger.info(f'Container {name} does not exist.')
        swift_connection_close(swift_conn)
        sys.exit()


def get_old_objects(swift_conn, all_objects, oldest_allowed):
    old_objects = [obj for obj in all_objects if obj['last_modified'] < oldest_allowed]
    if old_objects:
        return old_objects
    else:
        logger.info(f'No object older enough.')
        swift_connection_close(swift_conn)
        sys.exit()


@delete_or_wait_socket(5, .1)
def delete(swift_conn, container_name, object_name):
    swift_conn.delete_object(container_name, object_name)
    return True


def delete_objects(swift_conn, container_name, old_objects, max_del_errors, run_mode='dry_run'):
    if old_objects:
        old_objects.sort(key=lambda obj: obj['last_modified'])
        if run_mode != 'dry_run':
            logger.info(f'Objects to delete: {len(old_objects)}')
            deleted_count = 0
            data_amount = 0
            errors = 0
            start_time = datetime.now()
            for number, curr_obj in enumerate(old_objects, start=1):
                obj_name = curr_obj['name']
                modified = curr_obj['last_modified']
                if run_mode:
                    print(f'           {time.strftime("%T")}  {number:5}  {pretty_date(modified)}  {obj_name}')
                else:
                    logger.debug(f'deletion of object {number:5}: {obj_name} - {pretty_date}  ({modified})')
                success = delete(swift_conn, container_name, obj_name)
                if success:
                    deleted_count += 1
                    data_amount += curr_obj['bytes']
                else:
                    if errors >= max_del_errors:
                        break
                    errors += 1
            duration = datetime.now() - start_time
            if deleted_count:
                logger.info(f'{deleted_count} objects deleted')
                logger.info(f'Data amount: {human_bytes(data_amount)} bytes')
            else:
                logger.info(f'No object deleted')
            if duration.seconds:
                logger.info(f'Elapsed time: {pretty_duration(duration.seconds)}')
            if errors:
                if errors > max_del_errors:
                    logger.error(f'Aborted after over {max_del_errors} deletion errors !')
                else:
                    logger.error(f'Deletion errors: {errors}')
        else:
            first_name, first_date = old_objects[0]['name'], old_objects[0]['last_modified']
            last_name, last_date = old_objects[-1]['name'], old_objects[-1]['last_modified']
            logger.info(f'Objects to delete: {len(old_objects)}\n'
                        f'from  "{first_name}" {pretty_date(first_date)}  ({first_date})\n'
                        f'up to "{last_name}" {pretty_date(last_date)}  ({last_date})')
        swift_connection_close(swift_conn)


if __name__ != '__main__':

    logger = setup_logging(log_simple=False,
                           log_level=logging.INFO)

else:

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('-d', '--date', type=str,
                        help='oldest date allowed for attachments: yyyy-mm-dd[Thh:mm[:ss]]')
    PARSER.add_argument('-n', '--dry-run', action='store_true',
                        help='show how many objects would be deleted')
    PARSER.add_argument('-v', '--verbose', action='store_true',
                        help='run the script in verbose mode (print DEBUG messages)')
    ARGS = PARSER.parse_args()

    run_mode = 'dry_run' if ARGS.dry_run else \
               'manual' if ARGS.date else ''

    logger = setup_logging(log_simple=ARGS.date != '',
                           log_level=logging.DEBUG if ARGS.verbose else logging.INFO)

    oldest_limit = get_old_date(ARGS.date)

    swift_connection = swift_connection_initiate()

    container_objects = get_objects(swift_connection, variables.CONTAINER_NAME)

    old_objects = get_old_objects(swift_connection, container_objects, oldest_limit)

    delete_objects(swift_conn=swift_connection,
                   container_name=variables.CONTAINER_NAME,
                   old_objects=old_objects,
                   max_del_errors=MAX_DELETE_ERRORS,
                   run_mode=run_mode)
