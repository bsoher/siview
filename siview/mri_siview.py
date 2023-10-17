#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import os


# 3rd party modules
import numpy as np
import xml.etree.cElementTree as ElementTree

# Our modules
import siview.common.xml_ as util_xml
import siview.common.misc as util_misc

from siview.common.constants import Deflate

DEFAULT_TIME_POINTS    = 8      # 6-50
DEFAULT_TIME_START     = 0      # 0
DEFAULT_TIME_STEP      = 50     # 50

DEFAULT_REPETITIONS    = 10     # multiple of 1000s - 10x1000 = 10000
DEFAULT_PEAK_AMPLITUDE = 1000   # Max of 32000 - just because, and DICOM too.

DEFAULT_FIXED_SNR      =  40    # These are from Timeseries fitting 
DEFAULT_FIXED_DELAY1   = -40    #  start values ...
DEFAULT_FIXED_DELAY2   = 200
DEFAULT_FIXED_RATE1    =  25
DEFAULT_FIXED_RATE2    =  25
DEFAULT_FIXED_BASE     =  10

DEFAULT_APPLY_SNR      = False
DEFAULT_APPLY_DELAY1   = False
DEFAULT_APPLY_DELAY2   = False
DEFAULT_APPLY_RATE1    = False
DEFAULT_APPLY_RATE2    = False
DEFAULT_APPLY_BASE     = False

DEFAULT_STEPS_SNR      = 1
DEFAULT_STEPS_DELAY1   = 1
DEFAULT_STEPS_DELAY2   = 1
DEFAULT_STEPS_RATE1    = 1
DEFAULT_STEPS_RATE2    = 1
DEFAULT_STEPS_BASE     = 1

DEFAULT_START_SNR      = 5
DEFAULT_START_DELAY1   = -50
DEFAULT_START_DELAY2   = 100
DEFAULT_START_RATE1    = 10
DEFAULT_START_RATE2    = 10
DEFAULT_START_BASE     = 0

DEFAULT_SIZE_SNR       = 5
DEFAULT_SIZE_DELAY1    = 50
DEFAULT_SIZE_DELAY2    = 50
DEFAULT_SIZE_RATE1     = 5
DEFAULT_SIZE_RATE2     = 5
DEFAULT_SIZE_BASE      = 5


       
        
class Washsim(object):
    """ 
    A container for time series data. 

    This is the fundamental object being manipulated in various Timeseris 
    knockoff applications.
    
    """
    # The XML_VERSION enables us to change the XML output format in the future
    XML_VERSION = "1.0.0"
    
    def __init__(self, attributes=None):

        self.id = util_misc.uuid()

        # timeseries_filename is only set on-the-fly (as opposed to being set
        # via inflate()). It's only set when the current timeseries was read from
        # or saved to a VIFF file.

        self.timeseries_filename = ''
        self.timeseries_uuid     = ''
        self.timeseries_version  = ''
        
        self.time_points     = DEFAULT_TIME_POINTS
        self.time_start      = DEFAULT_TIME_START
        self.time_step       = DEFAULT_TIME_STEP
        
        self.repetitions     = DEFAULT_REPETITIONS
        self.peak_amplitude  = DEFAULT_PEAK_AMPLITUDE
        
        self.fixed_snr       = DEFAULT_FIXED_SNR
        self.fixed_rate1     = DEFAULT_FIXED_RATE1
        self.fixed_rate2     = DEFAULT_FIXED_RATE2
        self.fixed_delay1    = DEFAULT_FIXED_DELAY1
        self.fixed_delay2    = DEFAULT_FIXED_DELAY2
        self.fixed_base      = DEFAULT_FIXED_BASE
        
        self.apply_snr       = DEFAULT_APPLY_SNR
        self.apply_rate1     = DEFAULT_APPLY_RATE1
        self.apply_rate2     = DEFAULT_APPLY_RATE2
        self.apply_delay1    = DEFAULT_APPLY_DELAY1
        self.apply_delay2    = DEFAULT_APPLY_DELAY2
        self.apply_base      = DEFAULT_APPLY_BASE

        self.steps_snr       = DEFAULT_STEPS_SNR
        self.steps_rate1     = DEFAULT_STEPS_RATE1
        self.steps_rate2     = DEFAULT_STEPS_RATE2
        self.steps_delay1    = DEFAULT_STEPS_DELAY1
        self.steps_delay2    = DEFAULT_STEPS_DELAY2
        self.steps_base      = DEFAULT_STEPS_BASE

        self.start_snr       = DEFAULT_START_SNR
        self.start_rate1     = DEFAULT_START_RATE1
        self.start_rate2     = DEFAULT_START_RATE2
        self.start_delay1    = DEFAULT_START_DELAY1
        self.start_delay2    = DEFAULT_START_DELAY2
        self.start_base      = DEFAULT_START_BASE

        self.size_snr        = DEFAULT_SIZE_SNR
        self.size_rate1      = DEFAULT_SIZE_RATE1
        self.size_rate2      = DEFAULT_SIZE_RATE2
        self.size_delay1     = DEFAULT_SIZE_DELAY1
        self.size_delay2     = DEFAULT_SIZE_DELAY2
        self.size_base       = DEFAULT_SIZE_BASE
        
        self.data_simulations = None            # one numpy array per slice of noiseless signal
                                                # fyi - line1 = self.timeseries.data[voxel[1],voxel[0],voxel[2],:]

        self.comment = ''
        
        if attributes is not None:
            self.inflate(attributes)


    ##### Standard Methods and Properties #####################################

    def __str__(self):
        return self.__unicode__().encode("utf-8")


    def __unicode__(self):
        lines = [ ]
        lines.append("--- MriWashSim Parameters ---")
        lines.append("washsim_uuid        : " + str(self.id))
        lines.append("timeseries_uuid     : " + str(self.timeseries_uuid))
        lines.append("timeseries_filename : " + str(self.timeseries_filename))
        lines.append("timeseries_version  : " + str(self.timeseries_version))
        lines.append("")
        lines.append("time_points         : " + str(self.time_points))
        lines.append("time_start          : " + str(self.time_start))
        lines.append("time_step           : " + str(self.time_step))
        lines.append("")
        lines.append("repetitions         : " + str(self.repetitions))
        lines.append("peak_amplitude      : " + str(self.peak_amplitude))
        lines.append("")
        lines.append("fixed_snr           : " + str(self.fixed_snr))
        lines.append("fixed_rate1         : " + str(self.fixed_rate1))
        lines.append("fixed_rate2         : " + str(self.fixed_rate2))
        lines.append("fixed_delay1        : " + str(self.fixed_delay1))
        lines.append("fixed_delay2        : " + str(self.fixed_delay2))
        lines.append("fixed_base          : " + str(self.fixed_base))
        lines.append("")
        lines.append("apply_snr           : " + str(self.apply_snr))
        lines.append("apply_rate1         : " + str(self.apply_rate1))
        lines.append("apply_rate2         : " + str(self.apply_rate2))
        lines.append("apply_delay1        : " + str(self.apply_delay1))
        lines.append("apply_delay2        : " + str(self.apply_delay2))
        lines.append("apply_base          : " + str(self.apply_base))
        lines.append("")
        lines.append("steps_snr           : " + str(self.step_snr))
        lines.append("steps_rate1         : " + str(self.step_rate1))
        lines.append("steps_rate2         : " + str(self.step_rate2))
        lines.append("steps_delay1        : " + str(self.step_delay1))
        lines.append("steps_delay2        : " + str(self.step_delay2))
        lines.append("steps_base          : " + str(self.step_base))
        lines.append("")
        lines.append("start_snr           : " + str(self.start_snr))
        lines.append("start_rate1         : " + str(self.start_rate1))
        lines.append("start_rate2         : " + str(self.start_rate2))
        lines.append("start_delay1        : " + str(self.start_delay1))
        lines.append("start_delay2        : " + str(self.start_delay2))
        lines.append("start_base          : " + str(self.start_base))
        lines.append("")
        lines.append("size_snr            : " + str(self.size_snr))
        lines.append("size_rate1          : " + str(self.size_rate1))
        lines.append("size_rate2          : " + str(self.size_rate2))
        lines.append("size_delay1         : " + str(self.size_delay1))
        lines.append("size_delay2         : " + str(self.size_delay2))
        lines.append("size_base           : " + str(self.size_base))
        
        # __unicode__() must return a Unicode object. In practice the code
        # above always generates Unicode, but we ensure it here.
        return '\n'.join(lines)


    def make_comment(self):
        lines = [ ]
        lines.append("--- MriWashSim Simulation Description ---")
        lines.append("")        
        lines.append("washsim_uuid        : " + str(self.id))
        lines.append("timeseries_uuid     : " + str(self.timeseries_uuid))
        lines.append("timeseries_filename : " + str(self.timeseries_filename))
        lines.append("timeseries_version  : " + str(self.timeseries_version))
        lines.append("")
        lines.append("Time Course Values")
        lines.append("----------------------------------")
        lines.append("time_points         : " + str(self.time_points))
        lines.append("time_start          : " + str(self.time_start))
        lines.append("time_step           : " + str(self.time_step))
        lines.append("")
        lines.append("Other Constants")
        lines.append("----------------------------------")
        lines.append("repetitions         : " + str(self.repetitions))
        lines.append("peak_amplitude      : " + str(self.peak_amplitude))
        lines.append("")
        lines.append("Fixed Parameter Values")
        lines.append("----------------------------------")
        lines.append("fixed_snr           : " + str(self.fixed_snr))
        lines.append("fixed_rate1         : " + str(self.fixed_rate1))
        lines.append("fixed_rate2         : " + str(self.fixed_rate2))
        lines.append("fixed_delay1        : " + str(self.fixed_delay1))
        lines.append("fixed_delay2        : " + str(self.fixed_delay2))
        lines.append("fixed_base          : " + str(self.fixed_base))
        lines.append("")
        lines.append("SNR Parameter Values")
        lines.append("----------------------------------")
        lines.append("apply_snr           : " + str(self.apply_snr))
        lines.append("steps_snr           : " + str(self.steps_snr))
        lines.append("start_snr           : " + str(self.start_snr))
        lines.append("size_snr            : " + str(self.size_snr))
        lines.append("")
        lines.append("Rate1 Parameter Values")
        lines.append("----------------------------------")
        lines.append("apply_rate1         : " + str(self.apply_rate1))
        lines.append("steps_rate1         : " + str(self.steps_rate1))
        lines.append("start_rate1         : " + str(self.start_rate1))
        lines.append("size_rate1          : " + str(self.size_rate1))
        lines.append("")
        lines.append("Rate2 Parameter Values")
        lines.append("----------------------------------")
        lines.append("apply_rate2         : " + str(self.apply_rate2))
        lines.append("steps_rate2         : " + str(self.steps_rate2))
        lines.append("start_rate2         : " + str(self.start_rate2))
        lines.append("size_rate2          : " + str(self.size_rate2))
        lines.append("")
        lines.append("Delay1 Parameter Values")
        lines.append("----------------------------------")
        lines.append("apply_delay1        : " + str(self.apply_delay1))
        lines.append("steps_delay1        : " + str(self.steps_delay1))
        lines.append("start_delay1        : " + str(self.start_delay1))
        lines.append("size_delay1         : " + str(self.size_delay1))
        lines.append("")
        lines.append("Delay2 Parameter Values")
        lines.append("----------------------------------")
        lines.append("apply_delay2        : " + str(self.apply_delay2))
        lines.append("steps_delay2        : " + str(self.steps_delay2))
        lines.append("start_delay2        : " + str(self.start_delay2))
        lines.append("size_delay2         : " + str(self.size_delay2))
        lines.append("")
        lines.append("Base Parameter Values")
        lines.append("----------------------------------")
        lines.append("apply_base          : " + str(self.apply_base))
        lines.append("steps_base          : " + str(self.steps_base))
        lines.append("start_base          : " + str(self.start_base))
        lines.append("size_base           : " + str(self.size_base))
        
        # __unicode__() must return a Unicode object. In practice the code
        # above always generates Unicode, but we ensure it here.
        return '\n'.join(lines)
    
    
    def create_simulations(self, timeseries):
        
        fixed_flag = False
        
        xdim = 128
        ydim = 128
        
        # ---------------------------------------------------------------------
        # Set time axis

        time_points = self.time_points
        time_axis   = (np.arange(time_points) * float(self.time_step)) + float(self.time_start)
        
        # -----------------------------------------------------------------
        # Set Data Dimensions
        
        # check how many slices in that dimension
        # - each slice is a separate set of parameters
        # - noise is equal in all voxels in one slice
        # - if no parameter ranges are 'applied' there is still 1 slice
        #    which is the set of fixed parameters
        slices = 0
        if self.apply_snr    : slices += self.steps_snr    
        if self.apply_rate1  : slices += self.steps_rate1
        if self.apply_rate2  : slices += self.steps_rate2
        if self.apply_delay1 : slices += self.steps_delay1
        if self.apply_delay2 : slices += self.steps_delay2
        if self.apply_base   : slices += self.steps_base
        
        if slices == 0: 
            slices = 1      # fixed values only
            fixed_flag = True 
        
        # dims = [xdim,ydim,slices,time_points]         # bjs - correct dims vs. tab_siview.plot()
          
        mask    = np.zeros([xdim,ydim,slices],             dtype='int')
        data    = np.zeros([xdim,ydim,slices,time_points], dtype='float')     # pure signal + noise in ALL voxels
        signals = np.zeros([slices,time_points],           dtype='float')     # just the pure signal in each slice
        
        
        # ---------------------------------------------------------------------
        # Set Model Parameters into numpy array
        
        fix_peak   = float(self.peak_amplitude)
        fix_snr    = float(self.fixed_snr)
        fix_rate1  = float(self.fixed_rate1)
        fix_rate2  = float(self.fixed_rate2)
        fix_delay1 = float(self.fixed_delay1)
        fix_delay2 = float(self.fixed_delay2)
        fix_base   = float(self.fixed_base)
        noises     = []
        
        if fixed_flag:
            params = [[fix_peak, fix_rate1, fix_rate2, fix_delay1, fix_delay2, fix_base],]
            params = np.array(params)
            noises.append(fix_peak/fix_snr)
        else:
            params = np.ndarray([slices,6], dtype='float')
            islice = 0
            
            if self.apply_snr: 
                for i in range(self.steps_snr):
                    val = self.start_snr + self.size_snr * i
                    params[islice,:] = [fix_peak, fix_rate1, fix_rate2, fix_delay1, fix_delay2, fix_base]
                    noises.append(fix_peak/val)
                    islice += 1
            if self.apply_rate1: 
                for i in range(self.steps_rate1):
                    val = self.start_rate1 + self.size_rate1 * i
                    params[islice,:] = [fix_peak, val, fix_rate2, fix_delay1, fix_delay2, fix_base]
                    noises.append(fix_peak/fix_snr)
                    islice += 1
            if self.steps_rate2: 
                for i in range(self.steps_rate2):
                    val = self.start_rate2 + self.size_rate2 * i
                    params[islice,:] = [fix_peak, fix_rate1, val, fix_delay1, fix_delay2, fix_base]
                    noises.append(fix_peak/fix_snr)
                    islice += 1
            if self.steps_delay1: 
                for i in range(self.steps_delay1):
                    val = self.start_delay1 + self.size_delay1 * i
                    params[islice,:] = [fix_peak, fix_rate1, fix_rate2, val, fix_delay2, fix_base]
                    noises.append(fix_peak/fix_snr)
                    islice += 1
            if self.apply_delay2: 
                for i in range(self.apply_delay2):
                    val = self.start_delay2 + self.size_delay2 * i
                    params[islice,:] = [fix_peak, fix_rate1, fix_rate2, fix_delay1, val, fix_base]
                    noises.append(fix_peak/fix_snr)
                    islice += 1
            if self.apply_base: 
                for i in range(self.apply_base):
                    val = self.start_base + self.size_base * i
                    params[islice,:] = [fix_peak, fix_rate1, fix_rate2, fix_delay1, fix_delay2, val]
                    noises.append(fix_peak/fix_snr)
                    islice += 1

        # ---------------------------------------------------------------------
        # Pre-Init TIMESERIES so we can use model function

        timeseries.import_from_washsim(data, time_axis, mask)

        # ---------------------------------------------------------------------
        # SIGNALS array create

        for i in range(slices):
            signals[i,:], _ = timeseries.model_exponential_rate(params[i])
            
        # ---------------------------------------------------------------------
        # NOISE level in each slice
        
        for i in range(slices):
            tmp = np.random.random((xdim,ydim,time_points)) * noises[i]
            for j in range(time_points):
                data[:,:,i,j] = tmp[:,:,j]
            
        # ---------------------------------------------------------------------
        # DATA - add signal to noise in each slice at all voxels
        
        xstr = 14       # center simulation signals in middle of 128x128 slice
        xend = 114      # - assume each row can contain 100 voxels
        ystr = 14       # - each slice can have up to 10,000 voxels
        yend = ystr + 10 * self.repetitions
        
        for i in range(slices):
            data[xstr:xend,ystr:yend,i,:] += signals[i,:]
            mask[xstr:xend,ystr:yend,i]    = 1
            
#         for i in range(slices):
#             mask[xstr:xend,ystr:yend,i] = 1
#             for j in range(time_points):
#                 data[xstr:xend,ystr:yend,i,j] += signals[i,j]

        # ---------------------------------------------------------------------
        # OVERWRITE data into Timeseries
         
        data = np.round(data, decimals=0)   # emulate DICOM data type
        
        timeseries.import_from_washsim(data, time_axis, mask)
        timeseries.timeseries_filename = self.timeseries_filename
        
        self.data_simulations = signals
        
    
    
    def deflate(self, flavor=Deflate.ETREE):
        if flavor == Deflate.ETREE:
            e = ElementTree.Element("washsim",
                                    {"id" : self.id,
                                     "version" : self.XML_VERSION})

            util_xml.TextSubElement(e, "washsim_uuid",        self.id)
            util_xml.TextSubElement(e, "timeseries_uuid",     self.timeseries_uuid)
            util_xml.TextSubElement(e, "timeseries_filename", self.timeseries_filename)
            util_xml.TextSubElement(e, "timeseries_version",  self.timeseries_version)
            

            # These atttributes are all scalars and map directly to 
            # XML elements of the same name.
            for attribute in ("time_points",  "time_start",   "time_step",
                              "repetitions",  "peak_amplitude",
                              "fixed_snr",    "apply_snr",    "steps_snr",    "start_snr",    "size_snr",
                              "fixed_rate1",  "apply_rate1",  "steps_rate1",  "start_rate1",  "size_rate1",
                              "fixed_rate2",  "apply_rate2",  "steps_rate2",  "start_rate2",  "size_rate2",
                              "fixed_delay1", "apply_delay1", "steps_delay1", "start_delay1", "size_delay1",
                              "fixed_delay2", "apply_delay2", "steps_delay2", "start_delay2", "size_delay2",
                              "fixed_base",   "apply_base",   "steps_base",   "start_base",   "size_base",
                              ):
                util_xml.TextSubElement(e, attribute, getattr(self, attribute))

            e.append(util_xml.numpy_array_to_element(self.data_simulations, "data_simulations"))

            util_xml.TextSubElement(e, "comment", self.comment)
                     
            return e

        elif flavor == Deflate.DICTIONARY:
            return self.__dict__.copy()


    def inflate(self, source):
        if hasattr(source, "makeelement"):
            # Quacks like an ElementTree.Element
            xml_version = source.get("version")

            self.id = source.get("id")

            if xml_version == "1.0.0":
                # Can use version to set up specific inflation.
                pass
            else:
                # In all other versions ...
                pass

            # Strings
            for attribute in ("timeseries_filename", 
                              "timeseries_uuid",
                              ):
                item = source.findtext(attribute)
                if item is not None:
                    setattr(self, attribute, item)

            # Ints
            for attribute in ("time_points",  "time_start",   "time_step",
                              "repetitions",  "peak_amplitude",
                              "fixed_snr",    "apply_snr",    "steps_snr",    "start_snr",    "size_snr",
                              "fixed_rate1",  "apply_rate1",  "steps_rate1",  "start_rate1",  "size_rate1",
                              "fixed_rate2",  "apply_rate2",  "steps_rate2",  "start_rate2",  "size_rate2",
                              "fixed_delay1", "apply_delay1", "steps_delay1", "start_delay1", "size_delay1",
                              "fixed_delay2", "apply_delay2", "steps_delay2", "start_delay2", "size_delay2",
                              "fixed_base",   "apply_base",   "steps_base",   "start_base",   "size_base", 
                              ):
                item = source.findtext(attribute)
                if item is not None:
                    setattr(self, attribute, int(float(item)))

            # Booleans
            for attribute in ("apply_snr"
                              "apply_rate1",
                              "apply_rate2",
                              "apply_delay1",
                              "apply_delay2",
                              "apply_base",
                             ):
                item = source.findtext(attribute)
                if item is not None:
                    setattr(self, attribute, util_xml.BOOLEANS[item])

        elif hasattr(source, "keys"):            
            # Quacks like a dict
            for key in list(source.keys()):
                if hasattr(self, key):
                    setattr(self, key, source[key])




