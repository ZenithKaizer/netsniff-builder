#!/usr/bin/python3.6
#-*- coding: utf-8 -*-
import sys
# On ajoute /etc/netsniff pour importer les variables
sys.path.append('/etc/netsniff/')
from variables import *
import utils as u
import os
import time
import json
from pathlib import Path
from collections import OrderedDict
import hashlib
import uuid
import copy
import argparse
import subprocess
import queue
import logging
import threading
import traceback
from swiftclient.client import Connection
from haralyzer import HarParser, HarPage
from colorlog import ColoredFormatter
LIB_PATH = "/usr/lib/python2.7/dist-packages"
sys.path.append(LIB_PATH)
import mon_xymon_lib

def setup_logging(log_level=logging.INFO):
    """Set up the logging."""
    fmt = '%(asctime)s,%(msecs)d %(levelname)s [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s'
    datefmt = '%Y-%m-%d:%H:%M:%S'
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)s [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s',
                        datefmt=datefmt,
                        level=log_level)
    colorfmt = '%(asctime)s,%(msecs)d %(log_color)s%(levelname)s%(reset)s [%(filename)s:%(lineno)d] [Thread ID: %(thread)d] %(message)s'

    # Suppress overly verbose logs from libraries that aren't helpful
    # logging.getLogger('requests').setLevel(logging.WARNING)
    # logging.getLogger('urllib3').setLevel(logging.WARNING)
    # logging.getLogger('swiftclient.client').setLevel(logging.WARNING)

    if colorfmt:
        logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
            colorfmt,
            datefmt=datefmt,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        ))

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    return logger


logger = setup_logging(logging.INFO)

def get_har(CONST_PROGRAM, CONST_MAIN_SCRIPT,
            global_filename, global_config, check_conf, conf_unit, attachments, xymoncli, user_agent, url):

    dict_ = {
        r'://': "_",
        r'[\/, \#, \$]': "_",
    }

    url = conf_unit['urls']
    url_sub = u.MultiSub(dict_, url)

    thread_number = str(threading.current_thread().ident)

    conf_encoded = u.encode_conf(global_filename, conf_unit)
    url_har = f'{url_sub}_{thread_number}.har'

    url_sub = f'{url_sub}_{thread_number}'

    if ARGS.dryrun:

        print(f'{CONST_PROGRAM}, EXECUTE LE SCRIPT : \n{CONST_MAIN_SCRIPT}\n, AVEC LES PARAMÈTRES SUIVANTS : \n{conf_encoded}\n,{url}\n')
        print(f'HAR CENSÉ ÊTRE SAUVEGARDÉ : {url_har}\n')
        print(f'USER_AGENT : {user_agent}\n')

    thread_ID = str(threading.current_thread())

    logger.info(f'{CONST_PROGRAM} run : \n{CONST_MAIN_SCRIPT}\n with following parameters : \n{conf_encoded}\n, {url}')
    logger.info('Get Har started')

    try:
        subprocess.run(
            [CONST_PROGRAM, CONST_MAIN_SCRIPT, conf_encoded, url_sub, thread_number], universal_newlines=True, check=True, stderr=subprocess.PIPE)

    except subprocess.CalledProcessError as err:
        logger.exception('python catched error')
        logger.exception(f'Task skipped)')
        update_xymon_status(xymoncli, user_agent, url, nodejs_err=err.stderr)

    try:
        full_page = u.open_screenshot_attachment(url_sub, 'fullpage')
        full_page_date = u.get_screenshot_attachment_date(url_sub, 'fullpage')
        logger.debug(f'fullpage created : {full_page_date}')

        viewport = u.open_screenshot_attachment(url_sub, 'viewport')
        viewport_date = u.get_screenshot_attachment_date(url_sub, 'viewport')
        logger.debug(f'viewport created : {viewport_date}')

        har_file = Path(f'{ATTACHMENTS_DIR}/{url_har}')
        har_file_date = time.ctime(os.path.getctime(har_file))
        logger.debug(f'har created : {har_file_date}')
 
        har_read_file = u.read_har_file(har_file)

        logger.info('preprocess_har_parser started')
        preprocess_har_parser(har_read_file, har_file, har_file_date, full_page, viewport,
                  check_conf, global_config, full_page_date, viewport_date, attachments, xymoncli, user_agent, url, thread_number, url_sub)

    except Exception as err:
        logger.exception(f'Handling run-time error: {err}')
        raise

def preprocess_har_parser(har_read_file, har_file, har_file_date, full_page, viewport, check_conf, global_config, full_page_date, viewport_date, attachments, xymoncli, user_agent, url, thread_number, url_sub):

    har_parser = u.create_har_object(har_file)
    
    #for page in har_parser.pages:
    for page in har_parser.pages:
        if page:
            if 'pageTimings' in dir(page):
                if any(page.pageTimings.keys()):
                    logger.debug(f'PAGE: {page}')
                    har_page_id = page.page_id
                    har_parser_page = u.create_page_har_object(har_file, har_page_id)

                    logger.info(f'get_parser_har started')
                    get_parser_har(har_read_file, har_file, har_parser_page, page, har_parser,
                                full_page, viewport, check_conf, global_config, har_file_date, full_page_date, viewport_date, attachments, xymoncli, user_agent, url, thread_number, url_sub)


def get_parser_har(har_read_file, har_file, har_parser_page, page, har_parser,
                   full_page, viewport, check_conf, global_config, har_file_date, full_page_date, viewport_date, attachments, xymoncli, user_agent, url, thread_number, url_sub):

    # Tests with HAR only
    mudr = u.match_url_har(page, check_conf)
    gscfhdr = u.get_status_code_from_har(page, check_conf)

    ttfbdr = u.get_ttfb(page, check_conf)
    mhcdr = u.match_headers_cookies(page, check_conf)
    gdrurd = u.get_duplicate_request_urls(page, check_conf)

    # Create Tree from HAR
    #current_iteration = u.preprocess_tree(page, check_conf)

    #logger.debug('create Tree started')
    #tree = u.create_recurstree(check_conf, page, current_iteration)
    #logger.debug('create Tree stopped')

    # Use Tree for tests
    #gscftdr = u.get_status_code_from_tree(page, tree, check_conf)
    #gnntdr = u.get_nested_number_tags(check_conf, tree)
    #glftdr = u.get_load_from_tree(page, check_conf, tree)

    # Tests with HAR only
    glfhdr = u.get_load_from_har(page, check_conf)
    glfhwldr = u.get_load_from_har_without_list(page, check_conf)
    grbtdr = u.get_response_body_text(page, check_conf)

    #print(glfhwldr)

    # Create nodes for graph
    #nodes = u.preprocess_graph(tree, check_conf)

    # Check Parents from url using nodes
    #gpudr = u.get_parents_url(check_conf, nodes)

    # Create Graph
    #logger.debug('create Graph started')
    #hierarchical_tags_graph = u.create_graph(nodes, thread_number)
    #logger.debug('create Graph stopped')

    # Create objects for xymon
    #hierarchical_tags_graph = u.open_graph_attachment(thread_number)
    #hierarchical_tags_graph_date = u.get_graph_attachment_date(thread_number)

    # Curl check bad certificate
    gbcdr = u.get_bad_certificates(page, check_conf)

    # List of all check results
    logger.debug(f"create list with all check results")
    checks_results_list = [
    mudr, ttfbdr, mhcdr, gscfhdr, glfhdr, glfhwldr, gbcdr, grbtdr
    ]

    logger.debug(f"Check if check results is None")
    nested_dict = u.get_not_none_check_results(checks_results_list)

    # List of all objects must be save in MediaStorage

    logger.info(f"create list with all Mediastorage objects")

    objects = [
                        {'digest_name': 'screenshot_viewport_file_digest',
                        'object_name': viewport,
                        'object_type': "image/png",
                        'label': f'Screenshot viewport created in {viewport_date}'},

                        {'digest_name': 'screenshot_full_file_digest',
                        'object_name': full_page,
                        'object_type': "image/png",
                        'label': f'Screenshot fullpage created in {full_page_date}'},

                        {'digest_name': 'har_file_digest',
                        'object_name': har_read_file,
                        'object_type': "application/json",
                        'label': f'HAR created in {har_file_date}'},

                        #{'digest_name': 'hierarchical_tags_graph_digest',
                        #'object_name': hierarchical_tags_graph,
                        #'object_type': "application/pdf",
                        #'label': f'hierarchical tags graph created in {hierarchical_tags_graph_date}'}
                        ]

    mediastorage_objects = u.get_not_none_mediastorage_objects(objects)

    preprocess_upload_attachments(nested_dict, mediastorage_objects, attachments, url, page, har_file_date, xymoncli, user_agent, thread_number, url_sub)


def preprocess_upload_attachments(nested_dict, mediastorage_objects, attachments, url, page, har_file_date, xymoncli, user_agent, thread_number, url_sub):

    # Upload attachments to MediaStorage
    # Non - Blocking action: we perform the tests anyway
    swift_conn = None
    try:
        swift_conn = swift_init_conn()
        url_prefix = swift_conn.get_auth()[0]

        for _list in mediastorage_objects:
            object_to_upload = None
            if _list['digest_name'] == 'har_file_digest':
                utf8_object_to_upload = json.dumps(_list['object_name']).encode("utf8")
                utf8_file_digest = upload_attachment(swift_conn, utf8_object_to_upload, _list['object_type'])
                attachments.append({'file_digest': utf8_file_digest, 'label': _list['label'], 'url_prefix': url_prefix})

            else:
                bytes_object_to_upload = bytes(_list['object_name'])
                bytes_file_digest = upload_attachment(swift_conn, bytes_object_to_upload, _list['object_type'])
                attachments.append({'file_digest': bytes_file_digest, 'label': _list['label'], 'url_prefix': url_prefix})

    except:
        raise
    finally:
        if swift_conn is not None:
            swift_conn.close()

    update_xymon_status(xymoncli, user_agent, url, attachments, thread_number, url_sub,
                        OrderedDict(sorted(nested_dict.items())))

    # disabled features : do not remove for the moment

    # print(har_parser_page.time_to_first_byte)
    #
    # print(har_parser_page.page_size_trans)
    # print(har_parser_page.css_size_trans)
    # print(har_parser_page.js_size_trans)
    # print(har_parser_page.image_size_trans)
    # print(har_parser_page.audio_size_trans)
    # print(har_parser_page.video_size_trans)
    # print("size in bytes (with all assets)")
    # print(har_parser_page.page_size)


def init_xymon_object(global_config):
    try:
        xymoncli = mon_xymon_lib.XymonLib()
        if ARGS.dryrun:
            print(xymoncli.hostname())
            print(xymoncli.service(CONST_ALERT_NAME))
            print(xymoncli.status("green"))
        else:
            xymon_host = u.replace_xymon_host(global_config)
            xymoncli.hostname(xymon_host)
            xymoncli.service(CONST_ALERT_NAME)
            # xymoncli.lifetime("30m")
            # print(xymoncli.lifetime())
            xymoncli.status("green")
            return xymoncli
    except:
        raise


def swift_init_conn():
    # Connect to Media Storage
    # Create session

    try:
        _authurl = KEYSTONE_AUTH_URL
        _auth_version = KEYSTONE_AUTH_VERSION
        _user = KEYSTONE_USERNAME
        _key = KEYSTONE_PASSWORD
        _os_options = {
            'user_domain_name': KEYSTONE_USER_DOMAIN_NAME,
            'project_domain_name': KEYSTONE_PROJECT_DOMAIN_NAME,
            'project_name': KEYSTONE_PROJECT_NAME,
            'endpoint_type': CONST_OS_ENDPOINT_TYPE
        }

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
#    if ARGS.dryrun:
#        print("Response headers: %s" % resp_headers)
#        # for container in containers:
#        #     print(conn.get_account()[1])
#        #     conn.get_container(container)[1]
#        for data in conn.get_container("netsniff-attachments")[1]:
#            print('{0}\t{1}\t{2}'.format(
#                data['name'], data['bytes'], data['last_modified']))


# Create Container if needed
        account_dict = conn.get_account()[1]
        if not CONTAINER_NAME in account_dict[0]['name']:
            logger.debug(f"Container {CONTAINER_NAME} does not exist creating container")
            conn.put_container(CONTAINER_NAME, {'X-Container-Read': '.r:*,.rlistings'})
            logger.debug(f"Container {CONTAINER_NAME} has been created")
        return conn
    except:
        raise


def upload_attachment(swift_conn, content, mime_type):
    try:
        file_hash = hashlib.md5()
        file_hash.update(content)
        file_digest = file_hash.hexdigest()
        file_digest = str(uuid.uuid1())
        logger.info(f"Upload file {file_digest}")
        if not ARGS.dryrun:
            swift_conn.put_object(
                CONTAINER_NAME,
                file_digest,
                contents=content,
                content_type=mime_type
            )
            return file_digest
    except Exception as upload_err:
        logger.exception(upload_err)
        return "#"


def update_xymon_status(xymoncli, user_agent, url, attachments=None, thread_number=None, url_sub=None, nested_dict=None, **kwargs):
    try:
        color_status = {}
        color_status.update({"green": "\033[92m"})
        color_status.update({"yellow": "\033[93m"})
        color_status.update({"red": "\033[91m"})
        color_end = "\033[0m"
        if not ARGS.dryrun:
            xymoncli.addhtmldata('<h2>' + url + '</h2>' + '</h3>' + user_agent + "<br />")

            # Add attachments (non-blocking action)
            try:
                if nested_dict and attachments and thread_number is not None:
                    for file in attachments:
                        xymoncli.addhtmldata('<a href="' + file["url_prefix"] + "/" +
                                             CONTAINER_NAME + '/' + file['file_digest'] + '">' + file['label'] + '</a>')
            except:
                raise
        else:
            print('<h2>', url, '</h2>', '</h3>', user_agent, "<br />")

        if not ARGS.dryrun:
            # # Adding a blank string to prettify
            xymoncli.addhtmldata("<br />")

        # print(nested_dict)
        if nested_dict is not None:
            for key in nested_dict:
                #xymoncli.addhtmldata("<br />")

                status = nested_dict[key]['status']
                message = key + " : " + \
                    json.dumps(nested_dict[key]['message'],
                               indent=4, sort_keys=True)
                if ARGS.dryrun:
                    print(color_status.get(status),
                          "STATUS - ", color_end, message)
                else:
                    xymoncli.add_substatus(status, message)
                    xymoncli.addhtmldata("<hr width=70% size=1 color=white align=left>")

                    #xymoncli.addhtmldata('<hr>')
            #p = Path(f'{ATTACHMENTS_DIR}/graph_{thread_number}.pdf')
            #p.unlink()
            #logger.info(f'{ATTACHMENTS_DIR}/graph_{thread_number}.pdf deleted')
            p = Path(f'{ATTACHMENTS_DIR}/{url_sub}.har')
            p.unlink()
            logger.info(f'{ATTACHMENTS_DIR}/{url_sub}.har deleted')
            p = Path(f'{ATTACHMENTS_DIR}/{url_sub}_viewport.png')
            p.unlink()
            logger.info(f'{ATTACHMENTS_DIR}/{url_sub}_viewport.png deleted')
            p = Path(f'{ATTACHMENTS_DIR}/{url_sub}_fullpage.png')
            p.unlink()
            logger.info(f'{ATTACHMENTS_DIR}/{url_sub}_fullpage.png deleted')
                    # xymoncli.addhtmldata("<br />")
        else:
            for key, value in kwargs.items():
                if key == 'nodejs_err':
                    description = f"<b>Ci-dessous l'exception concernant l'exécution de NodeJS :</b><br> <i>Pour plus de détails, vérifiez les logs du container</i>" 
                    link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff/-/blob/master/lib/netsniff-url/netsniffPrototype.js>code NodeJS</a>"
                    xymoncli.add_substatus('red', f"{description} <br><br> {value} <br><br> {link_1}")

                    #xymoncli.addhtmldata("<button aria-haspopup=true aria-expanded=false>Mon compte</button> <ul role=menu> <li> <a href=# role=menuitem>Mon panier</li> <li> <a href=# role=menuitem>Mes commandes</li> </ul>")

                elif key == 'python_err':
                    description = f"<b>Ci-dessous l'exception concernant l'exécution du code Python :</b><br> <i>Pour plus de détails, vérifiez les logs du container :</i>" 
                    link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff/-/blob/master/lib/netsniff/netsniff.py>code Python</a>"
                    xymoncli.add_substatus('red', f"{description} <br><br> {value} <br><br> {link_1}")
                else:
                    pass

    except:
        raise


def send_xymon_status(xymoncli):
    if ARGS.dryrun:
        print("dryrun sending status to Xymon")
        #print(xymoncli._data)

    else:
        xymoncli.send_status()
        logger.info('sending status to Xymon')


def main():

    q = queue.Queue(maxsize=0)
    threads_nb = threads_num
    threads = []

    def do_stuff(q):
        while True:
            x = q.get()
            if x is None:
                break

            try:
                get_har(
                    CONST_PROGRAM,
                    CONST_MAIN_SCRIPT,
                    x['global_filename'],
                    x['global_config'],
                    x['check_conf'],
                    x['conf_unit'],
                    x['attachments'],
                    x['xymoncli'],
                    x['user_agent'],
                    x['url']
                    )
            except Exception as err:
                logger.error('Thread exception detected')
                logger.error(f'Task skipped)')
                pp = u.pprint.PrettyPrinter(indent=1, depth=1, width=20)
                python_err_reformated = pp.pformat(str(err))
    
                update_xymon_status(xymoncli, user_agent, url, python_err=python_err_reformated)
            finally:
                q.task_done()

    for i in range(threads_nb):
      logging.debug('Starting thread ', i)
      worker = threading.Thread(target=do_stuff, args=(q,))
      worker.setDaemon(True)
      worker.start()
      threads.append(worker)

    print(f'\n CONF_NETSNIFF: {CONF_NETSNIFF }\n')
    print(  f'CHECK_NETSNIFF: {CHECK_NETSNIFF}\n')

    # for global_filename in CONF_NETSNIFF:
    # TEST multi-confs
    for i, global_filename in enumerate(CONF_NETSNIFF, 1):
        print(f'global_filename {i}:', global_filename)
        global_config = u.read_conf(global_filename)
        # for check_filename in CHECK_NETSNIFF:
        # TEST multi-confs
        for i, check_filename in enumerate(CHECK_NETSNIFF, 1):
            print(f'\tcheck_filename {i}:', check_filename)
            check_conf = u.read_conf(check_filename)
            if check_filename.stem[:-len('.checks')] == global_filename.stem[:-len('.conf')]:
                if global_config['active']:
                    xymoncli = init_xymon_object(global_config)
                    for url in global_config['urls']:
                        for user_agent in global_config['request_user_agent']:
                            attachments = []
                            conf_unit = copy.deepcopy(global_config)
                            u.rewrite(conf_unit, url, user_agent)
                            x = dict(global_filename=global_filename, global_config=global_config, check_conf=check_conf,
                                conf_unit=conf_unit, attachments=attachments, xymoncli=xymoncli, user_agent=user_agent, url=url)
                            q.put(x)
                            logger.info(f'Processing {url} - Task added in the Queue')
                    q.join()
                    send_xymon_status(xymoncli)
                    logger.info(f'Processing {url} Complete')
                else:
                    logger.info(f"Site config <{global_config['active']}> in {global_filename}")

    # TEST multi-confs
    print('\n')


    # for global_filename in CONF_NETSNIFF:
    #     global_config = u.read_conf(global_filename)
    #     for check_filename in CHECK_NETSNIFF:
    #         check_conf = u.read_conf(check_filename)
    #         if check_filename.stem[:-len('.checks')] == global_filename.stem[:-len('.conf')]:
    #             if global_config['active']:
    #                 xymoncli = init_xymon_object(global_config)
    #                 for url in global_config['urls']:
    #                     for user_agent in global_config['request_user_agent']:
    #                         attachments = []
    #                         conf_unit = copy.deepcopy(global_config)
    #                         u.rewrite(conf_unit, url, user_agent)
    #                         x = dict(global_filename=global_filename, global_config=global_config, check_conf=check_conf,
    #                             conf_unit=conf_unit, attachments=attachments, xymoncli=xymoncli, user_agent=user_agent, url=url)
    #                         q.put(x)
    #                         logger.info(f'Processing {url} - Task added in the Queue')
    #                 q.join()
    #                 send_xymon_status(xymoncli)
    #                 logger.info(f'Processing {url} Complete')
    #             else:
    #                 logger.info(f"Site config <{global_config['active']}> in {global_filename}")

    q.join()
    logging.info('Processing all tasks complete')
    for i in range(threads_nb):
        q.put(None)
    for t in threads:
        t.join()


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(
        description="Netsnif : checks ressources loaded for a given url",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    PARSER.add_argument(
        "-v", "--verbose",
        help="run the script in verbose mode (print DEBUG messages)",
        action="store_true")

    PARSER.add_argument(
        "-d", "--dryrun",
        help="run the script in dryrun mode (do not send status to xymon)",
        action="store_true")

    PARSER.add_argument('--curlopts', default="", dest='curlopts',
                        help='CURL options to set tls/ssl version, ciphers, ...')

    ARGS = PARSER.parse_args()

    # Launch application
    main()
