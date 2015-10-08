# hlreporter - HP RAID collector for www.monitorscout.com
# by Stefan Midjich <swehack@gmail.com>
#
# Depends on the hpacucli tool from HP Linux repos
# 

import os

from hlreporterlib import collector
from hlreporterlib import errors

hpacucli_path = '/usr/sbin/hpacucli'

class HPRAIDCollector(collector.BaseCollector):
    name = 'HP RAID collector'
    platforms = ['linux']

    def collect(self):
        self.root = self.device.initComponentGroup('hardware')
        self.root = self.root.initComponentGroup('hp')
        raid = self.root.initComponent('raid')
        pass

    def collectRAIDStatus(self):
        command = '{0} controller all show status'.format(hpacucli_path)

    def canCollect(self):
        return os.path.isfile(hpacucli_path) and os.access(hpacucli_path, (os.X_OK&os.R_OK))
