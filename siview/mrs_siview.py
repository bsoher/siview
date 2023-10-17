#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import os
import datetime
import time
import collections

# 3rd party modules
try:
    import pydicom
except ImportError:
    import dicom as pydicom
import numpy as np
import scipy as sp
import xml.etree.cElementTree as ElementTree
import scipy.ndimage as ndi

# Our modules
import siview.constants as const
import siview.chain_siview as chain_siview
import siview.common.xml_ as util_xml
import siview.common.misc as util_misc
import siview.common.constants as common_constants

from siview.common.constants import Deflate

        
        
class Timeseries(object):
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
        self.patient_id = ''
        self.series_description = ''
        self.study_uid = ''
        self.dicom_path = ''
        self.output_path = ''

        self.element_spacing   = []
        self.data_sources      = []
        self.time_axis         = None
        self.data              = None
        
        self.time_course_model = 'Exponential Rate Decay'
        self.weight_function   = 'Asymmetric Half-Sine'
        self.weight_scale      = 3.0
        
        self.peak_min        = const.PEAK_MIN     # 10       # times % max value of current plot
        self.peak_start      = const.PEAK_START   # 20       # times % max value of current plot
        self.peak_max        = const.PEAK_MAX     #500      # times % max value of current plot
        self.rate1_min       = const.RATE1_MIN    # 5        # 
        self.rate1_start     = const.RATE1_START  # 25
        self.rate1_max       = const.RATE1_MAX    # 320
        self.rate2_min       = const.RATE2_MIN    # 5
        self.rate2_start     = const.RATE2_START  # 25
        self.rate2_max       = const.RATE2_MAX    # 330
        self.delay1_min      = const.DELAY1_MIN   # -45
        self.delay1_start    = const.DELAY1_START # -40
        self.delay1_max      = const.DELAY1_MAX   # 5
        self.delay2_min      = const.DELAY2_MIN   # 150
        self.delay2_start    = const.DELAY2_START # 200
        self.delay2_max      = const.DELAY2_MAX   # 346
        self.base_min        = const.BASE_MIN     # 1
        self.base_start      = const.BASE_START   # 10
        self.base_max        = const.BASE_MAX     # 20

        self.result_maps = None

        self.chain = None
        self.noise = 0.0        # set after data is loaded
        self.lsq_function = None

        if attributes is not None:
            self.inflate(attributes)
            self.create_chain()
            self.noise = np.std(self.data[4,:,:,:])
            self.assign_functions()



    ##### Standard Methods and Properties #####################################

    @property
    def dims(self):
        """Data dimensions in a list, e.g. [1024, 1, 1, 1]. It's read only."""
        # Note that self.data.shape is a tuple. Dims must be a list.
        if self.data is not None:
            return list(self.data.shape)  
        return None


    def create_chain(self):
        self.chain = chain_siview.ChainSiview(self)        

        
    def import_from_dcmstack(self, my_stack, all_filenames, 
                                             pad_data=False, 
                                             patient_id='no_id', 
                                             series_description='no_description',
                                             study_uid='no_id',
                                             output_path=''):
        self.patient_id = patient_id
        self.series_description = series_description
        self.study_uid = study_uid
        self.output_path = output_path
        
        self.data_sources = all_filenames
        self.element_spacing = np.array([1,1,1,100])
        self.data = my_stack.get_data().copy()

        times = []
        temps = sorted(my_stack._time_vals)     # string time in hhmmss.frac 
        for item in temps:
            hr = float(item[0:2]) * 3600.0
            mn = float(item[2:4]) * 60.0
            sc = float(item[4:])
            times.append( hr + mn + sc )        # time in float(secs) since midnight
        self.time_axis = [float(item) - float(times[0]) for item in times]   # delta time from first scan
        self.time_axis = np.array(self.time_axis)
        
        # if low-res asymmetric 32,64 we want to display as square 64,64
        if pad_data:
            xorig, yorig, zorig, torig = self.raw.shape
            if yorig != xorig:
                padding = []
                xpad,  ypad  = 0,0  
                full_size = max(self.raw.shape)
                if xorig < full_size:
                    xpad = int((full_size - xorig) / 2)
                if yorig < full_size:
                    ypad = int((full_size - yorig) / 2)
                padding.append([xpad,xpad])
                padding.append([ypad,ypad])
                if len(self.raw.shape)>2: padding.append([0,0]) 
                if len(self.raw.shape)>3: padding.append([0,0])
                # default constant value is 0
                self.data = np.pad(self.data, padding, 'constant')  #, constant_values=[0,0])
        
        self.reset_results()
        self.create_chain()
        self.noise = np.std(self.data[4,:,:,:])
        self.make_mask()
        self.assign_functions()


    def import_from_washsim(self, data, time_axis, mask, output_path=''):
        '''
        Data from WashSim should be a 4D numpy NDarray with dims (128,128,slice,time).
        Data is centered in the 128,128 array with 14 rows/cols of noise only on
        each side. Thus rows of 100 voxels of data, and 10000 total possible voxels
        of simulated data in each slice.  Each slice is a different set of parameters
        from WashSim, but only one set of data parameters per slice. There is a 
        minimum of 1000 voxels per slice (10 rows), up to a max of 10000 voxels.
        
        '''
        self.patient_id         = 'washsim_patient_id'
        self.series_description = 'washsim_series_description'
        self.study_uid          = 'washsim_study_id'
        self.output_path        = output_path
        
        self.data_sources       = ['washsim_application',]
        self.element_spacing = np.array([1,1,1,100])
        
        self.data = data                     # should be a 4D numpy array coming in (128, 128, slice, time_points).

        self.time_axis = np.array(time_axis)    # each point is defined as delta time from first scan
        
        self.reset_results()
        self.create_chain()
        
        self.noise = np.std(self.data[4:10,:,0,:])  # FIXME - bjs, noise level may change between 'slices' in WashSim
        
        # self.make_mask()
        self.result_maps['Mask'] = mask     # should be [128,128,slice] dims
        
        self.assign_functions()
        

    def assign_functions(self):
        
        if self.time_course_model == 'Exponential Rate Decay':
        
            if self.dims[-1] > 6:
                self.fit_function  = self.model_exponential_rate
                self.lsq_function  = self.model_exponential_rate_lsq
                self.init_function = self.initial_values_exponential_rate
            elif self.dims[-1] > 5:
                self.fit_function  = self.model_exponential_rate_nobase
                self.lsq_function  = self.model_exponential_rate_nobase_lsq
                self.init_function = self.initial_values_exponential_rate_nobase
            else:
                raise ValueError("Not enough time points for fitting functions (less than 6)")

        elif self.time_course_model == 'Exponential Washin Only':

            if self.dims[-1] > 4:
                self.fit_function  = self.model_washin_only
                self.lsq_function  = self.model_washin_only_lsq
                self.init_function = self.initial_values_washin_only
            elif self.dims[-1] > 3:
                self.fit_function  = self.model_washin_only_nobase
                self.lsq_function  = self.model_washin_only_nobase_lsq
                self.init_function = self.initial_values_washin_only_nobase
            else:
                raise ValueError("Not enough time points for fitting functions (less than 6)")

        else:
            raise ValueError( "Unknown fitting function selection.")

    def reset_results(self):
        """
        Resets (to zero) and resizes dimensionally-dependent data
        
        """
        self.result_maps = collections.OrderedDict()
        dims = self.dims

        for key in ['Mask',   'Peak',   'R1', 'R2', 
                    'Delay1', 'Delay2', 'Base',
                    'Chis',   'Badfit']:
            self.result_maps[key] = np.zeros(dims[0:3], float)
        self.result_maps['Mask'] += 1

        if self.chain is not None:
            self.chain.reset_results_arrays()
    
    
    def reset_mask(self):
        self.result_maps['Mask'] = 0 * self.result_maps['Mask'] + 1


    def get_output_text_by_slice(self):
        """
        Output values from the fitting results array into a CSV based text
        file. 
        
        This method organizes the output serially by voxel value. We loop
        through x,y,z value (x changing fastest) and write a result to the 
        text array if the mask value is non-zero. All fitting values are
        written to the same voxel line as are the mask and image value.
        
        """
        # Create output header and results strings, check element count. 
        # If the file exists, check that the element count is the same in 
        # in the last line as for this results line. If it is, just write
        # out the results string. If different length, output both the 
        # header and results strings.
        
        xmax, ymax, zmax, tmax = self.data.shape
        maps = self.result_maps
        
        # create header line
        # - first line is study_uid
        # - second line contains column headers
        lines_left = []
        lines_left.append(self.study_uid)
        line = 'X-voxel, Y-voxel,'
        for key in ['Mask','Peak','R1','R2','Delay1','Delay2','Base','Chis','Badfit']:
            for z in range(zmax):
                line += key+'_'+str(z)+', '
        lines_left.append(line)
        
        # these are magic numbers assigned by Cecil for his mask locations
        for y in range(ymax):
            for x in range(xmax):
                item = [str(x), str(y)]
                for key in ['Mask','Peak','R1','R2','Delay1','Delay2','Base','Chis','Badfit']:
                    for z in range(zmax):
                        if maps['Mask'][y,x,z] == 5:        # magic number set by Cecil
                            item.append(str(maps[key][y,x,z]))
                        else:
                            item.append('0')
                lines_left.append(",".join(item))

        lines_right = []
        lines_right.append(self.study_uid)
        line = 'X-voxel, Y-voxel,'
        for key in ['Mask','Peak','R1','R2','Delay1','Delay2','Base','Chis','Badfit']:
            for z in range(zmax):
                line += key+'_'+str(z)+', '
        lines_right.append(line)
        
        for y in range(ymax):
            for x in range(xmax):
                item = [str(x), str(y)]
                for key in ['Mask','Peak','R1','R2','Delay1','Delay2','Base','Chis','Badfit']:
                    for z in range(zmax):
                        if maps['Mask'][y,x,z] == 4:    # magic number set by Cecil
                            item.append(str(maps[key][y,x,z]))
                        else:
                            item.append('0')
                lines_right.append(",".join(item))
                
        return lines_left, lines_right 

        

    def get_output_text_by_voxel(self):
        """
        Output values from the fitting results array into a CSV based text
        file. 
        
        This method organizes the output serially by voxel value. We loop
        through x,y,z value (x changing fastest) and write a result to the 
        text array if the mask value is non-zero. All fitting values are
        written to the same voxel line as are the mask and image value.
        
        """
        # create header line
        # - first line is study_uid
        lines = []
        lines.append('Study UID, '+self.study_uid)

        # - second line contains column headers
        lines.append('X-voxel, Y-voxel, Z-voxel, Mask, Peak, R1, R2, Delay1, Delay2, Base, Chis, Badfit')
        maps = self.result_maps

        voxels = self.get_all_voxels()  # list of tuples, with mask != 0

        # - now loop through voxels and append lines of results        
        for x,y,z in voxels:
            item = [str(x), str(y), str(z)]
            for key in ['Mask','Peak','R1','R2','Delay1','Delay2','Base','Chis','Badfit']:
                item.append(str(maps[key][y,x,z]))
            lines.append(",".join(item))
        
        return lines
    

    def get_all_voxels(self):
        voxels = []
        dims = self.dims
        for z in range(dims[2]):
            for y in range(dims[1]):
                for x in range(dims[0]):
                    if self.result_maps['Mask'][y,x,z] != 0:
                        voxels.append([x,y,z])
        return voxels


    def get_all_voxels_by_slice(self, islice):
        z = islice
        voxels = []
        dims = self.dims
        for y in range(dims[1]):
            for x in range(dims[0]):
                if self.result_maps['Mask'][y,x,z] != 0:
                    voxels.append([x,y,z])
        return voxels


    def get_out_dicom(self):
        """ 
        Returns a dict with information about DICOM headers that can
        be used to create DICOM output  
        
        """
        # Get directory from first source file name
        # Enumerate the directory contents
        # Turn the filenames into fully-qualified filenames.
        # Filter out non-files
        fpath, _ = os.path.split(self.data_sources[0])
        
        msg = ''
        if not os.path.exists(fpath):
            msg = "DICOM source directory can not be located, returning."
        elif not os.path.isdir(fpath):
            msg = "DICOM source directory is nto a directory, returning."
        if msg:
            raise ValueError(msg)
        
        fnames = os.listdir(fpath)
        fnames = [os.path.join(fpath, fname) for fname in fnames]
        fnames = [fname for fname in fnames if os.path.isfile(fname)]
        nslice = self.result_maps['Mask'].shape[2]
        
        if len(fnames) <= 0:
            msg = "No DICOM files found in source directory, returning."
            raise ValueError(msg)
        if len(fnames) != nslice:
            msg = "Wrong number of DICOM files found in source directory, returning."
            raise ValueError(msg)
        
        dicoms = []
        set_study_uid = set()
        set_series_uid = set()
        for item in fnames:
            src_dcm = pydicom.dcmread(item)
            set_study_uid.add(src_dcm.StudyInstanceUID)
            set_series_uid.add(src_dcm.SeriesInstanceUID)
            dicoms.append(src_dcm)
            
        source_path, _ = os.path.split(fpath)
        out_dcm = { 'study_uid'   : list(set_study_uid),
                    'series_uid'  : list(set_series_uid),
                    'source_path' : source_path,
                    'dicom_files' : dicoms
                  }
        return out_dcm         


    def do_results_output_dicom(self):
        """
        This functionality got pushed into this object so it would be available
        from the command line interface used for batch processing.
        
        """
        try:
            out_dicom = self.get_out_dicom()
        except: 
            raise ValueError 

        study_uid   = str(out_dicom['study_uid'][0]).split('.')
        series_uid  = str(out_dicom['series_uid'][0]).split('.')

        base_uid = []
        for item1,item2 in zip(study_uid,series_uid):
            if item1 == item2:
                base_uid.append(item1)
            else:
                base_uid = '.'.join(base_uid)
                break

        keys = ['Mask', 'Peak', 'R1', 'R2', 'Delay1', 'Delay2', 
                'Base', 'Chis', 'Badfit']
        extn = ['washout_01_mask', 'washout_02_peak',   'washout_03_r1', 
                'washout_04_r2',   'washout_05_delay1', 'washout_06_delay2', 
                'washout_07_base', 'washout_08_chis',   'washout_09_badfit']
        
        for j,key in enumerate(keys):
        
            dat = self.result_maps[key]    

            if j == 0:
                imsk = dat > 0
        
            # create the destination directory if needed
            fpath = out_dicom['source_path']+'\\'+extn[j]
            try: 
                os.makedirs(fpath)
            except OSError:
                if not os.path.isdir(fpath):
                    raise
            
            #pscale, pmin, pmax = parm[j]
            
            ttmp = time.localtime(time.time())
            ptime_str = "%02d%02d%02d.000000" % (ttmp[3], ttmp[4], ttmp[5])
            
            pdate = str(datetime.date.today()).replace('-','')
            ptime = str(time.time()) # milliseconds since the epoch
            puid  = base_uid+'.'+pdate+ptime+'.0'

            dat    = dat.copy()
            dat    = dat[:,:,::-1]      # re-orient for internal Nifti -> DICOM output
            dat    = dat.astype(float)  # just in case it isn't a float array
            dmin   = np.min(dat[imsk])
            dmax   = np.max(dat[imsk])
            if dmin == dmax:
                dmin = 0.0
                dmax = 1.0
            if key == 'Mask': dmin = 0.0        # just in case
            width  = dmax-dmin
            center = dmin + 0.5*width

            pscale = 4095.0 / float(width)
            pslope = 1.0 / float(pscale) 
            pint   = dmin
            
            dat[imsk] -= dmin
            dat       *= pscale

            imin   = int(np.round(np.min(dat[imsk])))
            imax   = int(np.round(np.max(dat[imsk])))
            
            for i,item in enumerate(out_dicom['dicom_files']):
                # change out the data
                #
                # 1. copy the data
                # 2. type the data for insert into the Dataset
                # 3. modify header data
                # 4. write data to file
                
                pdata = dat[:,:,i].copy()
                
                if pdata.dtype != np.uint16:
                    pdata = pdata.astype(np.uint16)

                item.PixelData = pdata.tostring()

                pdate = str(datetime.date.today()).replace('-','')
                ptime = str(time.time()).replace('.','')            # milliseconds since the epoch
                item.SOPInstanceUID          = base_uid+'.'+pdate+ptime+str(100+i)+'.0'        # aka item[0x00080018]
                 
                item.ContentDate             = pdate
                item.ContentTime             = ptime_str
#                 item.SOPClassUID             = '1.2.840.10008.5.1.4.1.1.7'  #'Secondary Capture Image Storage'
                item.WindowCenter            = center
                item.WindowWidth             = width
                item.LargestImagePixelValue  = imax
                item.SmallestImagePixelValue = imin
                item.RescaleSlope            = pslope
                item.RescaleIntercept        = pint
                item.SeriesNumber            = 120+j
                item.SeriesDescription       = extn[j]
                item.SeriesInstanceUID       = puid
                imnum = str(item.InstanceNumber)
                while len(imnum) < 3:
                    imnum = '0'+imnum 
                fname = fpath+'\\'+extn[j]+'_slice'+imnum+'.dcm'
                item.save_as(fname)
        
        

    def make_mask(self):
        # FIXME - bjs, could hook this up to a widget for setting threshold?
        
        data  = self.data
        dims  = self.dims
        noise = self.noise
        if noise > 0:
            thrsh = noise * 6
        else:
            thrsh = 0.01 * data.max()
        
        for i in range(dims[2]):
            mask = self.result_maps['Mask'][:,:,i].copy()
            mask = mask*0 + 1
            slc = self.data[:,:,i,:]
            slc = np.sum(slc, axis=2) / float(dims[-1])
            # threshold
            mask[slc < thrsh] = 0
            # fill holes
            mask = ndi.binary_fill_holes(mask)
            
            self.result_maps['Mask'][:,:,i] = mask


    def get_fit_plot(self, voxel):

        npts = self.dims[-1]
        x,y,z = voxel

        a = []
        
        if self.time_course_model == 'Exponential Rate Decay':
            a.append(self.result_maps['Peak'  ][y,x,z])
            a.append(self.result_maps['R1'    ][y,x,z])
            a.append(self.result_maps['R2'    ][y,x,z])
            a.append(self.result_maps['Delay1'][y,x,z])
            a.append(self.result_maps['Delay2'][y,x,z])
            a.append(self.result_maps['Base'  ][y,x,z])
        else:
            a.append(self.result_maps['Peak'  ][y,x,z])
            a.append(self.result_maps['R1'    ][y,x,z])
            a.append(self.result_maps['Delay1'][y,x,z])
            a.append(self.result_maps['Base'  ][y,x,z])

        if np.sum(a) == 0:
            plot_results = np.zeros(npts)
        else:
            plot_results, _ = self.fit_function(a)
        
        return plot_results


    def model_exponential_rate_lsq(self, a, y, w):
        
        nfree   = np.size(y)-len(a)
        yfit, _ = self.model_exponential_rate(a)
        chisqr  = np.sum(w*(y-yfit)**2)/nfree
        return chisqr
    
    
    def model_exponential_rate_nobase_lsq(self, a, y, w):
        
        nfree   = np.size(y)-len(a)
        yfit, _ = self.model_exponential_rate_nobase(a)
        chisqr  = np.sum(w*(y-yfit)**2)/nfree
        return chisqr


    def initial_values_exponential_rate(self, data, pair_limits=False):
        
        t = self.time_axis 
        tmax = t[-1]
        ihalf = int(len(t) / 2.0)
        
        peak_val   = float(self.peak_start / 100.0)
        peak_min   = float(self.peak_min / 100.0)
        peak_max   = float(self.peak_max / 100.0)
        base_val   = float(self.base_start / 100.0)
        base_min   = float(self.base_min / 100.0)
        base_max   = float(self.base_max / 100.0)
        
        peak   = peak_val * max(data) 
        r1     = self.rate1_start
        r2     = self.rate2_start
        delay1 = self.delay1_start
        delay2 = self.delay2_start
        base   = base_val * max(data)
        
        # Provide an initial guess of the function's parameters.  
        a = np.array([peak, r1, r2, delay1, delay2, base])

        min_limits = [ peak_min * max(data),
                       self.rate1_min,
                       self.rate2_min,
                       self.delay1_min,
                       self.delay2_min,
                       base_min * max(data)]

        max_limits = [ peak_max * max(data),
                       self.rate1_max,
                       self.rate2_max,
                       self.delay1_max,
                       self.delay2_max,
                       base_max * max(data)]

        if pair_limits:
            limits = [(amin,amax) for amin,amax in zip(min_limits,max_limits)]
        else:
            limits = [min_limits, max_limits]

        limits = np.array(limits)
    
        return a, limits  
    

    def initial_values_exponential_rate_orig(self, data, pair_limits=False):
        
        t = self.time_axis 
        tmax = t[-1]
        ihalf = int(len(t) / 2.0)
        
        peak_val   = float(self.peak_start   / 100.0)
        peak_min   = float(self.peak_min     / 100.0)
        peak_max   = float(self.peak_max     / 100.0)
        rate1_val  = float(self.rate1_start  / 100.0)
        rate1_min  = float(self.rate1_min    / 100.0)
        rate1_max  = float(self.rate1_max    / 100.0)
        rate2_val  = float(self.rate2_start  / 100.0)
        rate2_min  = float(self.rate2_min    / 100.0)
        rate2_max  = float(self.rate2_max    / 100.0)
        delay1_val = float(self.delay1_start / 100.0)
        delay1_min = float(self.delay1_min   / 100.0)
        delay1_max = float(self.delay1_max   / 100.0)
        delay2_val = float(self.delay2_start / 100.0)
        delay2_min = float(self.delay2_min   / 100.0)
        delay2_max = float(self.delay2_max   / 100.0)
        base_val   = float(self.base_start   / 100.0)
        base_min   = float(self.base_min     / 100.0)
        base_max   = float(self.base_max     / 100.0)
        
        peak   = max(data) * peak_val
        r1     = tmax      * rate1_val     
        r2     = tmax      * rate2_val     
        delay1 = tmax      * delay1_val    
        delay2 = tmax      * delay2_val
        base   = max(data) * base_val
        
        # Provide an initial guess of the function's parameters.  
        a = np.array([peak, r1, r2, delay1, delay2, base])

        min_limits = [ max(data) * peak_min,
                       tmax      * rate1_min,
                       tmax      * rate2_min,
                       tmax      * delay1_min,
                       tmax      * delay2_min,
                       self.noise * base_min]

        max_limits = [ max(data) * peak_max,
                       tmax      * 2 * rate1_max,
                       tmax      * 2 * rate2_max,
                       tmax      * delay1_max,
                       tmax      * delay2_max,
                       max(data) * base_max]

        if pair_limits:
            limits = [(amin,amax) for amin,amax in zip(min_limits,max_limits)]
        else:
            limits = [min_limits, max_limits]

        limits = np.array(limits)
    
        return a, limits   


    def initial_values_exponential_rate_nobase(self, data, pair_limits=False):
        
        t = self.time_axis 
        tmax = t[-1]
        ihalf = int(len(t) / 2.0)
        
        peak_val   = float(self.peak_start / 100.0)
        peak_min   = float(self.peak_min / 100.0)
        peak_max   = float(self.peak_max / 100.0)
        rate1_val  = float(self.rate1_start / 100.0)
        rate1_min  = float(self.rate1_min / 100.0)
        rate1_max  = float(self.rate1_max / 100.0)
        rate2_val  = float(self.rate2_start / 100.0)
        rate2_min  = float(self.rate2_min / 100.0)
        rate2_max  = float(self.rate2_max / 100.0)
        delay1_val = float(self.delay1_start / 100.0)
        delay1_min = float(self.delay1_min / 100.0)
        delay1_max = float(self.delay1_max / 100.0)
        delay2_val = float(self.delay2_start / 100.0)
        delay2_min = float(self.delay2_min / 100.0)
        delay2_max = float(self.delay2_max / 100.0)
        
        peak   = max(data) * peak_val
        r1     = tmax      * rate1_val     
        r2     = tmax      * rate2_val     
        delay1 = tmax      * delay1_val    
        delay2 = tmax      * delay2_val
        
        # Provide an initial guess of the function's parameters.  
        a = np.array([peak, r1, r2, delay1, delay2])

        min_limits = [ max(data) * peak_min,
                       tmax      * rate1_min,
                       tmax      * rate2_min,
                       tmax      * delay1_min,
                       tmax      * delay2_min]

        max_limits = [ max(data) * peak_max,
                       tmax      * 2 * rate1_max,
                       tmax      * 2 * rate2_max,
                       tmax      * delay1_max,
                       tmax      * delay2_max]

        if pair_limits:
            limits = [(amin,amax) for amin,amax in zip(min_limits,max_limits)]
        else:
            limits = [min_limits, max_limits]

        limits = np.array(limits)
    
        return a, limits   
                

    def model_exponential_rate(self, a):
        """
        Basic exponential rate decay.  
        
        s(t)=P*{[1-exp((1/R1)*t1)]-[1-exp((1/R2)*t2)]}+B

        P   = peak intensity, scaling variable
        R1  = intensity rate change, wash in
        R2  = intensity rate change, wash out
        D1  = delay 1, time after switch to 19F mixture
        D2  = delay 2, time after switch to room air
        B   = baseline constant to account for Rician noise

        t1 - zero shifted time course based on delay 1
        t2 - zero shifted time course based on delay 2
        
        """
        tacq = self.time_axis 

        peak = a[0]
        r1   = a[1]
        r2   = a[2]
        d1   = a[3]
        d2   = a[4]
        base = a[5]

        arr = np.zeros([self.dims[-1],], float)

        for i,t in enumerate(tacq):
            val = 1 - np.exp(-((1.0/r1)*(t - d1)))
            if (t-d2) >= 0:
                val -= 1 - np.exp(-((1.0/r2)*(t - d2)))
            val = peak*val + base
            arr[i] = val

        return arr, None
    
    
    def model_exponential_rate_nobase(self, a):
        """
        Basic exponential rate decay.  
        
        s(t)=P*{[1-exp((1/R1)*t1)]-[1-exp((1/R2)*t2)]}+B

        P   = peak intensity, scaling variable
        R1  = intensity rate change, wash in
        R2  = intensity rate change, wash out
        D1  = delay 1, time after switch to 19F mixture
        D2  = delay 2, time after switch to room air
        B   = baseline constant to account for Rician noise

        t1 - zero shifted time course based on delay 1
        t2 - zero shifted time course based on delay 2
        
        """
        tacq = self.time_axis 

        peak = a[0]
        r1   = a[1]
        r2   = a[2]
        d1   = a[3]
        d2   = a[4]
        base = self.noise

        arr = np.zeros([self.dims[-1],], float)

        for i,t in enumerate(tacq):
            val = 1 - np.exp(-((1.0/r1)*(t - d1)))
            if (t-d2) >= 0:
                val -= 1 - np.exp(-((1.0/r2)*(t - d2)))
            val = peak*val + base
            arr[i] = val

        return arr, None  
    
    
    
    
    
    def model_washin_only_lsq(self, a, y, w):
        
        nfree   = np.size(y)-len(a)
        yfit, _ = self.model_washin_only(a)
        chisqr  = np.sum(w*(y-yfit)**2)/nfree
        return chisqr
    
    
    def model_washin_only_nobase_lsq(self, a, y, w):
        
        nfree   = np.size(y)-len(a)
        yfit, _ = self.model_washin_only_nobase(a)
        chisqr  = np.sum(w*(y-yfit)**2)/nfree
        return chisqr


    def initial_values_washin_only(self, data, pair_limits=False):
        
        t = self.time_axis 
        tmax = t[-1]
        ihalf = int(len(t) / 2.0)
        
        peak_val   = float(self.peak_start / 100.0)
        peak_min   = float(self.peak_min / 100.0)
        peak_max   = float(self.peak_max / 100.0)
        base_val   = float(self.base_start / 100.0)
        base_min   = float(self.base_min / 100.0)
        base_max   = float(self.base_max / 100.0)
        
        peak   = peak_val * max(data) 
        r1     = self.rate1_start
        delay1 = self.delay1_start
        base   = base_val * max(data)
        
        # Provide an initial guess of the function's parameters.  
        a = np.array([peak, r1, delay1, base])

        min_limits = [ peak_min * max(data),
                       self.rate1_min,
                       self.delay1_min,
                       base_min * max(data)]

        max_limits = [ peak_max * max(data),
                       self.rate1_max,
                       self.delay1_max,
                       base_max * max(data)]

        if pair_limits:
            limits = [(amin,amax) for amin,amax in zip(min_limits,max_limits)]
        else:
            limits = [min_limits, max_limits]

        limits = np.array(limits)
    
        return a, limits  
    

    def initial_values_washin_only_orig(self, data, pair_limits=False):
        
        t = self.time_axis 
        tmax = t[-1]
        ihalf = int(len(t) / 2.0)
        
        peak_val   = float(self.peak_start   / 100.0)
        peak_min   = float(self.peak_min     / 100.0)
        peak_max   = float(self.peak_max     / 100.0)
        rate1_val  = float(self.rate1_start  / 100.0)
        rate1_min  = float(self.rate1_min    / 100.0)
        rate1_max  = float(self.rate1_max    / 100.0)
        delay1_val = float(self.delay1_start / 100.0)
        delay1_min = float(self.delay1_min   / 100.0)
        delay1_max = float(self.delay1_max   / 100.0)
        base_val   = float(self.base_start   / 100.0)
        base_min   = float(self.base_min     / 100.0)
        base_max   = float(self.base_max     / 100.0)
        
        peak   = max(data) * peak_val
        r1     = tmax      * rate1_val     
        delay1 = tmax      * delay1_val    
        base   = max(data) * base_val
        
        # Provide an initial guess of the function's parameters.  
        a = np.array([peak, r1, delay1, base])

        min_limits = [ max(data) * peak_min,
                       tmax      * rate1_min,
                       tmax      * delay1_min,
                       self.noise * base_min]

        max_limits = [ max(data) * peak_max,
                       tmax      * 2 * rate1_max,
                       tmax      * delay1_max,
                       max(data) * base_max]

        if pair_limits:
            limits = [(amin,amax) for amin,amax in zip(min_limits,max_limits)]
        else:
            limits = [min_limits, max_limits]

        limits = np.array(limits)
    
        return a, limits   


    def initial_values_washin_only_nobase(self, data, pair_limits=False):
        
        t = self.time_axis 
        tmax = t[-1]
        ihalf = int(len(t) / 2.0)
        
        peak_val   = float(self.peak_start / 100.0)
        peak_min   = float(self.peak_min / 100.0)
        peak_max   = float(self.peak_max / 100.0)
        rate1_val  = float(self.rate1_start / 100.0)
        rate1_min  = float(self.rate1_min / 100.0)
        rate1_max  = float(self.rate1_max / 100.0)
        delay1_val = float(self.delay1_start / 100.0)
        delay1_min = float(self.delay1_min / 100.0)
        delay1_max = float(self.delay1_max / 100.0)
        
        peak   = max(data) * peak_val
        r1     = tmax      * rate1_val     
        delay1 = tmax      * delay1_val    
        
        # Provide an initial guess of the function's parameters.  
        a = np.array([peak, r1, delay1])

        min_limits = [ max(data) * peak_min,
                       tmax      * rate1_min,
                       tmax      * delay1_min]

        max_limits = [ max(data) * peak_max,
                       tmax      * 2 * rate1_max,
                       tmax      * delay1_max]

        if pair_limits:
            limits = [(amin,amax) for amin,amax in zip(min_limits,max_limits)]
        else:
            limits = [min_limits, max_limits]

        limits = np.array(limits)
    
        return a, limits   
                

    def model_washin_only(self, a):
        """
        Basic exponential rate decay.  
        
        s(t)=P*[1-exp((1/R1)*t1)]+B

        P   = peak intensity, scaling variable
        R1  = intensity rate change, wash in
        D1  = delay 1, time after switch to 19F mixture
        B   = baseline constant to account for Rician noise

        t1 - zero shifted time course based on delay 1
        
        """
        tacq = self.time_axis 

        peak = a[0]
        r1   = a[1]
        d1   = a[2]
        base = a[3]

        arr = np.zeros([self.dims[-1],], float)

        for i,t in enumerate(tacq):
            val = 1 - np.exp(-((1.0/r1)*(t - d1)))
            val = peak*val + base
            arr[i] = val

        return arr, None
    
    
    def model_washin_only_nobase(self, a):
        """
        Basic exponential rate decay.  
        
        s(t)=P*[1-exp((1/R1)*t1)]+B

        P   = peak intensity, scaling variable
        R1  = intensity rate change, wash in
        D1  = delay 1, time after switch to 19F mixture
        B   = baseline constant to account for Rician noise

        t1 - zero shifted time course based on delay 1
        
        """
        tacq = self.time_axis 

        peak = a[0]
        r1   = a[1]
        d1   = a[2]
        base = self.noise

        arr = np.zeros([self.dims[-1],], float)

        for i,t in enumerate(tacq):
            val = 1 - np.exp(-((1.0/r1)*(t - d1)))
            val = peak*val + base
            arr[i] = val

        return arr, None      
    
    
    
    
    


    def deflate(self, flavor=Deflate.ETREE):
        if flavor == Deflate.ETREE:
            e = ElementTree.Element("timeseries",
                                    {"id" : self.id,
                                     "version" : self.XML_VERSION})

            util_xml.TextSubElement(e, "timeseries_filename", self.timeseries_filename)
            util_xml.TextSubElement(e, "patient_id", self.patient_id)
            util_xml.TextSubElement(e, "series_description", self.series_description)
            util_xml.TextSubElement(e, "study_uid", self.study_uid)
            util_xml.TextSubElement(e, "dicom_path", self.dicom_path)
            util_xml.TextSubElement(e, "output_path", self.output_path)

            for item in self.data_sources:
                util_xml.TextSubElement(e, "data_sources", item)

            e.append(util_xml.numpy_array_to_element(self.element_spacing, "element_spacing"))
            e.append(util_xml.numpy_array_to_element(self.time_axis, "time_axis"))
            e.append(util_xml.numpy_array_to_element(self.data, "data"))

            for attribute in ("time_course_model", 
                              "weight_function",
                              "weight_scale", ):
                util_xml.TextSubElement(e, attribute, getattr(self, attribute))

            # These atttributes are all scalars and map directly to 
            # XML elements of the same name.
            for attribute in ("peak_min",   "peak_start",   "peak_max",
                              "rate1_min",  "rate1_start",  "rate1_max",
                              "rate2_min",  "rate2_start",  "rate2_max",
                              "delay1_min", "delay1_start", "delay1_max",
                              "delay2_min", "delay2_start", "delay2_max",
                              "base_min",   "base_start",   "base_max",):
                util_xml.TextSubElement(e, attribute, getattr(self, attribute))

            element = ElementTree.Element('result_maps', {"type" : "dict"})
            util_xml.dict_to_elements(self.result_maps, element)
            e.append(element)
                     
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

            for attribute in ("timeseries_filename", 
                              "patient_id", 
                              "series_description", 
                              "study_uid", 
                              "dicom_path", 
                              "output_path",
                              "time_course_model", 
                              "weight_function",):
                item = source.findtext(attribute)
                if item is not None:
                    setattr(self, attribute, item)

            self.data_sources = [item.text for item
                                  in source.findall("data_sources")
                                  if item.text]

            self.element_spacing = util_xml.element_to_numpy_array(source.find("element_spacing"))
            self.time_axis  = util_xml.element_to_numpy_array(source.find("time_axis"))
            self.data = util_xml.element_to_numpy_array(source.find("data"))

            # ints
            for attribute in ("weight_scale",
                              "peak_min",   "peak_start",   "peak_max",
                              "rate1_min",  "rate1_start",  "rate1_max",
                              "rate2_min",  "rate2_start",  "rate2_max",
                              "delay1_min", "delay1_start", "delay1_max",
                              "delay2_min", "delay2_start", "delay2_max",
                              "base_min",   "base_start",   "base_max",  ):
                item = source.findtext(attribute)
                if item is not None:
                    setattr(self, attribute, int(float(item)))

            # Now I inflate the attribs that are specific to this class
            node = source.findall("result_maps")
            if node:
                self.result_maps = util_xml.element_to_dict(node[0])


        elif hasattr(source, "keys"):            
            # Quacks like a dict
            raise NotImplementedError



