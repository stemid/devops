#!/usr/bin/env python
# Gather vcenter stats and insert into elasticsearch index

import json
import atexit
from sys import exit, stderr
from urllib.parse import unquote
from argparse import ArgumentParser, FileType
from configparser import RawConfigParser

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

config = RawConfigParser()
config.readfp(open('vcenter_stats.cfg'))
config.read(['/etc/vcenter_stats.cfg', './vcenter_stats.local.cfg'])

parser = ArgumentParser(
    description=('Gather statistics about VMs from vcenter and insert '
                 'into elasticsearch'),
    epilog='Example: ./vcenter_stats.py -c config.cfg'
)

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


def entity_info(vc_entity):
    """
    entity_info - get name information from a vcenter entity

    vc_entity - any vcenter entity
    """

    obj_id = str(vc_entity).split(':')[1].rstrip('\'')
    vc_name = unquote(vc_entity.name)

    # The Unicode madness is for siptrack
    return (
        vc_name.encode('utf-8'),
        obj_id.encode('utf-8')
    )


def import_stats(vc_node):
    (vm_name, vm_object_id) = entity_info(vc_node)

    stats = vc_node.summary.quickStats
    print('{vm}: consumedOverheadMemory: {mem}'.format(
        vm=vm_name,
        mem=stats.consumedOverheadMemory
    ))
    print(dir(stats))
    return


def traverse_vc(vc_root, depth=1):
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
    object_type = vc_root.__class__.__name__

    if object_type == 'vim.Datacenter':
        (datacenter_name, datacenter_object_id) = entity_info(vc_root)

        st_dc = st_root.getChildByName(datacenter_name)

        # Go through all the VM folders
        for _entity in vc_root.vmFolder.childEntity:
            traverse_vc(_entity, depth+1)
        return

    if object_type == 'vim.Folder':
        (folder_name, folder_object_id) = entity_info(vc_root)

        # Traverse subfolders
        for _entity in vc_root.childEntity:
            traverse_vc(_entity, depth+1)
        return

    if object_type == 'vim.VirtualApp':
        (vapp_name, vapp_object_id) = entity_info(vc_root)

        # Loop through VMs in this vApp
        for _entity in vc_root.vm:
            traverse_vc(_entity, depth+1)
        return

    if object_type == 'vim.VirtualMachine':
        import_stats(vc_root)

def main():
    args = parser.parse_args()

    if args.config_file:
        config.readfp(args.config_file)

    if args.verbose > 1:
        print('Connecting to {host}'.format(
            host=config.get('vcenter', 'hostname')
        ))

    try:
        si = SmartConnect(
            host=config.get('vcenter', 'hostname'),
            user=config.get('vcenter', 'username'),
            pwd=config.get('vcenter', 'password'),
            port=config.getint('vcenter', 'port')
        )
    except Exception as e:
        # Workaround for GH issue#212
        if isinstance(e, vim.fault.HostConnectFault) and '[SSL: CERTIFICATE_VERIFY_FAILED]' in e.msg:
            try:
                import ssl
                default_context = ssl._create_default_https_context
                ssl._create_default_https_context = ssl._create_unverified_context
                si = SmartConnect(
                    host=config.get('vcenter', 'hostname'),
                    user=config.get('vcenter', 'username'),
                    pwd=config.get('vcenter', 'password'),
                    port=config.getint('vcenter', 'port')
                )
                ssl._create_default_context = default_context
            except Exception as _e:
                raise Exception(_e)
        else:
            print(
                'Could not connect to vcenter server: {0}'.format(
                    str(e)
                ),
                file=stderr
            )
            raise Exception(e)

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    for vc_node in content.rootFolder.childEntity:
        traverse_vc(vc_node)

if __name__ == '__main__':
    main()
