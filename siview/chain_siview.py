#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules
import numpy as np

# Our modules
import siview.funct_siview_fit as funct_siview_fit
import siview.functor as functor




class ChainSiview(object):
    """ 
    blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
    blah blah blah blah 
    """
    
    def __init__(self, dataset):
        """
        Basically, no processing takes place in this chain because
        all this tab does is reflect the data and headers for the
        data that was read it.
        
        It exists because each processing block has to have an 
        associated chain object.
        
        """
        self.dataset = dataset

        self.fit = None
        self.time = None

        # these will be the functor lists used in the actual chain processing
        self.functors_all = []
        
        # these are all available functors for building the chain
        self.all_functors = {'siview_fit' : funct_siview_fit.FunctSiviewFit()
                            }

        for funct in list(self.all_functors.values()):
            if isinstance(funct, functor.Functor):
                funct.update(self.dataset)

 
    def reset_results_arrays(self):
        '''
        Results array reset is in its own method because it may need to be 
        called at other times that just in the object initialization.
        
        '''
        dims = self.dataset.dims
        if dims:
            dim0      = self.dataset.dims[0]
            self.time = np.zeros(dim0, float)
            self.fit  = np.zeros(dim0, float)


    def update(self):
        '''
        Each processing list of functors is recreated in here from the main
        dictionary of all functor objects.
         
        Then the processing settings in each functor is updated from the 
        values currently set in the parent (self._dataset.set) object
        
        '''
        self.functors_all = []

        #------------------------------------------------------------
        # setup All Functors chain

        self.functors_all.append(self.all_functors['siview_fit'])

        for funct in self.functors_all:
            funct.update(self.dataset) 

 
    def run(self, voxels, entry='all', status=None):
        '''
        Run is the workhorse method that is typically called every time a
        processing setting is changed in the parent (block) object. Run only
        processes data for a single voxel of data at a time.
        
        Results from processing the last call to run() are maintained in
        this object until overwritten by a subsequent call to run(). This 
        allows the View to update itself from these arrays without having 
        to re-run the pipeline every time. 
        
        Use of 'entry points' into the processing pipeline is used to reduce
        the processing required during interactive tasks such as mouse event
        handling while in a canvas.  The downside is that we need to keep 
        copies of results from the processing step just before each entry
        point. This is not too bad because we only have to keep data for one
        voxel's processing at a time.
        
        '''
        # update and run the functor chain
        self.update() 

        # currently all entry points use the same (single) functor
        if entry == 'all':
            functors = self.functors_all
        elif entry == 'slice':
            functors = self.functors_all
        elif entry == 'one':
            functors = self.functors_all

        self.fit_function  = self.dataset.fit_function
        self.init_function = self.dataset.init_function
        self.lsq_function  = self.dataset.lsq_function
        
        weight_function = self.dataset.weight_function
        weight_scale    = self.dataset.weight_scale

        npts = self.dataset.data.shape[-1]
        
        if weight_function == 'Even':
            self.weight_array = np.ones(npts,dtype=float)
        elif weight_function == 'Asymmetric Half-Sine':
            if self.dataset.time_course_model == 'Exponential Rate Decay':
                offset = int(npts/3)
                self.weight_array = weight_scale * np.sin(np.pi*np.arange(npts+offset,dtype=float)[offset:]/(npts+offset-1))+0.5
            else:
                offset = int(npts/3)
                self.weight_array = weight_scale * np.sin(np.pi*np.arange(npts+offset,dtype=float)[offset:]/(npts+offset-1))+0.5
                

        z_last = -1
        for voxel in voxels:
            # local copy of input data

            x,y,z = voxel
            self.time = self.dataset.data[y,x,z,:]
            self.time = self.time.copy()

            if z_last != z:
                print(( 'fitting slice - '+str(z)))
                if status:
                    status('Fitting Slice '+str(z), slot=1)
                z_last = z

            self.fit    = self.time * 0
            self.chis   = 0.0
            self.badfit = 0.0
            
            if self.dataset.time_course_model == 'Exponential Rate Decay':
                self.a      = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            else:
                self.a      = [0.0, 0.0, 0.0, 0.0]
                
            for funct in functors:
                funct.algorithm(self)

            # save data and parameter results into the Block results arrays
            
            if self.dataset.time_course_model == 'Exponential Rate Decay':
                self.dataset.result_maps['Peak'  ][y,x,z] = self.a[0]
                self.dataset.result_maps['R1'    ][y,x,z] = self.a[1]
                self.dataset.result_maps['R2'    ][y,x,z] = self.a[2]
                self.dataset.result_maps['Delay1'][y,x,z] = self.a[3]
                self.dataset.result_maps['Delay2'][y,x,z] = self.a[4]
                if len(self.a) > 5:
                    self.dataset.result_maps['Base'][y,x,z] = self.a[5]
                else:
                    self.dataset.result_maps['Base'][y,x,z] = self.dataset.noise
            else:
                self.dataset.result_maps['Peak'  ][y,x,z] = self.a[0]
                self.dataset.result_maps['R1'    ][y,x,z] = self.a[1]
                self.dataset.result_maps['R2'    ][y,x,z] = 1.0
                self.dataset.result_maps['Delay1'][y,x,z] = self.a[2]
                self.dataset.result_maps['Delay2'][y,x,z] = max(self.dataset.time_axis)
                if len(self.a) > 3:
                    self.dataset.result_maps['Base'][y,x,z] = self.a[3]
                else:
                    self.dataset.result_maps['Base'][y,x,z] = self.dataset.noise
                
            self.dataset.result_maps['Chis'  ][y,x,z] = self.chis
            self.dataset.result_maps['Badfit'][y,x,z] = self.badfit

        return self.fit
 
    