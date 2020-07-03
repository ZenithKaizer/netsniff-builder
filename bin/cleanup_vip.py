#!/usr/bin/python3
import os
import requests
import socket
import sys


def get_vhype_vip_name():
    return [key for key in os.environ.keys() if key.startswith("VHYPE_VIP")]


def get_vip_info(vhype_vip_name):
    try:
        info = os.environ[vhype_vip_name].split("|")
        try:
            vip_ip = info[0].split(":")[0]
            vip_port = info[0].split(":")[1]
            vip_site = info[3]
        except IndexError:
            print('Malformated VIP')
            exit(1)
        try:
            vip_environment = info[4].split("#")[0]
            vip_comment = info[4].split("#")[1]
        except IndexError:
            vip_environment = info[4]
            vip_comment="no-info"

        return {
            'vip_ip': vip_ip,
            'vip_port': vip_port,
            'vip_site': vip_site,
            'vip_environment': vip_environment,
            'vip_comment': vip_comment
            }
    except IndexError:
        print('No VIP defined')
        exit(0)


def get_vip_members(api_url):
    vip_request = requests.get(
        api_url,
        auth=(os.environ['VHYPE_USER'], os.environ['VHYPE_PASS']),
        verify=False)

    if vip_request.status_code != 200:
        print('error API return HTTP code ' + str(vip_request.status_code))
        print(vip_request.json())
        exit(1)
    try:
         return vip_request.json(
         )['members'][0]['loadbalancer']['pools'][0]['nodes']
    except IndexError:
         print('Empty or new VIP')
         exit(0)


def delete_node(api_url, node, vip):
    data = {
        "node": {
            "ip": node['ip'],
            "port": node['port'],
            "site": vip['vip_site'],
            "environment": vip['vip_environment']
        },
        "container": "true",
        "action": "remove"
    }
    sys.stdout.flush()
    print("Deleting node {}:{} in VIP {}:{}".format(
        node['ip'],
        node['port'],
        vip['vip_ip'],
        vip['vip_port']))
    node_request = requests.patch(api_url,
                                  json=data,
                                  auth=(os.environ['VHYPE_USER'],
                                        os.environ['VHYPE_PASS']),
                                  verify=False)
    print(node_request)


if __name__ == '__main__':
    container_ip = socket.gethostbyname(socket.gethostname())
    print("Container IP : {}".format(container_ip))
    vips = get_vhype_vip_name()

    for vip in vips:
        # print("VIP : {}".format(vip))
        vip_info = get_vip_info(vip)
        # print("VIP info : {}".format(vip_info))
        api_url = 'https://api.infra.orangeportails.net/network-lb/v3/' \
                  'vips/{}%3A{}'.format(
            vip_info['vip_ip'], vip_info['vip_port'])
        vip_members = get_vip_members(api_url)
        # print("VIP members : {}".format(vip_members))

        for node in vip_members:
            # print("Nodes : {}".format(node))
            # print("Node IP : {}".format(node['ip']))
            if vip_info['vip_comment'] == "empty-vip":
                delete_node(api_url, node, vip_info)
            elif vip_info['vip_comment'] == "delete-node" and \
                    node['ip'] == container_ip:
                delete_node(api_url, node, vip_info)
