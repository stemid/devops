# hlreporter - HP RAID collector for www.monitorscout.com
# by Stefan Midjich <swehack@gmail.com>
#
# Depends on the hpacucli tool from HP Linux repos
# 

import os
import subprocess

from hlreporterlib import collector
from hlreporterlib import errors

hpacucli_path = '/usr/sbin/hpacucli'

class HPRAIDCollector(collector.BaseCollector):
    name = 'HP RAID collector'
    platforms = ['linux']

    def _parseOutput(self, data):
        for line in data.split('\n'):
            controller = None
            if len(line):
                if line.startswith('Smart'):
                    controller = line
        pass

    def collect(self):
        self.root = self.device.initComponentGroup('hardware')
        self.root = self.root.initComponentGroup('hp')
        raid = self.root.initComponent('raid')
        pass

    def collectRAIDStatus(self):
        command = '{0} controller all show status'.format(hpacucli_path)
        output = subprocess.Popen(command.split(' '), stdout=subprocess.PIPE)
        return self._parseOutput(output)

    def canCollect(self):
        return os.path.isfile(hpacucli_path) and os.access(hpacucli_path, (os.X_OK&os.R_OK))
