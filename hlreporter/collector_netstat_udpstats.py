"""
Collect stats from netstat -su. Requires sh module installed.
"""

from re import match
from io import StringIO

can_collect = True

try:
    from sh import netstat
except ImportError:
    can_collect = False

from hlreporterlib import collector
from hlreporterlib import errors


class NetstatUDPCollector(collector.BaseCollector):
    name = 'netstat UDP stats'
    platforms = ['linux']

    def canCollect(self):
        return can_collect


    def collect(self):
        self.hw = self.device.initComponentGroup('hardware')
        self.net = self.hw.initComponentGroup('network')
        self.root = self.net.initComponentGroup('netstat')
        component = self.root.initComponent('udpstats')

        udp_data = self.run_netstat()
        aggr = []

        for data in udp_data:
            out = component.initMetric(
                data['key'],
                int(data['value']),
                'NUM_COUNTER',
                data['key']+'/s',
                value_per_interval=1
            )
            aggr.append(out)

        component.initMetricGraph('udp', aggr)


    def run_netstat(self):
        buf = StringIO()
        netstat(u'-su', _out=buf)
        buf.seek(0)
        data = []

        donot_parse = True
        for line in buf:
            line = line.rstrip('\n')

            if line.startswith('Udp:'):
                donot_parse = False
                continue

            if line.startswith('UdpLite:'):
                donot_parse = True

            if donot_parse:
                continue

            m = match(r'^\s*([0-9]+)\b([^$]+)$', line)
            if not m:
                continue

            data.append({
                'key': m.group(2).strip(' '),
                'value': m.group(1).strip(' ')
            })

        return data

