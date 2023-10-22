#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import os
import warnings
import datetime
import time


# 3rd party modules
import wx
import numpy as np
import matplotlib.cm as cm
from scipy.fft import fft, fftshift

# Our modules
import siview.tab_base
import siview.prefs as prefs
import siview.util_menu as util_menu
import siview.constants as constants
import siview.tab_base as tab_base
from siview.plot_panel_spectral import PlotPanelSpectral
from siview.image_panel_siview import ImagePanelSiview

import siview.auto_gui.siview as siview_ui

import siview.common.wx_util as wx_util
from siview.common.dist import dist




#------------------------------------------------------------------------------

class TabSiview(tab_base.Tab, siview_ui.SiviewUI):
    
    def __init__(self, outer_notebook, top, dataset=None):

        siview_ui.SiviewUI.__init__(self, outer_notebook)
        tab_base.Tab.__init__(self, self, top, prefs.PrefsMain)

        # global attributes

        self.top                = top
        self.parent             = outer_notebook
        self.dataset            = dataset
        self.block              = dataset.blocks['spectral']

        # Plot parameters
        self.dataymax       = 1.0       # used for zoom out
        self.voxel          = [0,0,0]   # x,y only, z in islice
        self.itime          = 0
        self.iresult        = 'Integral'
        self.fit_mode       = 'display' # 'display' only, fit 'current' voxel, or fit 'all' voxels

        if   self._prefs.cmap_autumn : self.cmap_results = cm.autumn
        elif self._prefs.cmap_blues  : self.cmap_results = cm.Blues
        elif self._prefs.cmap_jet    : self.cmap_results = cm.jet
        elif self._prefs.cmap_rdbu   : self.cmap_results = cm.RdBu
        elif self._prefs.cmap_gray   : self.cmap_results = cm.gray
        elif self._prefs.cmap_rdylbu : self.cmap_results = cm.RdYlBu

        self.image_mri = self.default_mri()
        self.image_calc = self.default_calc()
        self.ranges_mri = [0,1]
        self.ranges_calc = {'Integral':[0,1], 'First Point':[0,1]}

        # values used in plot and export routines, filled in process()
        self.last_export_filename   = ''
        
        self.plotting_enabled = False

        self.initialize_controls()        
        self.populate_controls()

        self.on_calc_reset(None)
#        self.on_mri_reset(None)

        self.plotting_enabled = True

        self.process_and_display(initialize=True)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy, self)

        # bjs hack - for now process all data into 'spectral' block here
        dat = self.dataset.blocks['raw'].data
        self.dataset.blocks['spectral'].data = fftshift(fft(dat, axis=-1), axes=-1)

        # If the sash position isn't recorded in the INI file, we use the
        # arbitrary-ish value of 400.
        if not self._prefs.sash_position:
            self._prefs.sash_position = 400

        # Under OS X, wx sets the sash position to 10 (why 10?) *after*
        # this method is done. So setting the sash position here does no
        # good. We use wx.CallAfter() to (a) set the sash position and
        # (b) fake an EVT_SPLITTER_SASH_POS_CHANGED.
        wx.CallAfter(self.SplitterWindow.SetSashPosition, self._prefs.sash_position, True)
        wx.CallAfter(self.on_splitter)


    @property
    def view_mode(self):
        return (3 if self._prefs.plot_view_all else 1)


    ##### GUI Setup Handlers ##################################################

    def initialize_controls(self):
        """ 
        This methods goes through the widgets and sets up certain sizes
        and constraints for those widgets. This method does not set the 
        value of any widget except insofar that it is outside a min/max
        range as those are being set up. 
        
        Use populate_controls() to set the values of the widgets from
        a data object.
        """

        # calculate a few useful values
        
        dataset  = self.dataset
        dims = dataset.spectral_dims[::-1]

        # The many controls on various tabs need configuration of
        # their size, # of digits displayed, increment and min/max. 

        wx_util.configure_spin(self.SpinX, 50, min_max=(1, dims[2]))
        wx_util.configure_spin(self.SpinY, 50, min_max=(1, dims[1]))
        wx_util.configure_spin(self.SpinZ, 50, min_max=(1, dims[0]))
        wx_util.configure_spin(self.FloatScale, 70, 4, None, (0.0001, 1000))
        self.FloatScale.multiplier = 1.1
        
        # Settings Tab values
        vals = ['Model1', 'Model2']
        self.ChoiceModel.Clear()
        self.ChoiceModel.AppendItems( vals )

        wx_util.configure_spin(self.SpinSliceIndex,   60, min_max=(1, dims[0]))
        wx_util.configure_spin(self.FloatCalcFloor, 60, 3, None, min_max=(-1000,1000))
        wx_util.configure_spin(self.FloatCalcCeil,  60, 3, None, min_max=(-1000,1000))
        # wx_util.configure_spin(self.SpinMriFloor,     60, min_max=(-1000,1000))
        # wx_util.configure_spin(self.SpinMriCeil,      60, min_max=(-1000,1000))

        self.ButtonCalcReset.SetSize(wx.Size(40,-1))
        # self.ButtonMriReset.SetSize(wx.Size(40,-1))



    def populate_controls(self):
        """ 
        Populates the widgets with relevant values from the data object. 
        It's meant to be called when a new data object is loaded.
        
        This function trusts that the data object it is given doesn't violate
        any rules. Whatever is in the data object gets slapped into the 
        controls, no questions asked. 
        
        """
        dataset = self.dataset
        dims = dataset.spectral_dims[::-1]

        #############################################################
        # Global controls            
        #############################################################
        
        self.TextSource.SetValue(self.dataset.data_sources[0])

        self.ChoiceModel.SetStringSelection('Integral')

        self.SpinSliceIndex.SetValue(1)
        self.FloatCalcFloor.SetValue(self.ranges_calc['Integral'][0])
        self.FloatCalcCeil.SetValue(self.ranges_calc['Integral'][1])
        # self.SpinMriFloor.SetValue(self.ranges_mri[0])
        # self.SpinMriCeil.SetValue(self.ranges_mri[1])


        #############################################################
        # Dataset View setup 
        #############################################################

        self.view = PlotPanelSpectral(self.PanelPlot,
                                      self,
                                      self,
                                      naxes=1,
                                      reversex=True,
                                      zoom='span',
                                      reference=True,
                                      middle=True,
                                      zoom_button=1,
                                      middle_button=3,
                                      refs_button=2,
                                      do_zoom_select_event=True,
                                      do_zoom_motion_event=True,
                                      do_refs_select_event=True,
                                      do_refs_motion_event=True,
                                      do_middle_select_event=True,
                                      do_middle_motion_event=True,
                                      do_scroll_event=True,
                                      props_zoom=dict(alpha=0.2, facecolor='yellow'),
                                      props_cursor=dict(alpha=0.2, facecolor='gray'),
                                      xscale_bump=0.0,
                                      yscale_bump=0.05,
                                      data = [],
                                      prefs=self._prefs,
                                      dataset=self.dataset,
                                      )

        # weird work around for Wx issue where it can't initialize and get RGBA buffer because height = 0?
        self.PanelPlot.SetSize((6,8))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.view, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.PanelPlot.SetSizer(sizer)
        self.view.Fit()
        self.view.change_naxes(1)
        
        
        self.image = ImagePanelSiview(  self.PanelImage,
                                        self,
                                        self.parent,
                                        naxes=1,
                                        data=[],
                                        vertOn=True, 
                                        horizOn=True,
#                                        layout='horiz'
                                     )
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.image, 1, wx.LEFT | wx.CENTER | wx.EXPAND)
        self.PanelImage.SetSizer(sizer)
        self.image.Fit()              

        self.view.dataymax = 150.0
        self.view.set_vertical_scale(150.0)
        self.FloatScale.SetValue(self.view.vertical_scale)


    ##### Menu & Notebook Event Handlers ######################################################

    def on_activation(self):
        # This is a faux event handler. wx doesn't call it directly. It's 
        # a notification from my parent (the dataset notebook) to let
        # me know that this tab has become the current one.
        
        # Force the View menu to match the current plot options.
        util_menu.bar.set_menu_from_state(self._prefs.menu_state)
       

    def on_destroy(self, event):
        self._prefs.save()


    def on_splitter(self, event=None):
        # This is sometimes called programmatically, in which case event is None
        self._prefs.sash_position = self.SplitterWindow.GetSashPosition()


    def on_menu_view_option(self, event):
        event_id = event.GetId()

        if self._prefs.handle_event(event_id):
            if event_id in (util_menu.ViewIds.ZERO_LINE_SHOW,
                            util_menu.ViewIds.ZERO_LINE_TOP,
                            util_menu.ViewIds.ZERO_LINE_MIDDLE,
                            util_menu.ViewIds.ZERO_LINE_BOTTOM,
                            util_menu.ViewIds.XAXIS_SHOW,
                           ):
                self.view.update_axes()
                self.view.canvas.draw()



            elif event_id in (util_menu.ViewIds.DATA_TYPE_REAL,
                              util_menu.ViewIds.DATA_TYPE_IMAGINARY,
                              util_menu.ViewIds.DATA_TYPE_MAGNITUDE,
                             ):
                if event_id == util_menu.ViewIds.DATA_TYPE_REAL:
                    self.view.set_data_type_real()
                elif event_id == util_menu.ViewIds.DATA_TYPE_IMAGINARY:
                    self.view.set_data_type_imaginary()
                elif event_id == util_menu.ViewIds.DATA_TYPE_MAGNITUDE:
                    self.view.set_data_type_magnitude()

                self.view.update(no_draw=True)
                self.view.set_phase_0(0.0, no_draw=True)
                self.view.canvas.draw()


        formats = { util_menu.ViewIds.CMAP_AUTUMN : cm.autumn,
                    util_menu.ViewIds.CMAP_BLUES  : cm.Blues, 
                    util_menu.ViewIds.CMAP_JET    : cm.jet, 
                    util_menu.ViewIds.CMAP_RDBU   : cm.RdBu, 
                    util_menu.ViewIds.CMAP_GRAY   : cm.gray, 
                    util_menu.ViewIds.CMAP_RDYLBU : cm.RdYlBu, 
                  }
        if event_id in formats:
            self.cmap_results = formats[event_id]
            self.show()





    ########## Widget Event Handlers ####################    

    def on_voxel(self, event):
        self.set_voxel()

    def set_voxel(self):
        tmpx = self.SpinX.GetValue()-1
        tmpy = self.SpinY.GetValue()-1
        tmpz = self.SpinZ.GetValue()-1
        dims = self.dataset.spectral_dims[::-1]
        tmpx = max(0, min(dims[2]-1, tmpx))  # clip to range
        tmpy = max(0, min(dims[1]-1, tmpy))
        tmpz = max(0, min(dims[0]-1, tmpz))
        self.SpinX.SetValue(tmpx+1)
        self.SpinY.SetValue(tmpy+1)
        self.SpinZ.SetValue(tmpz+1)
        self.voxel = [tmpx, tmpy, tmpz]
        self.process()
        self.plot()

    def on_scale(self, event):
        view = self.view
        scale = self.FloatScale.GetValue()
        if scale > view.vertical_scale:
            view.set_vertical_scale(1.0, scale_mult=1.1)
        else:
            view.set_vertical_scale(-1.0, scale_mult=1.1)
        self.FloatScale.SetValue(view.vertical_scale)

    # Image Control events ---------------------------------------

    def on_slice_index(self, event):
        # Index spinner changed. Here we allow the control to update itself.
        # If we don't, then there can be a noticeable & confusing pause 
        # between interacting with the control and seeing it actually change.
        wx.CallAfter(self._slice_index_changed)

    def _slice_index_changed(self):
        tmp  = self.SpinSliceIndex.GetValue() - 1
        dims = self.dataset.dims
        tmp  = max(0, min(dims[3]-1, tmp))      # clip to range
        self.itime = tmp
        self.show()

    def on_calc_image(self, event):
        # Results choice changed. Here we allow the control to update itself.
        # If we don't, then there can be a noticeable & confusing pause 
        # between interacting with the control and seeing it actually change.
        wx.CallAfter(self._calc_image_changed)

    def _calc_image_changed(self):
        indx = self.ChoiceCalcImage.GetSelection()
        key  = self.ChoiceCalcImage.GetString(indx)
        self.iresult = key
        self.FloatCalcCeil.SetValue(self.ranges_calc[key][1])
        self.FloatCalcFloor.SetValue(self.ranges_calc[key][0])
        self.process_image()
        self.show()

    def on_calc_range(self, event):
        indx = self.ChoiceCalcImage.GetSelection()
        key  = self.ChoiceCalcImage.GetString(indx)
        ceil_val  = self.FloatCalcCeil.GetValue()
        floor_val = self.FloatCalcFloor.GetValue()
        self.ranges_calc[key] = [floor_val, ceil_val] if floor_val<ceil_val else [ceil_val, floor_val]
        self.FloatCalcFloor.SetValue(self.ranges_calc[key][0])
        self.FloatCalcCeil.SetValue(self.ranges_calc[key][1])
        self.show()

    def on_calc_reset(self, event):
        indx = self.ChoiceCalcImage.GetSelection()
        key  = self.ChoiceCalcImage.GetString(indx)
        dat  = self.image_calc[key]
        ceil_val  = np.nanmax(dat)
        floor_val = np.nanmin(dat)
        self.ranges_calc[key] = [floor_val, ceil_val] if floor_val<ceil_val else [ceil_val, floor_val]
        self.FloatCalcFloor.SetValue(self.ranges_calc[key][0])
        self.FloatCalcCeil.SetValue(self.ranges_calc[key][1])
        self.show()
        
    # def on_mri_range(self, event):
    #     ceil_val  = self.SpinMriCeil.GetValue()
    #     floor_val = self.SpinMriFloor.GetValue()
    #     self.ranges_mri = [floor_val, ceil_val] if floor_val<ceil_val else [ceil_val, floor_val]
    #     self.SpinMriFloor.SetValue(self.ranges_mri[0])
    #     self.SpinMriCeil.SetValue(self.ranges_mri[1])
    #     self.show()
    #
    # def on_mri_reset(self, event):
    #     dat = self.image_mri
    #     ceil_val  = dat.max()
    #     floor_val = dat.min()
    #     self.ranges_mri = [floor_val, ceil_val]
    #     self.SpinMriCeil.SetValue(ceil_val)
    #     self.SpinMriFloor.SetValue(floor_val)
    #     self.show()

    def on_model(self, event):
        indx = self.ChoiceModel.GetSelection()
        key  = self.ChoiceModel.GetString(indx)
        self.model = key

    # Spectral Control events ---------------------------------------

    def on_apodization_method(self, event):
        index = event.GetEventObject().GetSelection()
        apodization = list(constants.Apodization.choices.keys())[index]
        self.block.set.apodization = apodization
            # Enable the value textbox if a method is selected
        self.FloatWidth.Enable(bool(apodization))
        self.process_and_plot()

    def on_apodization_value(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.apodization_width = value
        self.process_and_plot()

    def on_b0_shift(self, event):
        value = event.GetEventObject().GetValue()
        voxel = self.voxel
        self.dataset.set_frequency_shift(value, voxel)     # set absolute shift
        self.process_and_plot()

    def on_phase0(self, event):
        # phase 0 respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        voxel = self._tab_dataset.voxel
        orig = self.dataset.get_phase_0(voxel)
        self.set_phase_0(value-orig, voxel)         # sets delta change

    def on_phase1(self, event):
        # phase 1 respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        voxel = self._tab_dataset.voxel
        orig = self.dataset.get_phase_1(voxel)
        self.set_phase_1(value-orig, voxel)         # sets delta change

    def on_phase1_zero(self, event):
        # phase 1 zero respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        voxel = self._tab_dataset.voxel
        self.block.phase_1_lock_at_zero = value
        if value:
            self.dataset.set_phase_1(0.0, voxel)    # value is NULL here since method checks the 'lock' flag
            self.FloatPhase1.SetValue(0.0)
        self.CheckZeroPhase1.SetValue(value)
        self.process_and_plot( )

    def on_phase1_pivot(self, event):
        # phase 1 pivot respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        self.set_phase1_pivot(value)

    def set_phase1_pivot(self, value):
        self.block.set.phase_1_pivot = value
        self.FloatPhase1Pivot.SetValue(value)
        self.process_and_plot()


    def on_fit_all(self, event):
        pass
        # self.top.statusbar.SetStatusText((" Fitting All Voxels "), 1)
        # self.process()
        # self.plot()
        # self.show()





    ##### Internal helper functions  ##########################################

    def set_frequency_shift(self, delta, voxel, auto_calc=False, entry='all'):
        '''
        Phase0, phase 1 and frequency shift are all parameters that affect the
        data in the spectral tab, however, they can also be changed in other
        places using either widgets or mouse canvas events. In the end, these
        GUI interactions are all changing the same variables located in the
        block_spectral object.

        Because these can be changed by "between tabs" actions, I've located
        these methods at this level so that one datasest does not ever talk
        directly to another tab, but just to a parent (or grandparent).

        '''
        b0shift = self.block.get_frequency_shift(voxel)
        b0shift = b0shift + delta
        self.block.set_frequency_shift(b0shift, voxel)
        self.FloatFrequency.SetValue(b0shift)
        self.plot_results = self.block.chain.run([voxel]) #, entry=entry)
        self.plot()


    def set_phase_0(self, delta, voxel, auto_calc=False):
        '''
        This method only updates block values and widget settings, not view
        display. That is done in the set_xxx_x_view() method.

        '''
        phase_0 = self.block.get_phase_0(voxel)
        phase_0 = (phase_0  + delta) # % 360
        self.block.set_phase_0(phase_0,voxel)
        self.FloatPhase0.SetValue(phase_0)


    def set_phase_0_view(self, voxel):
        phase0 = self.block.get_phase_0(voxel)
        self.view.set_phase_0(phase0, index=[0], absolute=True, no_draw=True)
        self.view.canvas.draw()


    def set_phase_1(self, delta, voxel, auto_calc=False):
        '''
        Phase0, phase 1 and frequency shift are all parameters that affect the
        data in the spectral tab, however, they can also be changed in other
        places using either widgets or mouse canvas events. In the end, these
        GUI interactions are all changing the same variables located in the
        block_spectral object.

        Because these can be changed by "between tabs" actions, I've located
        these methods at this level so that one tab does not ever talk directly
        to another tab, but just to a parent (or grandparent).

        '''
        # check if phase1 is locked at zero
        if not self.block.phase_1_lock_at_zero:
            phase_1 = self.block.get_phase_1(voxel)
            phase_1 = phase_1  + delta
        else:
            phase_1 = 0.0

        self.block.set_phase_1(phase_1,voxel)
        self.FloatPhase1.SetValue(phase_1)


    def set_phase_1_view(self, voxel):
        phase1 = self.block.get_phase_1(voxel)
        self.view.set_phase_1(phase1, index=[0], absolute=True, no_draw=True)
        self.view.canvas.draw()


    def chain_status(self, msg, slot=1):
        self.top.statusbar.SetStatusText((msg), slot)


    def process_and_display(self, initialize=False):
        
        self.process()
        self.plot(initialize=initialize)
        self.show(keep_norm=not initialize)


    def process(self):
        """ 
        Currently this is just an FFT and FFTSHIFT.  May add more in future.
        
        """
        voxel = [self.voxel]
        entry = 'one'
        self.plot_results = self.block.chain.run(voxel, entry=entry)

        # if self.fit_mode == 'all':
        #     voxel = self.dataset.get_all_voxels()  # list of tuples, with mask != 0
        #     entry = 'all'
        #     self.plot_results = self.dataset.chain.run(voxel, entry=entry, status=self.chain_status)

    def process_image(self):
        """
        Currently this is just an First FID point or Sum across ref lines in plot

        """
        voxel = [self.voxel]
        if self.iresult == 'Integral':
            dat = self.dataset.blocks['spectral'].data
            istr = 360 #0
            iend = 400 #dat.shape[-1]
            if self.view.data_type[0] == 'magnitude':
                dat = np.sum(np.abs(dat[:,:,:,istr:iend]),axis=-1)
            elif self.view.data_type[0] == 'real':
                dat = np.sum(dat[:,:,:,istr:iend].real, axis=-1)
            elif  self.view.data_type[0] == 'imaginary':
                dat = np.sum(dat[:,:,:,istr:iend].imag, axis=-1)
            else:
                dat = dat[:,:,:,0].real * 0
            self.image_calc[self.iresult] = dat

        elif self.iresult == 'First Point':
            dat = (np.abs(self.dataset.blocks['raw'].data[:,:,:,0]))
            self.image_calc[self.iresult] = dat


    def plot(self, is_replot=False, initialize=False):

        if self.dataset == None:
            return

        if self.plotting_enabled:

            voxel = self.voxel
            data1 = self.plot_results['freq']
            ph0_1 = self.dataset.get_phase_0(voxel)
            ph1_1 = self.dataset.get_phase_1(voxel)

            data = [[data1], ]
            self.view.set_data(data)
            self.view.update(no_draw=True, set_scale=not self._scale_initialized)

            if not self._scale_initialized:
                self._scale_initialized = True

            # we take this opportunity to ensure that our phase values reflect
            # the values in the block.
            self.view.set_phase_0(ph0_1, absolute=True, no_draw=True, index=[0])
            self.view.set_phase_1(ph1_1, absolute=True, no_draw=True, index=[0])

            self.view.canvas.draw()

            # Calculate the new area after phasing
            area, rms = self.view.calculate_area()
            self.top.statusbar.SetStatusText(self.build_area_text(area[0], rms[0], plot_label='A'), 3)


    def show(self, keep_norm=True):

        if not self.plotting_enabled: 
            return
        
        if self.dataset == None:
            return
    
        voxel = self.voxel
        
#        dat1 = self.image_mri[:,:, self.itime]
        dat2 = self.image_calc[self.iresult][voxel[2],:,:]

        data2 =  [{'data'      : dat2,
                   'cmap'      : self.cmap_results,
                   'alpha'     : 1.0,
                   'vmax'      : self.ranges_calc[self.iresult][1],     # ignores NaN values
                   'vmin'      : self.ranges_calc[self.iresult][0],
                   'keep_norm' : False          }]

        # data1 =  [{'data'      : dat1,
        #            'cmap'      : cm.gray,
        #            'alpha'     : 1.0,
        #            'vmax'      : self.ranges_mri[1],
        #            'vmin'      : self.ranges_mri[0],
        #            'keep_norm' : False         }]


#        data = [data1,data2]
        data = [data2,]
        self.image.set_data(data, keep_norm=keep_norm)
        self.image.update(no_draw=True, keep_norm=keep_norm)
        self.image.canvas.draw()


    def default_mri(self):
        r = dist(24)
        r.shape = 1, r.shape[0], r.shape[1]
        return r

    def default_calc(self):
        ri = dist(24)
        ri.shape = 1, ri.shape[0], ri.shape[1]
        rf = dist(24)
        rf.shape = 1, rf.shape[0], rf.shape[1]

        return {'Integral':ri, 'First Point':rf}

