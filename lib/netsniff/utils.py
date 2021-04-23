#-*- coding: utf-8 -*-

import yaml
import os
import sys
import time
import json
import base64
from collections import OrderedDict
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from graphviz import Digraph, render
from haralyzer import HarParser, HarPage
sys.path.append('/etc/netsniff/')
from variables import *

import pprint
import operator

MAX_RECURSION = 4

def MultiSub(dict_, url):
    """To make a multitude subtitutions and return the rewrited url"""
    if len(dict_) == 0:
        return url

    def repl_(regex_):
        match_ = regex_.group()
        for x in (sorted(dict_.keys(), key=lambda x: len(x))):
            if (re.search(x, match_) is not None):
                return dict_[x]
        print("error with SimulSub")
        print("check lookahead/lookbehind/beginning/end regex")
        return match_
    return re.sub("(" + "|".join(sorted(
        dict_.keys(), key=lambda x: len(x))) + ")", repl_, url)


def read_conf(filename):
    """Reading the yml global configuration file
    and return a dict"""
    with open(filename, "r") as file:
        config = yaml.safe_load(file.read())
        return config

def replace_xymon_host(global_config):
    """Read xymon_host from conf with envvars"""
    xymon_host = global_config['xymon_host']
    cut_envvars = xymon_host[-(len(xymon_host)-len("$SERVICENAME_")-len("$ENV_")):]
    xymon_host = os.path.expandvars('${SERVICENAME}.${ENV}.') + cut_envvars
    return xymon_host

def rewrite(config, url, user_agent):
    """Rewrite url and user agent
    from a config dict and return
    a single url, user_agent"""
    config['urls'] = url
    config['request_user_agent'] = user_agent


def encode_conf(filename, config, **kwargs):
    """Encode the config file in base64"""
    config = str(config).encode('utf-8')
    conf_encoded = base64.b64encode(config)
    return conf_encoded


def read_har_file(filename):
    """Read the har file
    and load it in json format"""
    with open(filename, 'r') as f:
        har_file = json.load(f)
        return har_file


def create_har_object(har_file):
    """Create har instance to parse all entries from a single dict"""
    with open(har_file, 'r') as f:
        har_parser = HarParser(json.loads(f.read()))
    return har_parser


def create_page_har_object(har_file, har_page_id):
    """Create page instance to parse
    the all entries one by one from a list"""
    with open(har_file, 'r') as f:
        har_page = HarPage(
            har_page_id, har_data=json.loads(f.read()))
    return har_page


def reorganize_for_tests(key_, check_conf):
    """Return the specific section of the check
    configuration dict to make the tests from appropriate function"""
    for key, value in check_conf.items():
        if key == key_:
            return check_conf[key]


def open_screenshot_attachment(url_sub, what):
    """Return opened viewport/fullpage attachment file"""
    screenshot = Path(f'{ATTACHMENTS_DIR}/{url_sub}_{what}.png')
    screenshot = open(screenshot, 'rb').read()
    return screenshot


def get_screenshot_attachment_date(url_sub, what):
    """Return viewport/fullpage attachment creation date"""
    screenshot = Path(f'{ATTACHMENTS_DIR}/{url_sub}_{what}.png')
    return time.ctime(os.path.getctime(screenshot))


def open_graph_attachment(thread_number):
    """Return opened graph attachment file"""
    screenshot = Path(f'{ATTACHMENTS_DIR}/graph_{thread_number}.pdf')
    screenshot = open(screenshot, 'rb').read()
    return screenshot


def get_graph_attachment_date(thread_number):
    """Return viewport/fullpage attachment creation date"""
    screenshot = Path(f'{ATTACHMENTS_DIR}/graph_{thread_number}.pdf')
    return time.ctime(os.path.getctime(screenshot))


def match_url_har(page, check_conf):
    """Check whether url match regex"""
    conf = reorganize_for_tests("match_url_har", check_conf)
    if conf:
        match_url_dict_results = OrderedDict()
        mudr = match_url_dict_results
        for i in range(len(conf)):
            if conf[i]['policy']['active']:
                conf_index = conf[i]['policy']
                match = conf_index['match']
                req_type = conf_index['scope']['req_type']
                url = conf_index['scope']['key']
                active_filter = conf_index['active_filter']
                regex_list = conf_index['regex_list']
                threshold = conf_index['threshold']
                if active_filter:
                    policy_filter = conf_index['filter']
                    content_type = conf_index['filter']['content_type'] or None
                    http_version = conf_index['filter']['http_version'] or None
                    request_type = conf_index['filter']['request_type'] or None
                    status_code = conf_index['filter']['status_code'] or None
                    entries = page.filter_entries(**policy_filter)
                    if not match and not entries:
                        mudr.update({f"<B>must_not_match_url_with_filters</B> {(regex_list)}, ({status_code}), ({threshold}):": {
                                    "status": "green", "message": len(matches) }})
                    elif match and not entries:
                        mudr.update({f"<B>must_match_url_with_filters</B> {(regex_list)}, ({status_code}), ({threshold}):": {
                                    "status": "green", "message": len(matches) }})
                else:
                    entries = page.filter_entries()
                    if not match and not entries:
                        mudr.update({f"<B>must_not_match_url_without_filters</B>  {(regex_list)}, ({status_code}), ({threshold}):": {
                                    "status": "green", "message": len(matches) }})
                    elif match and not entries:
                        mudr.update({f"<B>must_match_url_with_filters</B> {(regex_list)}, ({status_code}), ({threshold}):": {
                                    "status": "green", "message": len(matches) }})

                if req_type != 'request' or url != 'url':
                    raise ValueError('Invalid scope, should be either:\n'
                                     '* request url\'')
                for r in regex_list:
                    matches = []
                    counter = 1
                    for e in entries:
                        url_entry = e[req_type][url]
                        status_code = e["response"]["status"]
                        p = re.compile(r, flags=re.IGNORECASE)
                        descriptif_match = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si l'expression {r} n'apparaît pas au moins {threshold} fois dans le har"
                        descriptif_not_match = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si l'expression {r} apparaît au moins {threshold} fois dans le har"
                        link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#match_url_har>consigne</a>"

                        if match and active_filter:
                            libelle_must_match_url_with_filters = f"<B>must_match_url_with_filters</B> filtre content: (content_type), filtre http version: {http_version}, filtre request_type: {request_type}, filtre code: (status_code) <br> {descriptif} <br> {link_1} <br>"
                            if p.search(url_entry) is not None:
                                matches.append(str(counter) + "." + " " + url_entry[:100] + "  " + str(status_code))
                                counter += 1
                            if len(matches) >= threshold:
                                mudr.update({libelle_must_match_url_with_filters: {
                                            "status": "green", "message": len(matches) }})
                            else:
                                mudr.update({libelle_must_match_url_with_filters: {
                                            "status": "red", "message": 'matches'}})
                        if not match and not active_filter:
                            libelle_must_not_match_url_without_filters = f"<B>must_not_match_url_without_filters</B> <br> {descriptif_not_match} <br> {link_1} <br>"
                            if p.search(url_entry) is not None:
                                matches.append(str(counter) + "." + " " + url_entry[:100] + "  " + str(status_code))
                                counter += 1
                            if len(matches) >= threshold:
                                mudr.update({libelle_must_not_match_url_without_filters: {
                                            "status": "red", "message": matches }})
                            else:
                                mudr.update({libelle_must_not_match_url_without_filters: {
                                            "status": "green", "message": len(matches) }})
                        if match and not active_filter:
                            libelle_must_match_url_without_filters = f"<B>must_match_url_without_filters</B> <br> {descriptif_match} <br> {link_1} <br>"
                            if p.search(url_entry) is not None:
                                matches.append(str(counter) + "." + " " + url_entry[:100] + "  " + str(status_code))
                                counter += 1
                            if len(matches) >= threshold:
                                mudr.update({libelle_must_match_url_without_filters: {
                                            "status": "green", "message": len(matches)}})
                            else:
                                mudr.update({libelle_must_match_url_without_filters: {
                                            "status": "red", "message": matches }})
                        elif not match and active_filter:
                            libelle_must_not_match_url_with_filters = f"<B>must_not_match_url_with_filters</B> filtre content: (content_type), filtre http version: {http_version}, filtre request_type: {request_type}, filtre code: (status_code) <br> {descriptif_not_match} <br> {link_1} <br>"
                            if p.search(url_entry) is not None:
                                matches.append(str(counter) + "." + " " + url_entry[:100] + "  " + str(status_code))
                                counter += 1
                            if len(matches) >= threshold:
                                mudr.update({libelle_must_not_match_url_with_filters: {
                                            "status": "red", "message": matches }})
                            else:
                                mudr.update({libelle_must_not_match_url_with_filters: {
                                            "status": "green", "message": len(matches) }})
                        elif match and not active_filter:
                            #print('There is no entry', entries)
                            if p.search(url_entry) is not None:
                                matches.append(str(counter) + "." + " " + url_entry[:100] + "  " + str(status_code))
                                counter += 1
                            if len(matches) >= threshold:
                                mudr.update({libelle_must_match_url_without_filters: {
                                            "status": "green", "message": len(matches) }})

                            else:
                                mudr.update({libelle_must_match_url_without_filters: {
                                            "status": "red", "message": matches }})
            else:
                pass
        return mudr
    else:
        pass



def get_ttfb(page, check_conf):

    conf = reorganize_for_tests("time_to_first_byte", check_conf)

    if conf:
        if conf['active']:
            get_ttfb_dict_results = OrderedDict()
            gttfbdr = get_ttfb_dict_results
            gttfbdr = {}

            threshold_warning = conf['threshold_warning']
            threshold_critical = conf['threshold_critical']
            ttfb = page.time_to_first_byte


            descriptif = f"<i>Description:</i> Remonte <img alt=yellow src={xymon_yellow_img} width=16 height=16 border=0> lorsque la délai attendu par le navigateur avant de recevoir son premier octet de donnée provenant du serveur est superieur à {threshold_warning} ms <br> et <img alt=red src={xymon_red_img} width=16 height=16 border=0> s'il dépasse {threshold_critical} ms <br> Le ttfb peut varier à plusieurs étape de son calcul suite à une latence réseau par exemple. Il prend en compte les élements suivants : temps dattente, <br> recherche DNS, requête envoyée, en attente du traitement par le serveur, téléchargement du contenu"

            link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#time_to_first_byte>consigne</a>"
            link_2 = f"<a href=https://fr.wikipedia.org/wiki/Time_to_first_byte>wikipedia</a>"

            libelle = f"<B>time to first byte</B> <br> {descriptif} <br> {link_1} / {link_2} <br>"

            if ttfb >= threshold_warning and ttfb < threshold_critical:
                gttfbdr.update({libelle : {
                            "status": "yellow", "message": ttfb}})
            elif ttfb >= threshold_critical:
                gttfbdr.update({libelle : {
                            "status": "red", "message": ttfb}})
            else:
                gttfbdr.update({libelle: {
                            "status": "green", "message": ttfb}})
            return gttfbdr


def match_headers_cookies(page, check_conf):
    """
    Function to match headers and cookies.

    Since the output of headers might use different case, like:

        'content-type' vs 'Content-Type'

    This function is case-insensitive

    entry: entry object
    header_type: ``str`` of header type. Valid values:

        * 'request'
        * 'response'

    :param header: ``str`` of the header to search for
    :param value: ``str`` of value to search for
    """

    conf = reorganize_for_tests(
        'match_headers_cookies', check_conf)

    if conf:
        match_headers_cookies_dict_results = OrderedDict()
        mhcdr = match_headers_cookies_dict_results
        for i in range(len(conf)):
            if conf[i]['policy']['active']:
                conf_index = conf[i]['policy']
                match = conf_index['match']
                header_type = conf_index['scope']['header_type']
                type_entry = conf_index['scope']['type_entry']
                header = conf_index['search_in']['header']
                threshold = conf_index['threshold']
                matches = []
                urls = []
                no_matches = []
                duplicate_matches = []
                for entry in page.entries:
                    if header_type not in entry:
                        raise ValueError('Invalid name_type, should be either:\n\n'
                                         '* \'request\'\n*\'response\'')
                    for h in entry[header_type][type_entry]:
                        if match:
                            libelle = f"<B>must_match_{header_type}_{type_entry}</B> : ({h['name']}), ({threshold})"
                            if h['name'].lower() == header.lower() and h['value'] is not None:
                                p = re.compile(header, flags=re.IGNORECASE)
                                if p.search(h['name']) is not None:
                                    matches.append(h['name'][:100])
                                    urls.append(entry['request']['url'][:100])
                                    if len(matches) >= threshold:
                                        mhcdr.update(
                                        {libelle: {"status": "green", "message": f"match {len(matches)} times {urls}" }})
                                    else:
                                        mhcdr.update(
                                        {libelle: {"status": "red", "message": f"match {len(matches)} times"}})
                            elif re.search(header, h['name']) is None:
                                libelle = f"<B>must_match_{header_type}_{type_entry}</B> : ({header}), ({threshold})"
                                no_matches.append(header)
                                for duplicate in no_matches:
                                    if duplicate not in duplicate_matches:
                                        duplicate_matches.append(duplicate)
                                        mhcdr.update(
                                            {libelle: {"status": "red", "message": "not found"}})

                        if not match:
                            libelle = f"<B>must_not_match_{header_type}_{type_entry}</B> : ({h['name']}), ({threshold})"
                            if h['name'].lower() == header.lower() and h['value'] is not None:
                                p = re.compile(header, flags=re.IGNORECASE)
                                if p.search(h['name']) is not None:
                                    matches.append((h['header'])[:100])
                                    urls.append(entry['request']['url'][:100])
                                    if len(matches) >= threshold:
                                        mhcdr.update(
                                            {libelle: {"status": "red", "message": f"match {len(matches)} times"} })
                                    else:
                                        mhcdr.update(
                                            {libelle: {"status": "green", "message": f"match {len(matches)} times {urls}" }})
            else:
                pass
        return mhcdr
    else:
        pass


def preprocess_tree(page, check_conf):
    """
    Function to match headers and cookies.

    Since the output of headers might use different case, like:

    'content-type' vs 'Content-Type'

    This function is case-insensitive

    entry: entry object
    header_type: ``str`` of header type. Valid values:

    * 'request'
    * 'response'

    :param header: ``str`` of the header to search for
    :param value: ``str`` of value to search for
    """

    conf = reorganize_for_tests('init_tree', check_conf)
    if conf:
        if conf['active']:
            tag = conf['tag']

            current_iteration = []

            for e in page.entries:
                if '_initiator' in e:
                    value_chars_escaped = re.escape(tag)
                    p = re.compile(value_chars_escaped, flags=re.IGNORECASE)
                    if p.search(e['_initiator']) is not None:
                        current_iteration.append({
                            'Initiator': e['_initiator'],
                            'URL': e['request']['url'],
                            'status': e['response']['status'],
                            'redir': e['response']['redirectURL'],
                            'time': e['time'],
                            'timings': e['timings'],
                            'request': {'cookies': e['request']['cookies']},
                            'response': {'cookies': e['response']['cookies']}
                            })

            return current_iteration


def create_recurstree(check_conf, page, current_iteration=None, merge_iterations=None, recursion_depth=0):

    conf = reorganize_for_tests("init_tree", check_conf)

    if conf:
        if conf['active']:
            current_list = []
            results = OrderedDict()

            if(merge_iterations == None):
                merge_iterations = []

            if len(current_iteration) == 0:
                return merge_iterations

            merge_iterations.append(current_iteration)
            for e in page.entries:
                for _list in current_iteration:
                    for key, value in _list.items():
                        if 'URL' in key:
                            value_chars_escaped = re.escape(value)
                            p = re.compile(value_chars_escaped, flags=re.IGNORECASE)
                            if '_initiator' in e and p.search(e['_initiator']) is not None:
                                current_list.append({
                                    'Initiator': e['_initiator'],
                                    'URL': e['request']['url'],
                                    'status': e['response']['status'],
                                    'redir': e['response']['redirectURL'],
                                    'time': e['time'],
                                    'timings': e['timings'],
                                    'request': {'cookies': e['request']['cookies']},
                                    'response': {'cookies': e['response']['cookies']}
                                    })

            current_iteration = current_list

            if recursion_depth < MAX_RECURSION:
                create_recurstree(check_conf, page, current_iteration, merge_iterations, recursion_depth + 1)
            return merge_iterations


def get_initiator_list_without_duplicates(tree, check_conf):

    conf = reorganize_for_tests(
        "init_tree", check_conf)

    if conf:
        if conf['active']:
            if tree is not None:
                initiators = []
                for _list in tree:
                    for _dict in _list:
                        initiators.append(_dict['Initiator'])
                initiators = list(dict.fromkeys(initiators))
                return initiators

            else:
                pass
        else:
            pass
    else:
        pass


def get_status_code_from_tree(page, tree, check_conf):
    """Check whether url match regex"""

    conf = reorganize_for_tests(
        "get_status_code_from_tree",check_conf)
    if conf:
        if conf['active']:
            if tree is not None:
                get_status_code_from_tree_dict_results = OrderedDict()
                gscftdr = get_status_code_from_tree_dict_results
                status_code_list = conf['status_code']
                threshold = conf['threshold']
                matches = []
                no_matches = []
                initiators = get_initiator_list_without_duplicates(tree, check_conf)
                for r in status_code_list:
                    no_matches.clear()
                    for initiator in initiators:
                        value_chars_escaped = re.escape(initiator)
                        p_initiator = re.compile(value_chars_escaped, flags=re.IGNORECASE)
                        p_status_code = re.compile(r, flags=re.IGNORECASE)
                        for e in page.entries:
                            url_entry = e['request']['url']
                            status_code = str(e["response"]["status"])

                            descriptif = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si l'une des initiators du graph est en erreur {r}"

                            link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#get_status_code_from_tree>consigne</a>"
                            list_urls = f"<font color=red>Liste des ressources en erreur : </font>"
                            libelle_without_details = f"<B>get_status_code_from_tree</B> <br> {descriptif} <br> {link_1} <br>"
                            libelle_details = f"<B>get_status_code_from_tree</B> <br> {descriptif} <br> {link_1} <br> {list_urls} <br>"

                            if p_initiator.search(e['request']['url']) is not None and p_status_code.search(status_code) is None:
                                no_matches.append(f"{r}, {initiator}, {threshold}")
                                gscftdr.update({libelle_without_details: {
                                    "status": "green", "message": f"{len(no_matches)} initiators sous le seuil d'alerte" }})
                            if p_initiator.search(e['request']['url']) is not None and p_status_code.search(status_code):
                                    matches.append(f"{url_entry}, {status_code}")
                if len(matches) > threshold:
                    gscftdr.update({libelle_details: {
                            "status": "red", "message": matches}})

                return gscftdr
            else:
                pass
        else:
            pass
    else:
        pass


def get_status_code_from_har(page, check_conf):
    """Check whether url match regex"""

    conf = reorganize_for_tests(
        "get_status_code_from_har",check_conf)
    if conf:
        if conf['active']:
            get_status_code_from_har_dict_results = OrderedDict()
            gscfhrd = get_status_code_from_har_dict_results
            status_code_list = conf['status_code']
            threshold = conf['threshold']
            matches = []
            no_matches = []
            for r in status_code_list:
                no_matches.clear()
                p_status_code = re.compile(r, flags=re.IGNORECASE)
                for e in page.entries:
                    url_entry = e['request']['url']
                    status_code = str(e["response"]["status"])

                    descriptif = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si l'une des urls du HAR est en erreur {r}"
                    link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf>consigne</a>"
                    list_urls = f"<font color=red>Liste des ressources en erreur : </font>"
                    libelle_without_details = f"<B>get_status_code_from_har</B> <br> {descriptif} <br> {link_1} <br>"
                    libelle_details = f"<B>get_status_code_from_har</B> <br> {descriptif} <br> {link_1} <br> {list_urls} <br>"

                    if p_status_code.search(status_code) != r:
                        no_matches.append(f"{r}, {url_entry}, {threshold}")
                        gscfhrd.update({libelle_without_details: {
                            "status": "green", "message": f"{len(no_matches)} urls sous le seuil d'alerte" }})
                    if p_status_code.search(status_code) == r:
                        matches.append(url_entry, status_code)
            if len(matches) > threshold:
                gscftdr.update({libelle_details: {
                            "status": "red", "message": matches}})

            return gscfhrd
        else:
            pass
    else:
        pass



def get_load_from_tree(page, check_conf, tree):
    conf = reorganize_for_tests(
        'get_load_from_tree', check_conf)

    if conf:
        get_load__from_tree_dict_results = OrderedDict()
        glftdr = get_load__from_tree_dict_results
        if conf['active']:
            if tree is not None:
                threshold = conf['threshold']
                red_xymon_message = conf['red_xymon_message']
                matches = OrderedDict()
                no_matches = []
                duplicate_matches = []
                initiators = []
                counter = 1
                for _list in tree:
                    for _dict in _list:
                        initiators.append(_dict['Initiator'])
                initiators = list(dict.fromkeys(initiators))


                def exclude_urls_from_tree(initiators, exclude_urls):
                    for r in exclude_urls:
                        for elem in initiators:
                            r_chars_escaped = re.escape(r)
                            p = re.compile(r_chars_escaped, flags=re.IGNORECASE)
                            if p.search(elem) is not None:
                                initiators.remove(elem)
                                #print(p.search(elem))
                            else:
                                pass
                    return initiators

                if 'exclude_urls' in conf:
                    exclude_urls = conf['exclude_urls']
                    initiators = exclude_urls_from_tree(initiators, exclude_urls)
                    #print("new list =", initiators)
                else:
                    pass

                for initiator in initiators:
                    value_chars_escaped = re.escape(initiator)
                    p = re.compile(value_chars_escaped, flags=re.IGNORECASE)

                    descriptif = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si le temps de réponse d'un des initiators du graph est superieur à {threshold} ms"

                    link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#get_load_from_tree>consigne</a>"
                    list_urls = f"<font color=red>Liste des ressources concernées : </font>"
                    libelle_details = f"<B>get_load_from_tree</B> <br> {descriptif} <br> {list_urls} <br>"
                    libelle_without_details = f"<B>get_load_from_tree</B> <br> {descriptif} <br> {link_1} <br>"

                    for entry in page.entries:
                        load_time = entry['time']
                        load_time_details = entry['timings']
                        req_url = entry['request']['url']
                        if p.search(req_url) is not None:
                            if load_time > threshold:
                                matches.update({
                                    'requestURL': req_url,
                                    'Time': load_time,
                                    'Timing': load_time_details})
                                glftdr.update({libelle_details: {"status": "red", "message": matches}})
                            else:
                                no_matches.append(f"{req_url}, {load_time}")
                                glftdr.update({libelle_without_details: {"status": "green", "message": f"{len(no_matches)} initiators sont sous le seuil d'alerte"}})

            else:
                pass
        else:
            pass
        return glftdr

    else:
        pass


def get_load_from_har(page, check_conf):
    conf = reorganize_for_tests(
        'get_load_from_har', check_conf)

    if conf:
        get_load_from_har_dict_results = OrderedDict()
        glfhdr = get_load_from_har_dict_results
        for i in range(len(conf)):
            if conf[i]['policy']['active']:
                conf_index = conf[i]['policy']
                match_str = conf_index['match']
                threshold_warning = conf_index['threshold_warning']
                threshold_critical = conf_index['threshold_critical']
                red_xymon_message = conf_index['red_xymon_message']
                matches = OrderedDict()
                no_matches = []
                duplicate_matches = []
                p = re.compile(match_str, flags=re.IGNORECASE)

### HTML content for get_load_from_har
                descriptif = f"<i>Description:</i> Evalue le temps de réponse de l'url {match_str} <br> Remonte <img alt=yellow src={xymon_yellow_img} width=16 height=16 border=0> si >= à {threshold_warning} ms ou <img alt=red src={xymon_red_img} width=16 height=16 border=0> si >= à {threshold_critical}"
                link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#get_load_from_har>consigne</a>"
                libelle = f"<B>get_load_from_har</B> <br> {descriptif} <br> {link_1} <br>"
###

                for entry in page.entries:
                    load_time = entry['time']
                    load_time_details = entry['timings']
                    req_url = entry['request']['url']
                    if p.search(req_url) is not None:
                        if load_time >= threshold_warning and load_time < threshold_critical:
                            matches.update({
                                'requestUrl': req_url,
                                'Time': load_time,
                                'Timings': load_time_details})
                            glfhdr.update(
                                {libelle: {"status": "yellow", "message": matches}})
                        elif load_time >= threshold_critical:
                            matches.update({
                                'requestUrl': req_url,
                                'Time': load_time,
                                'Timings': load_time_details})
                            glfhdr.update(
                                {libelle: {"status": "red", "message": matches}})
                        else:
                            glfhdr.update(
                                {libelle: {"status": "green", "message": load_time}})
                    else:
                        no_matches.append(p.search(req_url))
                        for duplicate in no_matches:
                            if duplicate not in duplicate_matches:
                                duplicate_matches.append(duplicate)
                                glfhdr.update(
                                        {libelle: {"status": "red", "message": red_xymon_message}})
            else:
                pass
        return glfhdr
    else:
        pass


def get_load_from_har_without_list(page, check_conf):
    conf = reorganize_for_tests(
        'get_load_from_har_without_list', check_conf)

    if conf:
        get_load_from_har_without_list_dict_results = OrderedDict()
        glfhwldr = get_load_from_har_without_list_dict_results
        if conf['active']:
            threshold = conf['threshold']
            nb_display = conf['nb_display']
            red_xymon_message = conf['red_xymon_message']
            gt_load_matches = {}
            lt_load_matches = []
            no_matches = []
            duplicate_matches = []
            page_load = page.pageTimings['onContentLoad']

            for entry in page.entries:
                load_time = entry['time']
                load_time_details = entry['timings']
                req_url = entry['request']['url']
                libelle = f"<B>get_load_from_har_without_list</B>"

                descriptif = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si le load du DOM de la page est supérieur à {threshold} ms"


                link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#get_load_from_har_without_list>consigne</a>"
                list_urls = f"<font color=red>Liste des {nb_display} ressources les plus longues a charger (ordre décroissant): </font>"
                libelle_without_details = f"{libelle} <br/> {descriptif} <br/> {link_1} <br/>"
                libelle_details = f"{libelle} <br/> {descriptif} <br/> {link_1} <br/> {list_urls} <br/>"
                if page_load is not None:

                    if page_load < threshold:
                        lt_load_matches.append(
                                f"{req_url} : {load_time}")
                        glfhwldr.update(
                            {libelle_without_details: {"status": "green", "message": 'OK'}})
                    if page_load > threshold:
                        gt_load_matches.update(
                                {req_url : load_time})
                        sorted_gt_load_matches = sorted(gt_load_matches.items(), reverse=True, key=operator.itemgetter(1))
                        nb_sorted_gt_load_matches = sorted_gt_load_matches[:nb_display]
                        pp = pprint.PrettyPrinter(depth=2, width=300)

                        glfhwldr.update(
                            {libelle_details: {"status": "red", "message": pp.pformat(nb_sorted_gt_load_matches)}})
                else:
                    no_matches.append(p.search(load_time))
                    for duplicate in no_matches:
                        if duplicate not in duplicate_matches:
                            duplicate_matches.append(duplicate)
                            glfhwldr.update(
                                {libelle: {"status": "red", "message": red_xymon_message}})
        else:
            pass
        return glfhwldr
    else:
        pass


def get_nested_number_tags(check_conf, tree):
    conf = reorganize_for_tests(
        'get_nested_number_tags', check_conf)

    if conf:
        if conf['active']:
            if tree is not None:
                initiators = []
                threshold = conf['threshold']
                get_number_nested_initiators_results_dict = OrderedDict()
                gnnird = get_number_nested_initiators_results_dict

                for _list in tree:
                    for _dict in _list:
                        initiators.append(_dict['Initiator'])
                initiators = list(dict.fromkeys(initiators))
                descriptif = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si le nombre de tags en cascade est inferieur à {threshold} <br> Cela peut signifier qu'une url n'est pas appelee ou qu'elle l'est aléatoirement"

                link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#get_nested_number_tags>consigne</a>"
                list_urls = f"<font color=red>Liste des ressources trouvées : </font>"
                libelle_details = f"<B>get_nested_number_tags</B> <br> {descriptif} <br> {link_1} <br> {list_urls} <br>"
                libelle_without_details = f"<B>get_nested_number_tags</B> <br> {descriptif} <br> {link_1} <br>"

                if len(initiators) < threshold:
                    gnnird.update(
                                {libelle_details: {"status": "red", "message": initiators}})
                else:
                    gnnird.update(
                            {libelle_without_details: {"status": "green", "message": len(initiators)}})

                return gnnird
            else:
                pass
        else:
            pass
    else:
        pass


def get_duplicate_request_urls(page, check_conf):
    conf = reorganize_for_tests(
        'get_duplicate_request_urls', check_conf)

    if conf:
        if conf['active']:
            get_duplicate_request_urls_results_dict = OrderedDict()
            gdrurd = get_duplicate_request_urls_results_dict
            threshold = conf['threshold']
            matches = {}
            no_matches = []

### HTML content for get_duplicate_request_urls ###
            descriptif = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> lorsqu'une requête se trouve au moins {threshold} fois dans le HAR"
            link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#get_duplicate_request_urls>consigne</a>"
            list_urls = f"<font color=red>Liste des ressources concernées (ordre décroissant): </font>"
            libelle_details = f"<B>get_duplicate_request_urls</B> <br> {descriptif} <br> {link_1} <br> {list_urls} <br>"
            libelle_without_details = f"<B>get_duplicate_request_urls</B> <br> {descriptif} <br> {link_1} <br>"
###

            for key, value in page.duplicate_url_request.items():
                if value >= threshold:
                    matches.update(
                            {key[:100] : value})
                    sorted_matches = sorted(matches.items(), reverse=True, key=operator.itemgetter(1))
                    pp = pprint.PrettyPrinter(depth=2, width=300)

                elif value < threshold:
                    no_matches.append(f"({key[:100]}), {value}")
            if len(matches) > 0:
                    gdrurd.update(
                                {libelle_details: {"status": "red", "message": pp.pformat(sorted_matches) }})
            else:
                gdrurd.update(
                            {libelle_without_details: {"status": "green", "message": f"Aucune url n'est presente au moins {threshold} fois dans le HAR"}})
            return gdrurd
        else:
            pass
    else:
        pass


def preprocess_graph(tree, check_conf):

    conf = reorganize_for_tests(
    'init_tree', check_conf)

    if conf:
        if conf['active']:
            if tree is not None:
                tag = conf['tag']
                letter_initiator = 'A'
                counter_initiator = 1

                letter_url = 'a'
                counter_url = 1

                nodes = []
                initiators = get_initiator_list_without_duplicates(tree, check_conf)
                for initiator in initiators:

                    for _list in tree:
                        for _dict in _list:

                            if initiator == _dict['Initiator']:
                                nodes.append({'Initiator': _dict['Initiator'],
                                    'ID_initiator': letter_initiator + str(counter_initiator),
                                    'URL': _dict['URL'],
                                    'ID_URL': letter_url + str(counter_url)})
                                counter_url += 1

                    counter_initiator += 1

                new_list_dicts = []
                initiators = get_initiator_list_without_duplicates(tree, check_conf)
                for initiator in initiators:
                    for node_list in nodes:
                        if initiator == node_list['URL']:
                            new_list_dicts.append({'Initiator': node_list['URL'], 'ID_initiator': node_list['ID_URL'] })
                # print(new_list_dicts)
                for node_list in nodes:
                    for new_list in new_list_dicts:
                        if node_list['Initiator'] == new_list['Initiator']:
                            node_list['ID_initiator'] = new_list['ID_initiator']
                            node_list = new_list
                nodes.insert(0 ,{'Initiator': 'None', 'ID_initiator': 'None', 'URL': tag, 'ID_URL': 'A1'})

                return nodes
            else:
                pass
        else:
            pass
    else:
        pass


def create_graph(nodes, thread_number):

    if nodes is not None:

        dot = Digraph('G',
                    node_attr={'resolution': '128',
                    'fontcolor': 'white',
                    'fillcolor': '#FF7900',
                    'fontsize': '12',
                    'fontname': 'Helvetica',
                    'shape': 'box',
                    'height': '.1'
                    })

        dot.graph_attr['rankdir'] = 'LR'
        dot.graph_attr['bgcolor'] = '#0e0e0e'
        dot.graph_attr['splines'] = 'polyline'
        dot.edge_attr['arrowhead'] ='normal'
        dot.edge_attr['arrowsize'] = '2'
        dot.edge_attr['arrowType'] = 'dot'
        dot.edge_attr['color']= 'white'
        dot.node_attr['style'] = 'filled, dashed'

        for node in nodes:
            if node['ID_initiator'] != 'None' and node['Initiator'] != 'None':
                dot.node(node['ID_initiator'], re.sub(r'(.{50})(?!$)', r'\1\\n', node['Initiator']))
                dot.node(node['ID_URL'], re.sub(r'(.{50})(?!$)', r'\1\\n', node['URL']))
                dot.edge(node['ID_initiator'], node['ID_URL'])
        dot.render(
            filename=f'{ATTACHMENTS_DIR}/graph_{thread_number}',
            format='pdf',
            cleanup=True,
            )
    else:
        pass


class Tree(object):
    def __init__(self, nodes):
        self.nodes = nodes

    def allParents(self, targetNodeName):
        currentNode = next(node for node in self.nodes if node.name == targetNodeName)

        if currentNode.parent is None:
            return [currentNode.name]
        else:
            return [currentNode.name] + self.allParents(currentNode.parent)


class TreeNode(object):
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent


def get_parents_url(check_conf, nodes):

    conf = reorganize_for_tests(
    'get_parents_url', check_conf)

    if conf:
        if conf['active']:
            if node is not None:
                get_parents_url_dict_results = OrderedDict()
                gpudr = get_parents_url_dict_results
                from_url = conf['from_url']
                threshold = conf['threshold']
                libelle = f"get_parents_url : ({from_url}), ({threshold})"

                myTreeNodes = []
                for node in nodes:
                    if node['ID_initiator'] == 'None' or node['Initiator'] == 'None':
                        node['ID_initiator'] = None
                        node['Initiator'] = None
                        myTreeNodes.append(TreeNode(name = node['URL'], parent = node['Initiator']))
                    else:
                        myTreeNodes.append(TreeNode(name = node['URL'], parent = node['Initiator']))

                myTree = Tree(nodes = myTreeNodes)
                initiators_from_url = myTree.allParents(targetNodeName = from_url)
                initiators_from_url.pop(0)
                if len(initiators_from_url) < threshold or len(initiators_from_url) > threshold:
                    gpudr.update(
                                {libelle: {"status": "red", "message": initiators_from_url}})
                else:
                    gpudr.update(
                                {libelle: {"status": "green", "message": len(initiators_from_url)}})
                return gpudr

            else:
                pass
        else:
            pass
    else:
        pass


from subprocess import Popen, PIPE, STDOUT

def get_bad_certificates(page, check_conf):

    conf = reorganize_for_tests(
            'get_bad_certificates', check_conf)

    if conf:
        if conf['active']:
            curlopts = conf.get('curlopts', '')
            exclude_domains = conf.get('exclude_domains', '')
            print(curlopts, exclude_domains)
            #curlopts = conf['curlopts'] or None
            #exclude_domains = conf['exclude_domains'] or None
            #if 'curlopts' in conf:
            #    curlopts = conf['curlopts']
            #if 'exclude_domains' in conf:
            #    exclude_domains = conf['exclude_domains']

            get_bad_certificates_dict_results = OrderedDict()
            gbcdr = get_bad_certificates_dict_results
            threshold_warning = conf['threshold_warning']
            threshold_critical = conf['threshold_critical']
            libelle = f"<B>get_bad_certificates</B> :"

            https_call = []
            https_bad_certificates = []

            for entry in page.entries:
                m = re.match("https://([^/]*)/.*", entry['request']['url'])
                #print(m.group(1))
                if m is not None:
                    https_call.append(m.group(1))

            https_call_sorted_uniq = sorted(set(https_call))
            #print(https_call_sorted_uniq)

            for site in https_call_sorted_uniq:
                # Dont check if domain in exception list
                if site in exclude_domains:
                    continue
                # Set max attempt to 3 to avoid false negative
                retries = CURL_RETRY_NUMBER
                r_rc = None

                #print(f"{CURL_BIN} {CURL_FLAGS} {curlopts} https://{site}")
                while r_rc != 0 and retries > 0:
                    out = Popen(f"{CURL_BIN} {CURL_FLAGS} {curlopts} https://{site}", shell=True,
                                stderr=STDOUT,
                                stdout=PIPE)
                    r_out = out.communicate()[0]
                    r_rc = out.returncode
                    #print("essaie " + site + "Numero " + str(retries) + "code retour " + str(r_rc))
                    retries = retries -1

                if r_rc > 0:
                    pp = pprint.PrettyPrinter(indent=3, depth=1, width=100)
                    message = (site), (r_rc), (r_out)
                    message_reformated = pp.pformat(message)
                    https_bad_certificates.append(message_reformated)
                    gbcdr.update(
                            {libelle: {"status": "red", "message": https_bad_certificates}})
                else:
                    gbcdr.update(
                            {libelle: {"status": "green", "message": 'Aucune erreur de certificat'}})
        #message.update({"green": ""})
        #message.update({"yellow": str(https_bad_certificate)})
        #message.update({"red": str(https_bad_certificate)})
            return gbcdr


def get_response_body_text(page, check_conf):

    conf = reorganize_for_tests(
            'get_response_body_text', check_conf)

    if conf:
        if conf['active']:
            regex_list = conf['regex_list']
            threshold = conf['threshold']
            #xymon_message_green = conf['xymon_message_green']
            #xymon_message_red = conf['xymon_message_red']
            get_response_body_text_dict_results = OrderedDict()
            grbtdr = get_response_body_text_dict_results
            for r in regex_list:
                matches = {}
                descriptif = f"<i>Description:</i> Remonte <img alt=red src={xymon_red_img} width=16 height=16 border=0> si l'expression <i>{r}</i> apparaît moins de {threshold} fois dans le body présent dans le HAR. <br> Ci-dessous le nombre d'entrées où est apparût au moins <i>{threshold}</i> fois l'expression"
                link_1 = f"<a href=https://gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf#get_reponse_body_text>consigne</a>"
                libelle = f"<B>get_response_body_text</B> <br> {descriptif} <br> {link_1} <br>"
                p = re.compile(r, flags=re.IGNORECASE)
                for entry in page.entries:
                    req_url = entry['request']['url']
                    dict_content = entry['response']['content']
                    for k,v in dict_content.items():
                        if k == 'text':
                            text_value = v
                            if p.search(text_value):
                                matches.update({'pattern_ref': p.search(text_value), "request_url": req_url})
                                if len(matches) >= threshold:
                                    grbtdr.update(
                                            {libelle: {"status": "green", "message": len(matches)}})
                                else:
                                    grbtdr.update(
                                            {libelle: {"status": "red", "message": matches}})

            return grbtdr

def get_not_none_check_results(checks_results_list):
    nested_dict = {}
    for dict_list in checks_results_list:
        if dict_list is not None:
            nested_dict.update(dict_list)
        else:
            pass
    return nested_dict


def get_not_none_mediastorage_objects(objects):
    not_none_objects = []
    for _list in objects:
        if _list['object_name'] is not None:
            not_none_objects.append(_list)
        else:
            pass
    return not_none_objects
