#!/usr/bin/env python3
# This tool tags an entire path of devices with a certain given tag and value.
#
# by Stefan Midjich <swehack@gmail.com> - 2016

import atexit
from urllib.parse import unquote
from configparser import RawConfigParser
from argparse import ArgumentParser, FileType

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

parser = ArgumentParser(
    description='Tag any vcenter VM object under a specific path',
    epilog=''
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
    help='Additional configuration options'
)

parser.add_argument(
    '-m', '--max-recursion',
    default=16,
    dest='max_recursion',
    type=int,
    help='Max recursion depth when traversing vcenter entities.'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level'
)

parser.add_argument(
    '-p', '--path',
    required=True,
    dest='vc_path',
    help='Vcenter path to tag all items under.'
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


def traverse_vc(vc_node, depth=1):
    args = parser.parse_args()

    maxdepth = args.max_recursion

    if depth > maxdepth:
        if args.verbose:
            print(
                'Reached max recursive depth, bailing out like a banker',
                file=stderr
            )
        return

    # This stores the name of the class
    object_type = vc_node.__class__.__name__

    if object_type == 'vim.Datacenter':
        (datacenter_name, datacenter_object_id) = entity_info(vc_node)

        # Go through all the VM folders
        for _entity in vc_node.vmFolder.childEntity:
            traverse_vc(_entity, depth+1)
        return

    if object_type == 'vim.Folder':
        (folder_name, folder_object_id) = entity_info(vc_node)

        # Traverse subfolders
        for _entity in vc_node.childEntity:
            traverse_vc(_entity, depth+1)
        return

    if object_type == 'vim.VirtualApp':
        (vapp_name, vapp_object_id) = entity_info(vc_node)

        # Loop through VMs in this vApp
        for _entity in vc_node.vm:
            traverse_vc(_entity, depth+1)
        return

    if object_type == 'vim.VirtualMachine':
        (vm_name, vm_object_id) = entity_info(vc_node)
        print(vm_name, object_type)


args = parser.parse_args()

if args.config_file:
    config.readfp(args.config_file)

if args.verbose > 1:
    print('Connecting to https://{user}@{host}:{port}/sdk/vimServiceVersions.xml'.format(
        user=config.get('vcenter', 'username'),
        port=config.getint('vcenter', 'port'),
        host=config.get('vcenter', 'hostname')
    ))

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
for vc_node in content.rootFolder.childEntity:
    traverse_vc(vc_node)

