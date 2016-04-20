"""
Copyright (c) 2015 Glen Rice

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
from datetime import datetime


class udp_io(object):

    def __init__(self, listen_port, desired_datagrams, timeout):
        self.listen_port = listen_port
        self.desired_datagrams = desired_datagrams
        self.timeout = timeout

        # A few controls on behaviour
        self.debug = False
        self.do_listen = False
        self.listening = False

        # Goodies for logging to memory
        self.logging_to_memory = False
        self.logged_data = []

        # Goodies for logging to file
        self.logging_to_file = False
        self.logfile = None
        self.logfile_name = None
        self.maxfilesize = 1000000
        self.loggedtofile = 0
        self.numlogfile = 0
        self.newfile = False

    def start_logging(self):
        """This method is meant to be over-ridden"""
        pass

    def stop_logging(self):
        """This method is meant to be over-ridden"""
        pass

    def clear_logged_data(self):
        self.logged_data = []

    def open_log_file(self):
        filetime = datetime.now()
        ftime = "%(year)04d%(month)02d%(day)02d%(hour)02d%(minute)02d" \
            % {'year': filetime.year,
            'month': filetime.month,
            'day': filetime.day,
            'hour': filetime.hour,
            'minute': filetime.minute
            }
        self.logfile_name = self.logfile_base + '_' + ftime + '.' + self.logfile_ext
        self._newlogfile = open(self.logfile_name,"wb")
        if self.newfile:
            threading.Thread(target=self.prep_and_switch_files).start()
        else:
            self.logfile = self._newlogfile
        
    def close_log_file(self):
        self.logfile.close()
        self.logfile = None
        self.logfile_name = None
        self.newfile = False
        
    def set_logfile_base(self, logfilename):
        outfile = logfilename.rsplit('.')
        if len(outfile) == 2:
            self.logfile_base, self.logfile_ext = outfile
        else:
            self.logfile_base = outfile[0]
            self.logfile_ext = 'out'
        
    def prep_and_switch_files(self):
        """
        This method switches the primary file between this classes already used
        file and the provided, open file object.  Overload this function and 
        then call it from the subclass to do "things" to the newfile before
        logging to it.  Because it is called in a thread, it should be safe to
        take the time to log other things before calling this method when the
        switch happens.
        """
        oldlogfile = self.logfile
        self.logfile = self._newlogfile
        oldlogfile.close()
        self.loggedtofile = 0
        self.newfile = False

    def start_listen(self, logfilename = '', maxfilesize = ''):
        if logfilename != '':
            self.set_logfile_base(logfilename)
            self.open_log_file()
            self.logging_to_file = True
            
        if maxfilesize != '':
            self.maxfilesize = maxfilesize

        self.listening = True
        if self.debug:
            print "Starting listen thread"
        threading.Thread(target=self.listen).start()

        if self.debug:
            print "Started listen thread"

    def listen(self):

        self.sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_in.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,2**16)

        if self.timeout > 0:
            self.sock_in.settimeout(self.timeout)

        try:
            self.sock_in.bind( ("0.0.0.0", self.listen_port) )
        except:
            self.listening = False
            self.sock_in.close()
            if self.debug:
                print "Port %d already bound?  Not listening anymore" % self.listen_port
            return

        if self.debug:
            print "Going to listen on port", self.listen_port, "for datagrams ", self.desired_datagrams

        self.do_listen = True
        self.listening = True

        while self.do_listen:
            try:
                self.data, self.sender = self.sock_in.recvfrom( 2**16 )
            except socket.timeout:
                if self.debug:
                    print "Got socket timeout..."
                continue

            if self.debug:
                print "Got data from", self.sender, "of length", len(self.data)
                #print "Data is\n", self.data

            if self.logging_to_file and self.logfile != None:
                if self.debug:
                    print "Going to write to output file", self.logfile_name, "length is", len(self.data), "bytes"

                self.log_to_file(self.data)

            if self.logging_to_memory:
                self.logged_data.append(self.data)

            self.parse()

        self.sock_in.close()

        if self.debug:
            print "Done listening!", self

    def stop_listen(self):
        self.do_listen = False

    def parse(self):
        return

    def log_to_file(self, data):
        datasize = len(data)
        self.logfile.write(data)
        self.loggedtofile += datasize
        if self.loggedtofile > self.maxfilesize and not self.newfile:
            self.newfile = True
            self.open_log_file()
            
        
