# coding: utf-8
# Most options are from configuration file.
#   * ./import_defaults.cfg
#   * /etc/siptrack_import.cfg
#   * ./import_local.cfg (local overrides)
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

import siptracklib
from pyVim.connect import SmartConnect, Disconnect

config = ConfigParser()
config.readfp(open('import_defaults.cfg'))
config.read(['/etc/siptrack_import.cfg', './import_local.cfg'])

parser = ArgumentParser(
    description='Import devices from vcenter into siptrack',
    epilog='Example: ./vcenter_import.py -d \'Public Cloud:Devices\''
)

parser.add_argument(
    '-r', '--dry-run',
    action='store_true',
    default=False,
    dest='dry_run',
    help='Only do a dry-run, do not store any data in siptrack'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    dest='verbose',
    help='Verbose output, use more v\'s to increase level'
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
    help=('Path to the device category to use as root for the import. '
          'Separate path components with : (semicolon) by default.'
          'Example: -d \'Public Cloud:Devices\'')
)

parser.add_argument(
    '-s', '--path-separator',
    action='store',
    default=':',
    dest='path_separator',
    help='Path separator to use in -d argument (siptrack device path).'
)


# Updating attributes in siptrack with optional default value
def st_attribute(st_entity, attribute, value=None, **kwargs):
    if not value:
        value = kwargs.get('default', '')

    if st_entity.attributes.get(attribute, '') != value:
        st_entity.attributes[attribute] = value
        attributes = st_entity.attributes.getObject(attribute).attributes
        attributes['important'] = kwargs.get('important', True)


def add_network_info(st_device, st_nt, vm_network):
    args = parser.parse_args()
    network_name = vm_network.network

    # This probably indicates that VMware tools needs to be restarted
    if not network_name:
        if args.verbose:
            print('Found network with no name! Skipping.', file=stderr)
        return

    if not hasattr(vm_network.ipConfig, 'ipAddress'):
        return

    for _ip in vm_network.ipConfig.ipAddress:
        ip_address = _ip.ipAddress
        cidr_suffix = _ip.prefixLength

        # Skip ipv6 addresses for now
        if ':' in ip_address:
            continue

        # FIXME: Use ipaddr for this perhaps, also adds support for ipv6
        ip_cidr = '{0}/32'.format(ip_address)
        net_cidr = '{0}/{1}'.format(ip_address, cidr_suffix)

        # First add network if it does not exist
        st_network = st_nt.getNetwork(net_cidr, create_if_missing=False)
        if not st_network:
            st_network = st_nt.addNetwork(net_cidr)

            if args.verbose:
                print('{0}: Imported network'.format(network_name))

        st_network.attributes['description'] = network_name

        # Then associate ip-address with subdevice
        st_ip = st_nt.getNetwork(ip_cidr, create_if_missing=True)
        try:
            st_device.associate(st_ip)
        except siptracklib.errors.SiptrackError:
            if args.verbose == 2:
                print('{0}: Network already associated'.format(
                    network_name
                ), file=stderr)

        st_ip.attributes['description'] = network_name


# Recursively traverse vm entities from vcenter (datacenters, clusters,
# folders, vms)
def traverse_entities(st_root, st_dt, st_nt, vc_root, depth=1):
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

    # This stores the name of the class
    object_type = vc_root.__class__.__name__

    # This attribute is only present in datacenter objects
    if object_type == 'vim.Datacenter':
        # This is unicode madness
        datacenter_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        # Find out if device category exists for this datacenter
        st_dc = st_root.getChildByName(datacenter_name)

        # If it does not exist, create it
        if not st_dc:
            if args.dry_run:
                print('{0}: Dry-run, skipping import of datacenter'.format(
                    datacenter_name
                ))
            else:
                st_dc = st_root.add('device category')
                st_attribute(st_dc, 'name', datacenter_name)

                if args.verbose:
                    print('{0}: Imported datacenter'.format(datacenter_name.encode('utf-8')))

        if args.dry_run:
            print('{0}: Dry-run, skipping reset of datacenter attributes'.format(
                datacenter_name
            ))
        else:
            st_attribute(st_dc, 'description', 'vCenter Datacenter')
            st_attribute(st_dc, 'class', 'vm datacenter')

        # First recurse through clusters
        for _entity in vc_root.hostFolder.childEntity:
            traverse_entities(st_dc, st_dt, st_nt, _entity, depth+1)

        # Continue recursively to subfolders
        for _entity in vc_root.vmFolder.childEntity:
            traverse_entities(st_dc, st_dt, st_nt, _entity, depth+1)
        return

    # This attribute appears in ClusterComputerResource objects, clusters
    if object_type == 'vim.ClusterComputeResource':
        cluster_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        st_cluster = st_root.getChildByName(cluster_name)

        if not st_cluster:
            if args.dry_run:
                print('Dry-run, skipping import of cluster')
            else:
                st_cluster = st_root.add('device category')
                st_attribute(st_cluster, 'name', cluster_name)

                if args.verbose:
                    print('{0}: Imported cluster'.format(cluster_name.encode('utf-8')))

        if args.dry_run:
            print('Dry-run, skipping reset of cluster attributes')
        else:
            st_attribute(st_cluster, 'description', 'vCenter Cluster')
            st_attribute(st_cluster, 'class', 'vm cluster')

        # Loop through hosts in this cluster
        for _entity in vc_root.host:
            traverse_entities(st_cluster, st_dt, st_nt, _entity, depth+1)
        return

    # ESX host object name
    if object_type == 'vim.HostSystem':
        host_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        # Find the ESX host in global siptrack
        results = st_dt.search(host_name.encode('utf-8'), include=['device'])
        if not results:
            if args.verbose:
                print('{0}: Host not found, could not link'.format(
                    host_name.encode('utf-8')
                ))
        else:
            # Loop through search results to find an exact match
            for result in results:
                if result.attributes['name'] == host_name:
                    if args.verbose == 2:
                        print('{0}: Found matching host'.format(
                            host_name.encode('utf-8')
                        ))
                    if args.dry_run:
                        print('Dry-run, skipping link of ESX host')
                    else:
                        try:
                            st_root.associate(result)
                        except siptracklib.errors.SiptrackError:
                            if args.verbose:
                                print(
                                    '{0}: Host already linked to cluster'.format(
                                        host_name.encode('utf-8')
                                    ))
                        else:
                            if args.verbose:
                                print('{0}: Linked host to cluster'.format(
                                    host_name.encode('utf-8')
                                ))
        return

    # This attribute is only present in Folders
    if object_type == 'vim.Folder':
        folder_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        # Find device category
        st_folder = st_root.getChildByName(folder_name)

        # Create if not exists
        if not st_folder:
            if args.dry_run:
                print('Dry-run, skipping import of folder')
            else:
                st_folder = st_root.add('device category')
                st_attribute(st_folder, 'name', folder_name)

                if args.verbose:
                    print('{0}: Imported folder'.format(folder_name.encode('utf-8')))

        if args.dry_run:
            print('Dry-run, skipping reset of folder attributes')
        else:
            st_attribute(st_folder, 'description', 'vCenter Folder')
            st_attribute(st_folder, 'class', 'vm folder')

        # Traverse subfolders of this folder
        for _entity in vc_root.childEntity:
            traverse_entities(st_folder, st_dt, st_nt, _entity, depth+1)
        return

    # This attribute is only present in vApps (resource groups)
    if object_type == 'vim.VirtualApp':
        vapp_name = unquote(vc_root.name).encode('utf-8').decode('utf-8')

        st_vapp = st_root.getChildByName(vapp_name)

        if not st_vapp:
            if args.dry_run:
                print('Dry-run, skipping import of vApp')
            else:
                st_vapp = st_root.add('device category')
                st_attribute(st_vapp, 'name', vapp_name)

                if args.verbose:
                    print('{0}: Imported vApp resource group'.format(vapp_name.encode('utf-8')))

        if args.dry_run:
            print('Dry-run, skipping reset of vApp attributes')
        else:
            st_attribute(st_vapp, 'description', 'vCenter VirtualApp')
            st_attribute(st_vapp, 'class', 'virtual appliance')

        for _entity in vc_root.vm:
            traverse_entities(st_vapp, st_dt, st_nt, _entity, depth+1)
        return

    # The rest should only be Virtual Machines
    if object_type != 'vim.VirtualMachine':
        return

    vm = vc_root
    vm_name = unquote(vm.name)

    # Find out if VM already exists in category
    st_vm = st_root.getChildByName(vm_name)

    # Find out if VM has changed name in same vfolder
    if not st_vm:
        try:
            st_vm = st_root.getChildByAttribute('vcenter_uuid', vm.config.uuid)
        except AttributeError:
            if args.verbose:
                print(
                    '{0}: No config.uuid attribute, failed searching for duplicates'.format(
                        vm_name
                    ), file=stderr
                )
            st_vm = None

    if args.dry_run:
        print('Dry-run, skipping import of VM')
        return

    # If not found, create new VM
    if not st_vm:
        st_vm = st_root.add('device')

        if args.verbose:
            print('{0}: Imported VM'.format(vm_name))

    # Reset some values for VMs
    st_attribute(st_vm, 'name', vm_name)
    st_vm.attributes['description'] = 'Virtual Machine'
    st_vm.attributes['class'] = 'virtual server'
    st_vm.attributes['generate backup'] = False
    st_vm.attributes['generate dns'] = False
    st_vm.attributes['not in snow'] = True
    st_vm.attributes['skip_link_check'] = True
    st_vm.attributes['skip_rack_check'] = True
    st_vm.attributes['vcenter_id'] = str(vm).split(':')[1]

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

        st_attribute(st_vm, 'vcenter_uuid', config.instanceUuid, important=False)

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

                        if args.verbose == 2:
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

        # Set primary IP as important attribute
        st_attribute(st_vm, 'Primary IP', guest.ipAddress)

        # Loop through network adapters
        if hasattr(guest, 'net'):
            # Loop through network adapters and IP-addresses
            for _net in guest.net:
                network_name = _net.network
                hw_dev_id = _net.deviceConfigId

                for _st_device in st_vm.listChildren(include=['device']):
                    if _st_device.attributes['deviceConfigId'] == hw_dev_id:
                        st_device = _st_device
                        break
                else:
                    if args.verbose:
                        print(
                            '{0}: Found unlinked NIC in OS: {1}'.format(
                                vm_name,
                                network_name
                            ),
                            file=stderr
                        )
                        continue

                if hasattr(_net, 'ipConfig'):
                    add_network_info(st_device, st_nt, _net)


def main():
    args = parser.parse_args()

    # Override configuration with file provided on cli
    if args.config_file:
        config.readfp(args.config_file)

    if args.verbose == 2:
        print('Connecting to {0}'.format(
            config.get('vcenter', 'hostname')
        ))
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

    st = siptracklib.connect(
        config.get('siptrack', 'hostname'),
        config.get('siptrack', 'username'),
        config.get('siptrack', 'password'),
        use_ssl=False
    )

    # Find the root for siptrack operations
    st_view = st.view_tree.getChildByName(
        config.get('import', 'base_view'), include=['view']
    )
    st_dt = st_view.listChildren(include=['device tree'])[0]
    _st_com = st_dt

    # Find the last component of the device category path
    for com in args.device_path.split(args.path_separator):
        _st_com = _st_com.getChildByName(com.encode('utf-8'))
        if not _st_com:
            if args.verbose:
                print('Device path not found, exiting', file=stderr)
            exit(1)

    st_root_category = _st_com

    # Find the network tree to use
    st_nt = st_view.getChildByName(
        # Siptrack is picky about the unicode attribute values
        config.get('import', 'network_tree').decode('utf-8'),
        include=['network tree']
    )

    # Create network tree if not found
    if not st_nt:
        if args.verbose:
            print('Could not find network tree {0}, creating it'.format(
                config.get('import', 'network_tree')
            ))

        if args.dry_run:
            print('Dry-run, skipping creation of network tree')
        else:
            st_nt = st_view.add('network tree', 'ipv4')
            st_nt.attributes['name'] = config.get('import', 'network_tree')

    content = si.RetrieveContent()
    # Loop through each parent entity recursively
    for child in content.rootFolder.childEntity:
        traverse_entities(st_root_category, st_dt, st_nt, child)


if __name__ == '__main__':
    main()
