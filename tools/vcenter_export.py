# coding: utf-8
# This tool is made to export data from vcenter API into a report in either
# CSV or JSON format. 
# 
# Most options are from configuration file.
# 
# by Stefan Midjich <swehack@gmail.com>

from __future__ import print_function

import json
import atexit
from sys import exit, stderr
from urllib import unquote
from argparse import ArgumentParser
from ConfigParser import ConfigParser
from pprint import pprint

from pyVim.connect import SmartConnect, Disconnect

config = ConfigParser()
config.readfp(open('export_defaults.cfg'))
config.read(['/etc/vcenter_export.cfg', './export_local.cfg'])

parser = ArgumentParser(
    description='Export devices from vcenter into a reportable format',
    epilog='Example: ./vcenter_export.py -d \'Public Cloud:Devices\''
)

parser.add_argument(
    '-V', '--verbose',
    action='store_true',
    default=False,
    dest='verbose',
    help='Verbose output'
)

parser.add_argument(
    '-c', '--configuration',
    type=file,
    dest='config_file',
    help='Additional configuration options'
)

parser.add_argument(
    '-d', '--device-path',
    action='store',
    required=True,
    dest='device_path',
    help=('Path to the device category to use as root for the export. '
          'Separate path components with : (semicolon) by default.'
          'Example: -d \'Public Cloud:Devices\'')
)

parser.add_argument(
    '-s', '--path-separator',
    action='store',
    default=':',
    dest='path_separator',
    help='Path separator to use in -d argument (vcenter path path).'
)

class ExportData(object):
    def __init__(self):
        data = {}
        data['current_path'] = []


# Recursively traverse vm entities from vcenter (datacenters, clusters,
# folders, vms)
def traverse_entities(vc_root, data, depth=1):
    args = parser.parse_args()

    # Recursive depth limit
    maxdepth = 16

    if depth > maxdepth:
        if args.verbose:
            print(
                'Reached max recursive depth, bailing out like a banker',
                file=stderr
            )
        return

    # This attribute is only present in datacenter objects
    if hasattr(vc_root, 'hostFolder'):
        # This is unicode madness
        datacenter_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        # Continue recursively to subfolders
        for _entity in vc_root.vmFolder.childEntity:
            traverse_entities(_entity, data, depth+1)
        return

    # This attribute is only present in Folders
    if hasattr(vc_root, 'childEntity'):
        folder_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        # Traverse subfolders of this folder
        for _entity in vc_root.childEntity:
            traverse_entities(_entity, data, depth+1)
        return

    # This attribute is only present in vApps (resource groups)
    if hasattr(vc_root, 'vAppConfig'):
        vapp_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        for _entity in vc_root.vm:
            traverse_entities(_entity, data, depth+1)
        return

    # All other entities are assumed to be VM
    vm = vc_root
    vm_name = unquote(vm.name)

    # The following code gathers information about the VM from various 
    # attributes of the VirtualMachine object in vcenter. 
    if hasattr(vm, 'runtime'):
        runtime = vm.runtime

        # Get cluster name of VM
        try:
            cluster_name = runtime.host.parent.name
        except AttributeError:
            cluster_name = ''

        st_attribute(st_vm, 'VM Cluster', cluster_name)

        # Get last VM power state, this is only interesting because newly 
        # imported VMs will lack guest info like IP and networks if they're
        # powered off at import. 
        try:
            power_state = str(runtime.powerState)
        except AttributeError:
            power_state = ''

        st_attribute(st_vm, 'Last Power state', power_state)

    if hasattr(vm, 'config'):
        config = vm.config

        st_attribute(st_vm, 'vcenter_uuid', config.uuid, important=False)

        # OS Name
        if hasattr(config, 'guestFullName'):
            st_attribute(st_vm, 'OS', config.guestFullName)

        # VM Description field from vcenter
        if hasattr(config, 'annotation'):
            vm_description = config.annotation
            st_attribute(st_vm, 'description', vm_description)

        # Add some hardware info if available
        if hasattr(config, 'hardware'):
            st_attribute(st_vm, 'CPU', config.hardware.numCPU)
            st_attribute(st_vm, 'Cores', config.hardware.numCoresPerSocket)
            st_attribute(st_vm, 'RAM', config.hardware.memoryMB)

            # Loop through all hardware devices
            for _device in config.hardware.device:
                device_name = _device.deviceInfo.label
                device_hw_id = _device.key

                # Must be some sort of NIC right? ;)
                if hasattr(_device, 'macAddress'):
                    st_device = None

                    # First check for duplicate device by unique device ID
                    for _st_device in st_vm.listChildren(include=['device']):
                        if _st_device.attributes['deviceConfigId'] == device_hw_id:
                            st_device = _st_device
                            break
                    else:
                        # Then try to find an existing device by name
                        st_device = st_vm.getChildByName(device_name)

                    # If all else fails, add device
                    if not st_device:
                        st_device = st_vm.add('device')
                        st_device.attributes['deviceConfigId'] = device_hw_id

                        if args.verbose:
                            print(
                                '{0}: Added hardware device'.format(vm_name),
                                file=stderr
                            )

                    # Reset attributes even if device previously existed
                    st_device.attributes['name'] = device_name
                    st_device.attributes['class'] = 'interface'
                    st_attribute(st_device, 'description', 'Virtual NIC')

    # Attribute present if VMware tools reports guest info. This is required
    # to properly link NICs with IP-addresses and networks in Siptrack. 
    if hasattr(vm, 'guest'):
        guest = vm.guest


def main():
    args = parser.parse_args()

    # Override configuration with file provided on cli
    if args.config_file:
        config.readfp(args.config_file)

    try:
        si = SmartConnect(
            host=config.get('vcenter', 'hostname'),
            user=config.get('vcenter', 'username'),
            pwd=config.get('vcenter', 'password'),
            port=int(config.get('vcenter', 'port'))
        )
    except Exception as e:
        print(
            'Could not connect to vcenter server: {0}'.format(
                str(e)
            ),
            file=stderr
        )
        exit(-1)

    atexit.register(Disconnect, si)

    data = ExportData()

    content = si.RetrieveContent()
    # Loop through each parent entity recursively
    for child in content.rootFolder.childEntity:
        traverse_entities(child, data)


if __name__ == '__main__':
    main()
