"""
Copyright (c) 2016 Glen Rice

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import socket
import threading
import struct
import operator
import time
import datetime as dt

import udp_io
import packet_handler as ph

class km_io(udp_io.udp_io):

    def __init__(self, listen_port, desired_datagrams, timeout):

        udp_io.udp_io.__init__(self, listen_port, desired_datagrams, timeout)

        # A few Nones to accommodate the potential types of datagrams
        # that are currently supported
        self.surface_ssp = None
        self.nav = None
        self.svp = None
        self.installation = None
        self.runtime = None
        self.svp_input = None
        self.xyz88 = None
        self.range_angle78 = None
        self.seabed_imagery89 = None
        self.watercolumn = None
        self.bist = None

        self.dg_names = {
            49 : 'PU Status',
            65 : 'Attitude',
            66 : 'BIST Output',
            67 : 'Clock',
            68 : 'Depth',
            71 : 'Surface Sound Speed',
            72 : 'Heading',
            73 : 'Installation Parameters (start)',
            78 : 'Raw Range and Angle (78)',
            80 : 'Position',
            82 : 'Runtime Parameters',
            83 : 'Seabed Image',
            85 : 'Sound Speed Profile (new)',
            88 : 'XYZ (88)',
            89 : 'Seabed Imagery (89)',
            102 : 'Raw Beam and Angle (new)',
            105 : 'Installation Parameters (stop)',
            107 : 'Watercolumn',
            110 : 'Network Attitude Velocity'
        }

    def request_IUR(self, remote_ip):
        sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # I don't want to force people to configure software for sensor type
        # Instead going to try all of them in the hopes that one works.
        codes = [ "710", "122", "302", "3020", "2040" ]
        for sensor in codes:
            if self.debug:
                # Leaving this statement on until I have a chance to test with
                # all systems.
                print "Requesting SVP from sensor", sensor

            # talker ID, Roger Davis (HMRG) suggested SM based on something KM told him
            output = '$SMR20,EMX=%s,' % ( sensor )

            # calculate checksum, XOR of all bytes after the $
            checksum = reduce(operator.xor, map(ord, output[1:len(output)]))

            # append the checksum and end of datagram identifier
            output += "*{0:02x}".format(checksum)
            output += "\\\r\n"

            sock_out.sendto( output , (remote_ip, 4001) )

            # Adding a bit of a pause
            time.sleep(1)

        sock_out.close()

    def parse(self):

        if len(self.desired_datagrams) == 0:
            #print "not going to parse!"
            return
        this_data = self.data[:]
        
        self.id = struct.unpack("<BB",this_data[0:2])[1]

        try:
            name = self.dg_names[self.id]
        except:
            name = "Unknown name"

        if self.debug:
            print "%s ... %s: Datagram ID %d/0x%x/%c, size: %d, type %s" % ( dt.datetime.utcnow(), self.sender, self.id, self.id, self.id, len(this_data), name )

        if self.id not in self.desired_datagrams:
            if self.debug:
                print "%s: Undesired datagram with ID %d, type %s" % ( self.sender, self.id, name )
            return

        # if self.id == 0x42:
            # self.bist = km_datagrams.km_bist(this_data)
            # if self.debug:
                # print self.bist
        # elif self.id == 0x47:
            # self.surface_ssp = km_datagrams.km_ssp(this_data)
            # if self.debug:
                # print self.surface_ssp
        # elif self.id == 0x49:
            # self.installation = km_datagrams.km_installation(this_data)
            # if self.debug:
                # print self.installation
        # elif self.id == 0x4e:
            # self.range_angle78 = km_datagrams.km_range_angle78(this_data)
            # if self.debug:
                # print self.range_angle78
        # elif self.id == 0x50:
            # self.nav = km_datagrams.km_nav(this_data)
            # if self.debug:
                # print self.nav
        # elif self.id == 0x52:
            # self.runtime = km_datagrams.km_runtime(this_data)
            # if self.debug:
                # print self.runtime
        # elif self.id == 0x55:
            # self.svp = km_datagrams.km_svp(this_data)
            # if self.debug:
                # print self.svp
        # elif self.id == 0x57:
            # self.svp_input = km_datagrams.km_svp_input(this_data)
            # if self.debug:
                # print self.svp_input
        # elif self.id == 0x58:
            # self.xyz88 = km_datagrams.km_xyz88(this_data)
            # if self.debug:
                # print self.xyz88
        # elif self.id == 0x59:
            # self.seabed_image89 = km_datagrams.km_seabed_image89(this_data)
            # if self.debug:
                # print self.seabed_image89
        if self.id == 0x6b:
            ping, = struct.unpack('<H', this_data[12:14])
            if not self.__dict__.has_key('holder'):
                self.holder = ph.packet_handler(this_data[12:])
            elif self.holder.ping == ping:
                self.holder.new_data(this_data[12:])
            else:
                self.old_holder = self.holder
                self.holder = ph.packet_handler(this_data[12:])
            if self.debug:
                print self.holder.ping
        # else:
            # if self.debug:
                # print "Cannot parse datagram of ID", self.id
                # return

        # return

    def log_to_file(self, data):
        # This is currently writes data in a Kongsberg .all format.
        # This involves writing the length of each datagram as a 4-byte
        # unsigned integer prior to writing out the datagram.  This is currently
        # hard-wired for little-endian byte-ordering.
        
        l = struct.pack("<I",len(data))
        udp_io.udp_io.log_to_file(self,l+data)

    def prep_and_switch_files(self):
        udp_io.udp_io.prep_and_switch_files(self)
        if self.debug:
            print "\nrequesting IUR"
        self.request_IUR("192.168.0.1")
