"""
Copyright (c) 2016 Glen Rice and Chen Zhang

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
import signal
import sys
import time
import km_io
import packet_handler as ph
import threading

def signal_handler(signal, frame):
    print ", You pressed Ctrl+C!"
    viewer.stop_logging()
    viewer.stop_listen()

    sys.exit(0)
    
signal.signal(signal.SIGINT, signal_handler)

# listen on port 55705 for incoming datagrams
viewer = km_io.km_io(55709, [107], 1.0)

# viewer.debug = True

viewer.start_listen()

indicator = ['-','\\','|','/']

print 'catching data:  ',

have_num_beams = False
while have_num_beams == False:
    time.sleep(1)
    if viewer.__dict__.has_key('holder'):
        if viewer.holder.data_ready:
            pWC = ph.PlotWCNoise(viewer.holder.beams, viewer.holder.minrange)
            have_num_beams = True     

def wLoop():            
    n = 0
    while True:
        if viewer.holder.data_ready:
            pWC.new_data(viewer.holder.ave_by_beam, viewer.holder.nadir_beam,
                viewer.holder.data_array)
            viewer.holder.data_ready = False
        if n > 3:
            n = 0
        print '\b\b' + indicator[n],
        n += 1
        
        #time.sleep(0.1)

      
#threading.Thread(target=wLoop()).start()
wLoop()

    