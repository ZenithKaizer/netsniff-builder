#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import socket
import sys
import time
import urllib3

from swiftclient.client import Connection
from swiftclient.exceptions import ClientException

# adding path /etc/netsniff to import common functions
sys.path.append('/etc/netsniff/')
import common    # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MediaStorage:

    logger = None

    def __init__(self, variables):
        self.connection = None
        self.logger = variables.logger
        self.container_name = variables.CONTAINER_NAME
        self.max_del_errors = variables.max_del_errors
        self.cli_args = variables.cli_args
        self.os_options = {'user_domain_name': variables.KEYSTONE_USER_DOMAIN_NAME,
                           'project_domain_name': variables.KEYSTONE_PROJECT_DOMAIN_NAME,
                           'project_name': variables.KEYSTONE_PROJECT_NAME,
                           'endpoint_type': variables.CONST_OS_ENDPOINT_TYPE}
        self.connection_data = {'authurl': variables.KEYSTONE_AUTH_URL,
                                'user': variables.KEYSTONE_USERNAME,
                                'key': variables.KEYSTONE_PASSWORD,
                                'auth_version': variables.KEYSTONE_AUTH_VERSION,
                                'os_options': self.os_options,
                                'timeout': 5,
                                'retries': 3,
                                'insecure': True}
        MediaStorage.logger = self.logger if self.logger else \
            common.setup_logging(log_simple=False,
                                 log_level=logging.INFO)

    # TODO: put in another class, with its own 'logger' variable
    def attempt_or_wait_socket(attempts, delay, failure_message):
        def decorator(func):
            def wrapper(*args):
                last_error = ''
                for attempt in range(attempts):
                    try:
                        return func(*args)
                    except ClientException as error:
                        last_error = error
                        time.sleep(delay)
                    except socket.timeout:
                        time.sleep(delay)
                else:
                    if last_error:
                        exc_info = MediaStorage.logger.getEffectiveLevel() == logging.DEBUG
                        MediaStorage.logger.error(f'{failure_message} ({attempts} attempts).')
                        MediaStorage.logger.exception(last_error, exc_info=exc_info)
                    else:
                        MediaStorage.logger.error(f'Socket always in timeout ({attempts} attempts).')
                    sys.exit()
            return wrapper
        return decorator

    # TODO: put in another class, with its own 'logger' variable
    def delete_or_wait_socket(attempts, delay):
        def decorator(func):
            def wrapper(*args):
                last_error = ''
                for attempt in range(attempts):
                    try:
                        return func(*args)
                    except ClientException as error:
                        print(f'\nClientException\n{error}\n')
                        last_error = error
                        # time.sleep(delay)
                    except socket.timeout:
                        print(f'\nSocket timeout\n')
                        # time.sleep(delay)
                else:
                    if last_error:
                        MediaStorage.logger.debug(f'error (last after {attempts} attempts): {last_error}')
                    return False
            return wrapper
        return decorator

    @attempt_or_wait_socket(15, 1, 'Swift client connection error')
    def swift_connection_initiate(self):
        # Connect to Media Storage
        self.connection = Connection(**self.connection_data)

    def swift_connection_close(self):
        try:
            self.connection.close()
        except (ClientException, socket.timeout):
            pass

    @attempt_or_wait_socket(15, 1, 'Swift client error - account could not be loaded')
    def get_account(self):
        return self.connection.get_account()

    @attempt_or_wait_socket(15, 1, 'Swift client error - objects could not be loaded')
    def get_container(self, name):
        return self.connection.get_container(name, full_listing=True)

    def get_objects_references(self):
        resp_headers, all_containers = self.get_account()
        containers_found = [container for container in all_containers
                            if container['name'] == self.container_name]
        if containers_found:
            self.logger.info('Loading objects references from container...')
            start = time.time()
            container_data = self.get_container(self.container_name)
            objects_count = container_data[0]['x-container-object-count']
            self.logger.info(f'( {time.time() - start:.1f} seconds )')
            self.logger.info(f'Objects in container: {objects_count}')
            return container_data[1]
        else:
            self.logger.info(f'Container {self.container_name} does not exist.')
            self.swift_connection_close()
            sys.exit()

    def get_old_objects_references(self, objects_references, oldest_limit):
        old_obj_refs = [ref for ref in objects_references if ref['last_modified'] < oldest_limit]
        if old_obj_refs:
            return old_obj_refs
        else:
            self.logger.info(f'No object older enough.')
            self.swift_connection_close()
            sys.exit()

    @delete_or_wait_socket(5, 1)
    def delete(self, object_name):
        self.connection.delete_object(self.container_name, object_name)
        return True

    def delete_objects_real(self, refs):
        refs_count = len(refs)
        self.logger.info(f'Objects to delete: {refs_count}')
        # feedback variables
        deleted_count, data_amount, errors, curr_time = 0, 0, 0, ''
        start_time = time.time()
        for number, curr_obj in enumerate(refs, start=1):
            obj_name = curr_obj['name']
            modified = curr_obj['last_modified']
            if self.cli_args.date:
                now = time.strftime("%T")
                if curr_time != now:
                    curr_time = now
                    time_str = now
                else:
                    time_str = '        '
                print(f'           {time_str}  {number:5}  {obj_name}  {common.pretty_date(modified)}'
                      f'\n  {number} / {refs_count}\r', end='')
            else:
                self.logger.debug(f'deletion of object {number:5}: {obj_name} - {common.pretty_date(modified)}')
            success = self.delete(obj_name)
            if success:
                deleted_count += 1
                data_amount += curr_obj['bytes']
            else:
                if errors >= self.max_del_errors:
                    break
                errors += 1
        duration = time.time() - start_time
        # errors feedback
        if errors:
            self.logger.error(f'Aborted after over {self.max_del_errors} deletion errors !'
                              if errors > self.max_del_errors else
                              f'Deletion errors: {errors}')
        # regular feedback
        self.logger.info(f'{deleted_count} objects deleted' if deleted_count else
                         f'No object deleted')
        if duration:
            self.logger.info(f'Deletion time: {common.pretty_duration(duration)}')
            if deleted_count:
                rate = deleted_count / duration
                self.logger.info(f'Rate: {rate:.1f}/second' if rate < 10 else
                                 f'Rate: {rate:.0f}/second')
        if data_amount:
            self.logger.info(f'Data amount: {common.human_bytes(data_amount)} bytes')

    def delete_objects_simulation(self, refs):
        # count of files by date (just the 5 oldest and the 5 most recent)
        files_by_date = {}
        for r in refs:
            stop = 16 if self.cli_args.date else 10
            d = r['last_modified'][:stop]
            try:
                files_by_date[d] += 1
            except KeyError:
                files_by_date[d] = 1
        if not self.cli_args.date or len(files_by_date) < 11:
            rows = [f'    {d}: {n:5}' for i, (d, n) in enumerate(files_by_date.items())]
        else:
            rows = [f'    {d}: {n:5}' for i, (d, n) in enumerate(files_by_date.items())
                    if i < 5 or i > len(files_by_date) - 6]
            if len(files_by_date) > 10:
                rows.insert(5, '     [ ... ]')
        print('\n'.join(rows))
        first_name, first_date = refs[0]['name'], refs[0]['last_modified']
        last_name, last_date = refs[-1]['name'], refs[-1]['last_modified']
        self.logger.info(f'Objects to delete: {len(refs)}\n'
                         f'from  "{first_name}" {common.pretty_date(first_date)}  ({first_date})\n'
                         f'up to "{last_name}" {common.pretty_date(last_date)}  ({last_date})')

    def delete_objects(self, refs):
        if refs:
            refs.sort(key=lambda obj: obj['last_modified'])
            if self.cli_args.dry_run:
                self.delete_objects_simulation(refs)
            else:
                self.delete_objects_real(refs)
        self.swift_connection_close()
