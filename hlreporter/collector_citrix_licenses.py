# hlreporter - Citrix license collector for www.monitorscout.com
# by Stefan Midjich <swehack@gmail.com>

import wmi
import win32com.client
from hlreporterlib import collector
from hlreporterlib import errors

HELP = """Collect stats on citrix licenses"""

# Make sure nothing is exported for this sample collector.
#collectors = []

# Add license types here to monitor them.
license_types = [
    ('MPS_ADV_CCU', 'Citrix XenApp Advanced | Concurrent'),
    ('MPS_ENT_CCU', 'Citrix XenApp Enterprise | Concurrent'),
    ('MPS_PLT_CCU', 'Citrix XenApp Platinum | Concurrent'),
    ('PVSD_STD_CCS', 'Citrix Provisioning Server for Desktops | Concurrent'),
    ('PVS_STD_CCS', 'Citrix Provisioning Services | Concurrent'),
    ('XDT_ENT_UD', 'Citrix XenDesktop Enterprise | User/Device'),
    #('XDS_ENT_CCS', 'Citrix XenDesktop Enterprise | Concurrent'), # Not sure about these
    #('CEHV_ENT_CCS', 'Citrix StorageLink Enterprise | Concurrent'), # Not sure about these
]

class CitrixLicenseCollector(collector.BaseCollector):
    name = 'citrix license collector'
    platforms = ['win32']

    # Required method, called when collecting data.
    def collect(self):
        self.root = self.device.initComponentGroup('applications').initComponentGroup('citrix')
        citrix = self.root.initComponent('citrix licenses')

        for (l_type, l_name) in license_types:
            (total, in_use) = self.collectLicenseInfo(license_type=l_type)
            free = total-in_use

            if total == 0:
                # System has no such licenses so skip counting them
                continue

            free_metric = citrix.initMetric(
                '{0} free'.format(
                    l_name
                ),
                free,
                'NUM_ABSOLUTE',
                'licenses'
            )
            in_use_metric = citrix.initMetric(
                '{0} in use'.format(
                    l_name
                ),
                in_use,
                'NUM_ABSOLUTE',
                'licenses'
            )
            total_metric = citrix.initMetric(
                '{0} total'.format(
                    l_name
                ),
                total,
                'NUM_ABSOLUTE',
                'licenses'
            )

            citrix.initMetricGraph(
                '{0} license usage'.format(
                    l_name
                ),
                [total_metric, in_use_metric, free_metric]
            )

    def collectLicenseInfo(self, license_type):
        total = 0
        in_use = 0

        wmi = win32com.client.Dispatch('WbemScripting.SWbemLocator')
        admin = wmi.ConnectServer('.', 'root\CitrixLicensing')
        licenses = admin.ExecQuery(
            'SELECT Count, InUseCount FROM Citrix_GT_License_Pool WHERE PLD = \'{0}\''.format(license_type)
        )

        for license in licenses:
            total = license.Count+total
            in_use = license.InUseCount+in_use

        return (total, in_use)

    # Only run collector if Citrix Licensing service is running on >= Win2k8
    def canCollect(self):
        c = wmi.WMI()
        if c.Win32_Service(Name='Citrix Licensing')[0].State == u'Running' and int(c.Win32_OperatingSystem()[0].version[0]) > 5:
            return True
        return False
