### Author: Dmitry Fedin <dmitry.fedin@gmail.com>


class dstat_plugin(dstat):
    ibdirname = '/sys/class/infiniband'
    netdirname = '/sys/class/net'
    """
    Bytes received or sent through infiniband/RoCE interfaces
    Usage:
        dstat --ib -N <adapter name>:<port>,total
        default dstat --ib is the same as
        dstat --ib -N total

        example for Mellanox adapter, transfering data via port 2
        dstat --ib -Nmlx4_0:2
    """

    def __init__(self):
        self.nick = ('recv', 'send')
        self.type = 'd'
        self.cols = 2
        self.width = 6

    def discover(self, *objlist):
        ret = []
        for subdirname in os.listdir(self.ibdirname):
            if not os.path.isdir(os.path.join(self.ibdirname,subdirname)) : continue
            device_dir =  os.path.join(self.ibdirname, subdirname, 'ports')
            for subdirname2 in os.listdir(device_dir) :
                if not os.path.isdir(os.path.join(device_dir,subdirname2)): continue
                name = subdirname + ":" + subdirname2
                ret.append(name)
        ret.sort()
        for item in objlist: ret.append(item)
        return ret

    def vars(self):
        ret = []
        if op.netlist:
            varlist = op.netlist
        elif not op.full:
            varlist = ('total',)
        else:
            varlist = self.discover
            varlist.sort()
        for name in varlist:
            if name in self.discover + ['total']:
                ret.append(name)
        if not ret:
            raise Exception, "No suitable network interfaces found to monitor"
        return ret


    def name(self):
        return ['ib/'+name for name in self.netcardFind() ]

    def extract(self):
        self.set2['total'] = [0, 0]
        ifaces = self.discover
        for name in self.vars: self.set2[name] = [0, 0]
        for name in ifaces:
            l=name.split(':');
            if len(l) < 2:
                 continue
            if os.path.exists('/sys/class/infiniband/' + l[0] + '/ports/' + l[1] + '/counters_ext'):
                rcv_counter_name=os.path.join('/sys/class/infiniband', l[0], 'ports', l[1], 'counters_ext/port_rcv_data_64')
                xmit_counter_name=os.path.join('/sys/class/infiniband', l[0], 'ports', l[1], 'counters_ext/port_xmit_data_64')
            else:
                rcv_counter_name=os.path.join('/sys/class/infiniband', l[0], 'ports', l[1], 'counters/port_rcv_data')
                xmit_counter_name=os.path.join('/sys/class/infiniband', l[0], 'ports', l[1], 'counters/port_xmit_data')
            rcv_lines = dopen(rcv_counter_name).readlines()
            xmit_lines = dopen(xmit_counter_name).readlines()
            if len(rcv_lines) < 1 or len(xmit_lines) < 1:
                continue
            rcv_value = long(rcv_lines[0])
            xmit_value = long(xmit_lines[0])
            if name in self.vars :
                self.set2[name] = (rcv_value, xmit_value)
            self.set2['total'] = ( self.set2['total'][0] + rcv_value, self.set2['total'][1] + xmit_value)
        if update:
            for name in self.set2:
                self.val[name] = [
                    (self.set2[name][0] - self.set1[name][0]) * 4.0 / elapsed,
                    (self.set2[name][1] - self.set1[name][1]) * 4.0/ elapsed,
                ]
                if self.val[name][0] < 0: self.val[name][0] += maxint + 1
                if self.val[name][1] < 0: self.val[name][1] += maxint + 1
        if step == op.delay:
            self.set1.update(self.set2)

    def ibMac(self):
        ret = []
        for subdirname in os.listdir(self.ibdirname):
            if not os.path.isdir(os.path.join(self.ibdirname,subdirname)) : continue
            macAddress = open(self.ibdirname + "/" + subdirname + "/node_guid").read()
            macAddress = macAddress.replace(":","")
            macAddress = macAddress[0:6] + macAddress[10:16]
            ret.append(macAddress + ":" + subdirname)
        return ret

    def netcardFind(self):
        cardMac = []
        nameList = []
        ipList = []
        ret = []
        for subdirname in os.listdir(self.netdirname):
            if not os.path.isdir(os.path.join(self.netdirname,subdirname)) : continue
            macAddress = open(self.netdirname + "/" + subdirname + "/address").read()
            macAddress = macAddress.replace(":","")
            cardMac.append(macAddress + ":" + subdirname)
        ibmac = self.ibMac()
        for addressIb in ibmac:
            addressIbSplit = addressIb.split(":")
            ibName = addressIbSplit[1]
            addressIb = addressIbSplit[0]
            for addressCard in cardMac:
                addressCardSplit = addressCard.split(":")
                name = addressCardSplit[1]
                addressNetcard = addressCardSplit[0][0:12]
                if addressIb == addressNetcard:
                    nameList.append(ibName + ":" + name)
        if not nameList:
            raise Exception, "No suitable network card found to match..."
        for name in nameList:
            ipAddress = os.popen("ifconfig " + name.split(":")[1] + " | grep 'inet addr'").readline()
            ipAddress = ipAddress.split(":")[1].split(" ")[0]
            ipList.append(name.split(":")[0] + ":" + ipAddress)
        for ibport in self.vars:
            if ibport == 'total':
                ret.append('total')
                continue
            ibname = ibport.split(":")[0]
            port = ibport.split(":")[1]
            for ipName in ipList:
                ipIb = ipName.split(":")[0]
                ip = ipName.split(":")[1]
                if ibname == ipIb:
                    ret.append(ip[8:] + ":" + port)
        return ret
