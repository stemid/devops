#!/usr/bin/env python3
# This tool uses vSphere Custom Attributes to "tag" an entire inventory folder
# of VMs recursively with a certain attribute given on the CLI.
# See --help argument for more information.
#
# Put vcenter information into a configuration file. By default 
# /etc/vcenter.cfg and ./vcenter.local.cfg are attempted. 
# Example:
# [vcenter]
# hostname = localhost
# username = svc_user
# password = secret password
# port = 443
#
# by Stefan Midjich <swehack@gmail.com> - 2016

import atexit
from sys import exit, stderr
from urllib.parse import unquote
from configparser import RawConfigParser
from argparse import ArgumentParser, FileType

import requests
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

parser = ArgumentParser(
    description='Tag any vcenter VM object under a specific path',
    epilog=('Example: ./tag_path.py -c vcenter.cfg -p '
            '"SE Datacenter/PoC VMs/lnx-lab02" -K "Customername" '
            '-V "Company X"')
)

config = RawConfigParser()
try:
    config.readfp(open('vcenter.cfg'))
except:
    pass
config.read(['/etc/vcenter.cfg', './vcenter.local.cfg'])

parser.add_argument(
    '-c', '--configuration',
    type=FileType('r'),
    dest='config_file',
    metavar='FILE',
    help='File with additional configuration options.'
)

parser.add_argument(
    '-m', '--max-recursion',
    default=16,
    dest='max_recursion',
    type=int,
    metavar='N',
    help='Max recursion depth when traversing vcenter entities.'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level.'
)

parser.add_argument(
    '-p', '--path',
    required=True,
    dest='vc_path',
    metavar='PATH',
    help='Vcenter path to tag all items under.'
)

parser.add_argument(
    '-K', '--key',
    required=True,
    dest='field_name',
    metavar='STRING',
    help='Vcenter custom field name.'
)

parser.add_argument(
    '-V', '--value',
    required=True,
    dest='field_value',
    metavar='STRING',
    help='Vcenter custom field value.'
)


def entity_info(vc_entity):
    """
    entity_info - get name information from a vcenter entity

    vc_entity - any vcenter entity
    """

    obj_id = str(vc_entity).split(':')[1].rstrip('\'')
    vc_name = unquote(vc_entity.name)

    return (
        vc_name,
        obj_id
    )


def tag(vc_node, key, value, depth=1):
    """
    Recursively tag any folders and VMs under a certain VC node.
    """
    args = parser.parse_args()
    maxdepth = args.max_recursion

    if depth > maxdepth:
        if args.verbose:
            print('Max recursion depth, bailing out like bankers',
                  file=stderr
                 )
        return

    object_type = vc_node.__class__.__name__

    if object_type == 'vim.Folder':
        (folder_name, folder_object_id) = entity_info(vc_node)

        for _entity in vc_node.childEntity:
            tag(_entity, key, value, depth+1)
        return

    if object_type == 'vim.VirtualApp':
        (vapp_name, vapp_object_id) = entity_info(vc_node)

        for _entity in vc_node.vm:
            tag(_entity, key, value, depth+1)
        return

    if object_type == 'vim.VirtualMachine':
        (vm_name, vm_object_id) = entity_info(vc_node)

        vc_node.setCustomValue(key=key, value=value)
        if args.verbose > 2:
            print('{vm}: Set {key}=>{value}'.format(
                vm=vm_name,
                key=key,
                value=value
            ))


def find_node_by_path(vc_node, depth=1, path=[]):
    """
    Find node by path in vcenter tree using iterative BFS.
    """
    args = parser.parse_args()
    maxdepth = args.max_recursion

    while path:
        if depth > maxdepth:
            if args.verbose:
                print(
                    'Reached max recursive depth, bailing out like a banker',
                    file=stderr
                )
            return

        depth += 1

        # This stores the name of the class
        object_type = vc_node.__class__.__name__
        (node_name, node_object_id) = entity_info(vc_node)

        if object_type == 'vim.Datacenter':
            # Go through all the VM folders
            for _entity in vc_node.vmFolder.childEntity:
                (node_name, node_object_id) = entity_info(_entity)
                if node_name == path[0]:
                    path.pop(0)
                    vc_node = _entity
                    break

        if object_type == 'vim.Folder':
            # Traverse subfolders
            for _entity in vc_node.childEntity:
                (node_name, node_object_id) = entity_info(_entity)
                if node_name == path[0]:
                    path.pop(0)
                    vc_node = _entity
                    break

        if object_type == 'vim.VirtualApp':
            # Loop through VMs in this vApp
            for _entity in vc_node.vm:
                (node_name, node_object_id) = entity_info(_entity)
                if node_name == path[0]:
                    path.pop(0)
                    vc_node = _entity
                    break

    return vc_node


args = parser.parse_args()

if args.config_file:
    config.readfp(args.config_file)

if args.verbose > 1:
    print('Connecting to https://{user}@{host}:{port}/sdk/vimServiceVersions.xml'.format(
        user=config.get('vcenter', 'username'),
        port=config.getint('vcenter', 'port'),
        host=config.get('vcenter', 'hostname')
    ))

# Disable warnings for insecure certificates
requests.packages.urllib3.disable_warnings()

# Workaround for GH issue #235, self-signed cert
try:
    import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
except:
    import ssl
    context = ssl.create_default_context()
    context.verify_mode = ssl.CERT_NONE

si = SmartConnect(
    host=config.get('vcenter', 'hostname'),
    user=config.get('vcenter', 'username'),
    pwd=config.get('vcenter', 'password'),
    port=config.getint('vcenter', 'port'),
    sslContext=context
)

atexit.register(Disconnect, si)

content = si.RetrieveContent()
pathlist = args.vc_path.rstrip('/').lstrip('/').split('/')

for vc_node in content.rootFolder.childEntity:
    object_type = vc_node.__class__.__name__
    (node_name, node_object_id) = entity_info(vc_node)
    if node_name == pathlist[0]:
        pathlist.pop(0)
        node = find_node_by_path(vc_node, 1, pathlist)
        break
else:
    print('Node not found', file=stderr)
    exit(1)

cfm = content.customFieldsManager

# Check if field exists
for field in cfm.field:
    if field.type == 'str':
        if field.name == args.field_name:
            if args.verbose > 2:
                print('Found field {name}'.format(
                    name=args.field_name
                ))
            break
else:
    # Create field
    if args.verbose > 2:
        print('Did not find field {name}, creating it'.format(
            name=args.field_name
        ))
    cfm.AddCustomFieldDef(name = args.field_name, moType = vim.VirtualMachine)

tag(node, args.field_name, args.field_value)
