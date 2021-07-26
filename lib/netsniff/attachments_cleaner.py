#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import logging
import socket
import sys
import traceback

from datetime import datetime, timedelta
from colorlog import ColoredFormatter
from swiftclient.client import Connection
from swiftclient.exceptions import ClientException

# adding path /etc/netsniff to import variables
sys.path.append('/etc/netsniff/')
import utils      # noqa: E402
import variables  # noqa: E402


def get_old_date():
    old_date = datetime.now() - timedelta(days=31)
    return old_date.isoformat()


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
                        'CRITICAL': 'red',}
        ))
    set_up_logger = logging.getLogger(__name__)
    set_up_logger.setLevel(log_level)
    return set_up_logger


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
                  'endpoint_type': variables.CONST_OS_ENDPOINT_TYPE
                  }
    try:
        return Connection(authurl=authurl,
                          user=user,
                          key=key,
                          os_options=os_options,
                          auth_version=auth_version,
                          insecure=True,
                          timeout=5,
                          retries=3
                          )
    except (ClientException, socket.timeout) as error:
        logger.error('Swift client connection error')
        logger.exception(error)
        raise


def get_objects(swift_conn):
    try:
        resp_headers, all_containers = swift_conn.get_account()
        # import json
        # print('Response headers:', json.dumps(resp_headers, indent=4))
        # for num, container in enumerate(all_containers, start=1):
        #     print(f'\ncontainer #{num}:', json.dumps(container, indent=4))
        containers_found = [container for container in all_containers if container['name'] == variables.CONTAINER_NAME]
        if not containers_found:
            logger.debug(f'Container {variables.CONTAINER_NAME} does not exist - Nothing to do')
            return []
        return swift_conn.get_container(variables.CONTAINER_NAME)[1]
    except (ClientException, socket.timeout) as error:
        logger.error('Swift client operation error at getting objects stage')
        logger.exception(error)
        raise


def delete_old(all_objects, old_date, swift_conn):
    try:
        # for num, obj in enumerate(all_objects[:5], start=1):
        #     print(f'\nobject #{num}:', json.dumps(obj, indent=4))
        for object in all_objects[:5]:
            modified = object['last_modified']
            stamp = datetime.fromisoformat(modified)
            recent = '' if stamp > old_date else '  recent'
            print(f'{num:3}: {stamp}{recent}')
        # all_modifs = [obj['last_modified'] for obj in all_objects]
        # for num, modified in enumerate(all_modifs[:15]):
        #     datetime.fromisoformat(stamp)
        #     print(f'')
    except (ClientException, socket.timeout) as error:
        logger.error('Swift client operation error at deletion stage')
        logger.exception(error)
        raise


logger = setup_logging(logging.INFO)


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('-v', '--verbose', action='store_false',
                        help='run the script in verbose mode (print DEBUG messages)')
    ARGS = PARSER.parse_args()

    swift_connection = swift_init_conn()

    all_objects = get_objects(swift_connection)

    old_date = get_old_date()

    delete_old(all_objects, old_date, swift_connection)
