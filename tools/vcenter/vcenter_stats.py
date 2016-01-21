#!/usr/bin/env python
# Gather vcenter stats and insert into elasticsearch index

from __future__ import print_function

import json
import atexit
from sys import exit, stderr
from argparse import ArgumentParser, FileType
from datetime import datetime

try:
    from urllib.parse import unquote
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
    from urllib import unquote
    pass

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from elasticsearch import Elasticsearch

config = RawConfigParser()
try:
    config.readfp(open('vcenter_stats.cfg'))
except:
    pass
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


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return JSONEncoder.default(self, obj)


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


def import_stats(vc_node, es):
    args = parser.parse_args()

    (vm_name, vm_object_id) = entity_info(vc_node)

    d = datetime.now()

    quickStats = vc_node.summary.quickStats
    stats = {}
    stats['timestamp'] = d
    stats['vm_name'] = vm_name
    stats['consumedOverheadMemory'] = quickStats.consumedOverheadMemory
    stats['distributedCpuEntitlement'] = quickStats.distributedCpuEntitlement
    stats['distributedMemoryEntitlement'] = quickStats.distributedMemoryEntitlement
    stats['guestMemoryUsage'] = quickStats.guestMemoryUsage
    stats['hostMemoryUsage'] = quickStats.hostMemoryUsage
    stats['overallCpuDemand'] = quickStats.overallCpuDemand
    stats['overallCpuUsage'] = quickStats.overallCpuUsage
    stats['privateMemory'] = quickStats.privateMemory
    stats['sharedMemory'] = quickStats.sharedMemory
    stats['staticCpuEntitlement'] = quickStats.staticCpuEntitlement
    stats['staticMemoryEntitlement'] = quickStats.staticMemoryEntitlement
    stats['swappedMemory'] = quickStats.swappedMemory
    stats['uptimeSeconds'] = quickStats.uptimeSeconds

    # Get storage stats for VM
    stats['storageCommitted'] = 0
    stats['storageUncommitted'] = 0
    try:
        storage = vc_node.storage.perDatastoreUsage
        stats['storageCommitted'] += storage[0].committed
        stats['storageUncommitted'] += storage[0].uncommitted
    except Exception as e:
        if args.verbose > 1:
            print(str(e))
        pass

    if args.verbose > 1:
        print(json.dumps(
            stats,
            sort_keys=True,
            indent=4,
            separators=(',', ': '),
            cls=DateEncoder
        ))

    es_res = es.index(
        index=d.strftime(config.get('elasticsearch', 'index')),
        doc_type=config.get('elasticsearch', 'doctype'),
        body=stats
    )

    if args.verbose and es_res['created']:
        print('{vm}: Created new index {index} in elasticsearch'.format(
            vm=vm_name,
            index=es_res
        ))
    elif args.verbose:
        print('{vm}: Imported data into elasticsearch: {data}'.format(
            vm=vm_name,
            data=es_res
        ))


def traverse_vc(vc_root, es, depth=1):
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

        # Go through all the VM folders
        for _entity in vc_root.vmFolder.childEntity:
            traverse_vc(_entity, es, depth+1)
        return

    if object_type == 'vim.Folder':
        (folder_name, folder_object_id) = entity_info(vc_root)

        # Traverse subfolders
        for _entity in vc_root.childEntity:
            traverse_vc(_entity, es, depth+1)
        return

    if object_type == 'vim.VirtualApp':
        (vapp_name, vapp_object_id) = entity_info(vc_root)

        # Loop through VMs in this vApp
        for _entity in vc_root.vm:
            traverse_vc(_entity, es, depth+1)
        return

    if object_type == 'vim.VirtualMachine':
        import_stats(vc_root, es)


def main():
    args = parser.parse_args()

    if args.config_file:
        config.readfp(args.config_file)

    if args.verbose > 1:
        print('Connecting to {host}'.format(
            host=config.get('vcenter', 'hostname')
        ))

    # Workaround for GH issue #235, self-signed cert
    try:
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        if args.verbose > 1:
            print('NOICE!')
    except:
        # Wheezy still not supported by this, barely even ubuntu trusty
        import ssl
        context = ssl.create_default_context()
        context.verify_mode = ssl.CERT_NONE
        if args.verbose > 1:
            print('Your version is fine for now')

    si = SmartConnect(
        host=config.get('vcenter', 'hostname'),
        user=config.get('vcenter', 'username'),
        pwd=config.get('vcenter', 'password'),
        port=config.getint('vcenter', 'port'),
        sslContext=context
    )

    atexit.register(Disconnect, si)

    es = Elasticsearch('http://{host}:{port}'.format(
        host=config.get('elasticsearch', 'host'),
        port=config.get('elasticsearch', 'port')
    ))

    content = si.RetrieveContent()
    for vc_node in content.rootFolder.childEntity:
        traverse_vc(vc_node, es)

if __name__ == '__main__':
    main()
