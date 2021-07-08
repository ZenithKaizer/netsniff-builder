#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import copy
import hashlib
import json
import logging
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import uuid

from collections import OrderedDict
from colorlog import ColoredFormatter
from pathlib import Path
from swiftclient.client import Connection

# LIB_PATH = "/usr/lib/python2.7/dist-packages"
# sys.path.append(LIB_PATH)
# import mon_xymon_lib

# adding path /etc/netsniff to import variables
sys.path.append('/etc/netsniff/')
import utils      # noqa: E402
import variables  # noqa: E402


logger = setup_logging(logging.INFO)


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

    _authurl = variables.KEYSTONE_AUTH_URL
    _auth_version = variables.KEYSTONE_AUTH_VERSION
    _user = variables.KEYSTONE_USERNAME
    _key = variables.KEYSTONE_PASSWORD
    _os_options = {
        'user_domain_name': variables.KEYSTONE_USER_DOMAIN_NAME,
        'project_domain_name': variables.KEYSTONE_PROJECT_DOMAIN_NAME,
        'project_name': variables.KEYSTONE_PROJECT_NAME,
        'endpoint_type': variables.CONST_OS_ENDPOINT_TYPE
    }

    # try:
    if 1:
        conn = Connection(
            authurl=_authurl,
            user=_user,
            key=_key,
            os_options=_os_options,
            auth_version=_auth_version,
            insecure=True,
            timeout=5,
            retries=3
        )

        resp_headers, containers = conn.get_account()
        print("Response headers: %s" % resp_headers)
        for container in containers:
            print(container)
        # for data in conn.get_container("netsniff-attachments")[1]:
        #     print('{0}\t{1}\t{2}'.format(
        #         data['name'], data['bytes'], data['last_modified']))

        # # Create Container if needed
        # account_dict = conn.get_account()[1]
        # if not variables.CONTAINER_NAME in account_dict[0]['name']:
        #     logger.debug(f"Container {variables.CONTAINER_NAME} does not exist creating container")
        #     # conn.put_container(variables.CONTAINER_NAME, {'X-Container-Read': '.r:*,.rlistings'})
        #     logger.debug(f"Container {variables.CONTAINER_NAME} has been created")
        # return conn

    # except:
    #     raise


def delete_attachment(swift_conn):
    obj = 'local_object.txt'
    container = 'new-container'
    logger.info(f"Delete file: {file_digest}")
    try:
        swift_conn.get_object(container, obj)
    except Exception as error:
        logger.exception(error)


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument("-v", "--verbose",
                        help="run the script in verbose mode (print DEBUG messages)", action="store_false")
    ARGS = PARSER.parse_args()

    with swift_init_conn() as swift_conn:
        print(type(swift_conn))
        # delete_attachment(swift_conn)
