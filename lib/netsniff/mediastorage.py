#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
    Custom library class to interact with MediaStorage from Netsniff Python scripts

    - by design, exceptions are caught to go easy on the log
    - decorators allow operations to be attempted a given number of times
"""

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
    """

    Class Attributes
    - logger: imported logger

    Attributes
    - connection: Swift object
    - connection_parameters: MediaStorage connection parameters
    - container_name: Netsniff data container name
    - max_del_errors: no more deletion operations if that many errors occur
    - os_options: domain and project related parameters
    - variables: imported variables

    Parameters
    - variables: constants and CLI parameters
    """

    logger = None

    def __init__(self, variables):
        self.connection = None
        self.logger = variables.logger
        self.container_name = variables.CONTAINER_NAME
        self.max_del_errors = variables.max_del_errors
        self.variables = variables
        self.os_options = {'user_domain_name': variables.KEYSTONE_USER_DOMAIN_NAME,
                           'project_domain_name': variables.KEYSTONE_PROJECT_DOMAIN_NAME,
                           'project_name': variables.KEYSTONE_PROJECT_NAME,
                           'endpoint_type': variables.CONST_OS_ENDPOINT_TYPE}
        self.connection_parameters = {'authurl': variables.KEYSTONE_AUTH_URL,
                                      'user': variables.KEYSTONE_USERNAME,
                                      'key': variables.KEYSTONE_PASSWORD,
                                      'auth_version': variables.KEYSTONE_AUTH_VERSION,
                                      'os_options': self.os_options,
                                      'timeout': 5,
                                      'retries': 3,
                                      'insecure': True}
        MediaStorage.logger = self.logger if self.logger else common.setup_logging()

    # temporary encapsulated log.info with writing to custom user file
    def extended_log_info(self, message):
        self.logger.info(message)
        try:
            self.variables.del_file.write(message + '\n')
        except IOError:
            pass

    # TODO: put in another class, with its own 'logger' variable
    # ...but then, pass the necessary methods or variables as parameters
    def attempt_or_wait_socket(attempts, delay, failure_message):
        """ decorator for operations that may need retries
            = will try up to "attempts" times, pausing "delay" seconds before each retry
            - exceptions are caught to avoid filling the logs with irrelevant

        :param attempts: total number of times to try the operation
        :param delay: number of seconds before retrying
        :param failure_message: dedicated message on failure here
        """
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
    # ...but then, pass the necessary methods or variables as parameters
    def delete_or_wait_socket(attempts):
        """ decorator for deletion operations with retries
            = will try up to "attempts" times
            - delay appear to be redundant for Swift deletions
            - exceptions are caught to avoid filling the logs with irrelevant

        :param attempts: total number of times to try the operation
        """
        def decorator(func):
            def wrapper(*args):
                last_error = ''
                for attempt in range(attempts):
                    try:
                        return func(*args)
                    except ClientException as error:
                        print(f'\nClientException\n{error}\n')
                        last_error = error
                    except socket.timeout:
                        print(f'\nSocket timeout\n')
                else:
                    if last_error:
                        MediaStorage.logger.debug(f'error (last after {attempts} attempts): {last_error}')
                    return False
            return wrapper
        return decorator

    @attempt_or_wait_socket(15, 1, 'Swift client connection error')
    def swift_connection_initiate(self):
        """ Initiate Swift connection """
        # Connect to Media Storage
        self.connection = Connection(**self.connection_parameters)

    def swift_connection_close(self):
        """ Close Swift connection and ignore eventual closing exception """
        try:
            self.connection.close()
        except (ClientException, socket.timeout):
            pass

    @attempt_or_wait_socket(15, 1, 'Swift client error - account could not be loaded')
    def get_account(self):
        """ Fetch connection information """
        return self.connection.get_account()

    @attempt_or_wait_socket(15, 1, 'Swift client error - objects could not be loaded')
    def get_container(self, name):
        """ Fetch a named container information """
        return self.connection.get_container(name, full_listing=True)

    def get_objects_references(self):
        """ Retrieve container contents data """
        resp_headers, all_containers = self.get_account()
        containers_found = [container for container in all_containers
                            if container['name'] == self.container_name]
        if containers_found:
            self.extended_log_info('Loading objects references from container...')
            start = time.time()
            container_data = self.get_container(self.container_name)
            objects_count = container_data[0]['x-container-object-count']
            elapsed = time.time() - start
            if elapsed >= 2:
                self.extended_log_info(f'( {elapsed:.1f} seconds )')
            self.extended_log_info(f'Objects in container: {objects_count}')
            return container_data[1]
        else:
            self.extended_log_info(f'Container {self.container_name} does not exist.')
            self.swift_connection_close()
            sys.exit()

    def get_old_objects_references(self, objects_references, limit_date):
        """ Select container contents considered too old (for eventual deletion)
            because older than provided limit date

        :param objects_references: references to container contents
        :param limit_date: date considered the limit
        :return: list of selected "old" objects
        """
        old_obj_refs = [ref for ref in objects_references if ref['last_modified'] < limit_date]
        if old_obj_refs:
            return old_obj_refs
        else:
            self.extended_log_info(f'No object older than {self.variables.max_days} days.')
            self.swift_connection_close()
            sys.exit()

    @delete_or_wait_socket(5, 1)
    def delete(self, object_name):
        """ Delete a named object from a given container
            - True is used as success flag
        """
        self.connection.delete_object(self.container_name, object_name)
        return True

    def delete_objects_real(self, refs):
        """ Delete container contents with references provided from Swift container
            - process is aborted if the number of deletion errors reaches "max_del_errors"

        :param refs: list of Swift objects references
        """
        refs_count = len(refs)
        self.extended_log_info(f'Objects to delete: {refs_count}')
        # feedback variables
        deleted_count, data_amount, errors, curr_time = 0, 0, 0, ''
        start_time = time.time()
        rate_str = ''
        for number, curr_obj in enumerate(refs, start=1):
            obj_name = curr_obj['name']
            modified = curr_obj['last_modified']
            if self.variables.manual:
                now = time.strftime("%T")
                if curr_time != now:
                    curr_time = now
                    time_str = now
                else:
                    time_str = '        '
                print(f'           {time_str}  '
                      f'{number:5}  {obj_name} - {common.posix_to_date(modified)}'
                      f'\n  {number} / {refs_count}{rate_str}\r', end='')
            else:
                self.extended_log_info(f'deletion of object {number:5} /{refs_count}:'
                                       f' {obj_name} - {common.posix_to_date(modified)}')
            success = self.delete(obj_name)
            if success:
                deleted_count += 1
                data_amount += curr_obj['bytes']
                if self.variables.manual:
                    duration = time.time() - start_time
                    if duration > 10:
                        rate = deleted_count / duration
                        rate_str = f'  ( {rate:.1f}/s )' if rate < 10 else \
                                   f'  ( {rate:.0f}/s )'
            else:
                if errors >= self.max_del_errors:
                    break
                errors += 1
        if not self.variables.manual:
            duration = time.time() - start_time
        # errors feedback
        if errors:
            self.logger.error(f'Aborted after over {self.max_del_errors} deletion errors !'
                              if errors > self.max_del_errors else
                              f'Deletion errors: {errors}')
        # regular feedback
        self.extended_log_info(f'{deleted_count} objects deleted' if deleted_count else f'No object deleted')
        if duration > 5 and not self.variables.manual:
            self.extended_log_info(f'Time elapsed: {common.pretty_duration(duration)}')
            if deleted_count:
                rate = deleted_count / duration
                self.extended_log_info(f'Rate: {rate:.1f}/second' if rate < 10 else
                                       f'Rate: {rate:.0f}/second')
        if data_amount:
            self.extended_log_info(f'Data amount: {common.human_bytes(data_amount)} bytes')

    def delete_objects_simulation(self, refs):
        """ Show which container contents would be deleted from Swift container
            among provided references

        :param refs: list of objects references
        """
        # count of files by date (just the 5 oldest and the 5 most recent)
        files_by_date = {}
        for r in refs:
            d = r['last_modified'][:10]
            try:
                files_by_date[d] += 1
            except KeyError:
                files_by_date[d] = 1
        # some logic to limit the size of feedback
        rows = [f'    {d}: {n:5}'
                for i, (d, n) in enumerate(files_by_date.items())
                if i < 5 or i > len(files_by_date) - 6]
        if len(files_by_date) > 10:
            rows.insert(5, '     [ ... ]')
        print('\n'.join(rows))
        first_name, first_date = refs[0]['name'], refs[0]['last_modified']
        last_name, last_date = refs[-1]['name'], refs[-1]['last_modified']
        self.logger.info(f'Objects to delete: {len(refs)}\n'
                         f'from  "{first_name}" {common.posix_to_date(first_date)}  ({first_date})\n'
                         f'up to "{last_name}" {common.posix_to_date(last_date)}  ({last_date})')

    def delete_objects(self, refs):
        """ Delete container contents with references provided from Swift container
            or show what would be deleted if dry_run flag in on
            - oldest objects are deleted first

        :param refs: list of Swift container contents references
        """
        if refs:
            refs.sort(key=lambda obj: obj['last_modified'])
            if self.variables.cli_args.dry_run:
                self.delete_objects_simulation(refs)
            else:
                self.delete_objects_real(refs)
        self.swift_connection_close()
