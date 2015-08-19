#!/usr/bin/env python
# Adds an attribute for all devices under a certain path in siptrack.
#
# by Stefan Midjich <swehack@gmail.com>

from __future__ import print_function

from sys import stderr, exit
from argparse import ArgumentParser, FileType, ArgumentDefaultsHelpFormatter
from ConfigParser import ConfigParser

import siptracklib

config = ConfigParser()

parser = ArgumentParser(
    description='Add attributes to devices in siptrack',
    epilog=('Example: ./add_attribute.py -d'
            ' \'Public Cloud:Devices:Customer\' \'customername=ABC\''
            ''
            'by Stefan Midjich <swehack@gmail.com>'),
    formatter_class=ArgumentDefaultsHelpFormatter
)

parser.add_argument(
    '-d', '--dry-run',
    action='store_true',
    default=False,
    dest='dry_run',
    help='Only do a dry-run, do not store any data in siptrack'
)

parser.add_argument(
    '-c', '--config-file',
    type=FileType('r'),
    required=True,
    help='Configuration file for siptrack connection information.'
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    default=False,
    help='Verbose output, use more v\'s to increase level of verbosity.'
)

parser.add_argument(
    '-i', '--important',
    action='store_true',
    default=False,
    help='Store attribute as "Important" so it appears in device view.'
)

parser.add_argument(
    '-p', '--device-path',
    action='store',
    required=True,
    help='Device path in siptrack to use as root.'
)

parser.add_argument(
    '-r', '--recursive',
    action='store_true',
    default=False,
    help='Recursively add an attribute to devices in any sub category.'
)

parser.add_argument(
    'key_value',
    action='store',
    metavar='key=value',
    help='Key=value form of attribute name and the value you wish to assign.'
)

parser.add_argument(
    '-s', '--path-separator',
    action='store',
    default=':',
    dest='path_separator',
    help='Path separator to use in -d argument (siptrack device path).'
)


def add_attribute(st_root, attribute, value, include=[], exclude=[]):
    """
    Recurse through the siptrack device category provided and add an attribute
    to each device found.
    """
    args = parser.parse_args()

    # First set the attribute on all devices
    for _child in st_root.listChildren(include=include):
        try:
            st_value = _child.attributes[attribute]
        except (AttributeError, TypeError) as e:
            st_value = None
            pass

        if st_value is None and args.verbose > 1:
            print('{device}: Creating {attribute}: None => {value}'.format(
                device=_child.attributes['name'],
                attribute=attribute,
                value=value
            ))
        elif args.verbose > 1:
            print('{device}: Setting {attribute}: {st_value} => {value}'.format(
                device=_child.attributes['name'],
                attribute=attribute,
                st_value=st_value,
                value=value
            ))

        if args.dry_run and args.verbose:
            print('{device}: Dry-run: Not setting attribute'.format(
                device=_child.attributes['name']
            ))
        else:
            _child.attributes[attribute] = value
            if args.important:
                if args.verbose > 1:
                    print('{device}: Setting important flag on {attribute}'.format(
                        device=_child.attributes['name'],
                        attribute=attribute
                    ))
                attr_attributes = _child.attributes.getObject(attribute)
                attr_attributes.attributes['important'] = True

    # Then if recursive we try to find more device categories
    if args.recursive:
        for _category in st_root.listChildren(include=['device category']):
            add_attribute(_category, attribute, value,
                          include=include, exclude=exclude)


def main():
    args = parser.parse_args()

    attribute = args.key_value.split('=')[0]
    value = args.key_value.split('=')[1]

    if not len(attribute):
        print('Must have an attribute name, exiting', file=stderr)
        parser.print_help()
        exit(1)

    # Override configuration with file provided on cli
    if args.config_file:
        config.readfp(args.config_file)

    st = siptracklib.connect(
        config.get('siptrack', 'hostname'),
        config.get('siptrack', 'username'),
        config.get('siptrack', 'password'),
        use_ssl=config.get('siptrack', 'ssl')
    )

    # Find the root for siptrack operations
    st_view = st.view_tree.getChildByName(
        config.get('import', 'base_view'), include=['view']
    )

    # First device tree is usually [devices]
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

    add_attribute(st_root_category, attribute, value, include=['device'])

if __name__ == '__main__':
    main()
