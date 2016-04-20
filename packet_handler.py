"""
packet_handler.py

Glen and Chen!
20160214

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

This module catches water column packets sent from a network stream and
assembles them for other uses. 

"""

import numpy as np
import matplotlib.pyplot as plt
import par

plt.ion()


class packet_handler:
    """
    hold
    """
    def __init__(self, wc, absorption = 0.030):
        """
        hold
        """
        self.data_ready = False
        self.absorption = absorption
        data = par.Data107(wc)
        self.ping = data.header['PingCounter']
        self.total_number = data.header['#OfDatagrams']
        self.beams = data.header['Total#Beams']
        this_beams = data.header['NumberBeamsInDatagram']
        # set the beam angle array pointer
        self._beams_so_far = this_beams
        # set the maximum number of samples tracker
        self.maxsamples = len(data.ampdata)
        # set the minimum range tracker
        detection_range = data.rx['DetectedRange']
        idx = np.nonzero(detection_range != 0)[0]
        if len(idx) > 0:
            self.minrange = detection_range[idx].min()
        else:
            self.minrange = len(data.ampdata)
        # get the water column magnitude data
        self.ampdata = []
        data.deTVG(self.absorption,0)
        self.ampdata.append(data.ampdata)
        # store the beam pointing angles
        self.beam_angles = np.zeros(self.beams)
        self.beam_angles[:this_beams] = data.rx['BeamPointingAngle'][:]
        self.numpackets = 1
        if self.numpackets == self.total_number:
            self.process_data(data.ampdata)               
        
    def new_data(self, wc):
        """
        hold
        """
        data = par.Data107(wc)
        # get the number of beams
        this_beams = data.header['NumberBeamsInDatagram']
        # get the beam pointing angles and add to the array
        self.beam_angles[self._beams_so_far:self._beams_so_far+this_beams] = data.rx['BeamPointingAngle'][:]
        # increment the pointer
        self._beams_so_far += this_beams
        # get the water column magnitude data
        data.deTVG(self.absorption,0)
        self.ampdata.append(data.ampdata)
        # track the maximum number of samples
        if len(data.ampdata) > self.maxsamples:
            self.maxsamples = len(data.ampdata)
        # track the minimum range to detection
        detection_range = data.rx['DetectedRange']
        idx = np.nonzero(detection_range != 0)[0]
        if len(idx) > 0:
            minrange = detection_range[idx].min()
            if self.minrange > minrange:
                self.minrange = minrange
        self.numpackets += 1
        if self.numpackets == self.total_number:
            data_array = self.assemble()
            self.process_data(data_array)
            
    def assemble(self):
        """
        hold
        """
        data_array = np.zeros((self.maxsamples, self.beams))
        data_array[:,:] = np.nan
        beam_pointer = 0
        for n in self.ampdata:
            dim = n.shape
            data_array[:dim[0], beam_pointer:beam_pointer+dim[1]] = n[:,:]
            beam_pointer += dim[1]
        idx = self.beam_angles.argsort()
        data_array[:,:] = data_array[:,idx]
        return data_array
        
    def process_data(self,data_array):
        """
        hold
        """
        self.data_array = data_array
        self.ave_by_beam = data_array[:self.minrange - 10, :].mean(axis = 0)
        self.nadir_beam = data_array[:,int(self.beams/2)]
        self.data_ready = True
 
 
class PlotWCNoise():

    def __init__(self, beams, samples, low_pass_len = 10):
        fig = plt.figure(figsize = (12,8))
        # initialize the average by beam subplot
        ax = fig.add_subplot(221)
        self.ave_buff = np.zeros((beams, 63))
        self.ave_buff[:,:] = np.nan
        self.ave_im = ax.imshow(self.ave_buff, aspect = 'auto', interpolation = 'none')
        self.cabar = plt.colorbar(mappable = self.ave_im)
        self.cabar.set_label('dB re $1\mu Pa$ at 1 meter')
        ax.set_ylabel('Beam Number')
        ax.set_title('Beam Averaged Noise')
        self.ca = color_range_tracker(multiplier = 3)
        # initialize the nadir beam scrolling plot
        ax2 = fig.add_subplot(223)
        self.nadir_buff = np.zeros((samples, 63))
        self.nadir_buff[:,:] = np.nan
        self.nadir_im = ax2.imshow(self.nadir_buff, aspect = 'auto', interpolation = 'none')
        self.cnbar = plt.colorbar(mappable = self.nadir_im)
        self.cnbar.set_label('dB re $1\mu Pa$ at 1 meter')
        ax2.set_ylabel('Nadir Samples (Range)')
        self.cn = color_range_tracker()
        # initialize the along track filtered water column display
        ax3 = fig.add_subplot(122)
        self._wc_ave_pntr = 0
        self._total_wc_ave = low_pass_len
        # guessing at a max range
        self.wc_buff = np.zeros((4000, beams, self._total_wc_ave))
        self.wc_buff[:,:,:] = np.nan
        self.wc_im = ax3.imshow(self.wc_buff[:,:,0], aspect = 'auto', interpolation = 'none')
        self.cwbar = plt.colorbar(mappable = self.wc_im)
        self.cwbar.set_label('dB re $1\mu Pa$ at 1 meter')
        ax3.set_yticklabels([])
        ax3.set_ylabel('Range')
        ax3.set_xlabel('Beam Number')
        ax3.set_title('High Pass Water column')
        self.cwc = color_range_tracker(multiplier = 3)
        
    def new_data(self, ave_by_beam, nadir_beam, data_array):
        #update average by beam
        self.ave_buff[:,1:] = self.ave_buff[:,:-1]
        self.ave_buff[:,0] = ave_by_beam[:]
        self.ave_im.set_data(self.ave_buff)
        self.ca.add(ave_by_beam)
        self.ave_im.set_clim(self.ca.minmax())
        #update nadir beam plot
        self.nadir_buff[:,1:] = self.nadir_buff[:,:-1]
        self.nadir_buff[:,0] = nadir_beam[:self.nadir_buff.shape[0]]
        self.nadir_im.set_data(self.nadir_buff)
        self.cn.add(nadir_beam)
        self.nadir_im.set_clim(self.cn.minmax())
        #update water column
        wc_mean = self.ave_wc(data_array)
        self.wc_im.set_data(wc_mean)
        self.cwc.add(wc_mean)
        self.wc_im.set_clim(self.cwc.minmax())
        # draw all the plots
        plt.pause(0.001)
        
    def ave_wc(self, data_array):
        if self._wc_ave_pntr >= self._total_wc_ave:
            self._wc_ave_pntr = 0
        numsamples = data_array.shape[0]
        self.wc_buff[:numsamples,:,self._wc_ave_pntr] = data_array
        wc_mean = np.nanmean(self.wc_buff, axis = 2)
        wc_mean_out = data_array - wc_mean[:numsamples, :]
        self._wc_ave_pntr += 1
        return wc_mean_out
        
      
class color_range_tracker:
    def __init__(self, numpts = 200, multiplier = 2, debug = False):
        self.cstd = np.zeros(numpts) + np.nan
        self.cmean = np.zeros(numpts) + np.nan
        self._m = multiplier
        self._debug = debug
        
    def add(self, data):
        self.cstd = np.roll(self.cstd, 1)
        self.cstd[0] = np.nanstd(data)
        self.cmean = np.roll(self.cmean,1)
        self.cmean[0] = np.nanmean(data)
        
    def minmax(self):
        cmin = np.nanmean(self.cmean) - self._m * np.nanmean(self.cstd)
        cmax = np.nanmean(self.cmean) + self._m * np.nanmean(self.cstd)
        if self._debug:
            nummeanused = len(np.nonzero(np.isnan(self.cmean)==False)[0])
            numstdused = len(np.nonzero(np.isnan(self.cstd)==False)[0])
            print numstdused, nummeanused
            print cmin, cmax
            print
        return cmin, cmax
    
