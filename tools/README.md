Assorted mix of tools. 

# vCenter import (vcenter_import.py)

Import script from vcenter to [siptrack](https://github.com/sii/siptrackweb). 

Development of this script takes place in a private repo so I sometimes copy it to this repo so people can see a good example use of siptracklib and pyvmomi. 

See default configuration file import_defaults.cfg for comments. 

Requires pyvmomi and siptracklib installed.

Install both [siptrack](https://github.com/sii/siptrack) and [siptracklib](https://github.com/sii/siptrackd). 

    pip install pyvmomi

## Known issues

Dry-run does not work if new datacenters, clusters or folders have been added. 

## Example run

Here I have a siptrack path of Public Cloud/VMware so everything will end up under the VMware device category. 

I also have my own configuration file for my datacenter called vcenter_mydatacenter.cfg. 

    python vcenter_import.py -d 'Public Cloud:VMware' -c vcenter_mydatacenter.cfg
