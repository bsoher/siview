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
        
        # global attributes

        self.top                = top
        self.parent             = outer_notebook
        self.dataset            = dataset
        self.block              = dataset.blocks['spectral']

        self._prefs = prefs.PrefsMain()

        # Plot parameters
        self.dataymax       = 1.0       # used for zoom out
        self.voxel          = [0,0,0]   # x,y only, z in islice
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
        self.on_calc_reset(None)
        self.on_mri_reset(None)

        # values used in plot and export routines, filled in process()
        self.last_export_filename   = ''
        
        self.plotting_enabled = False

        self.initialize_controls()        
        self.populate_controls()
        
        self.plotting_enabled = True
        
        self.process_and_display(initialize=True)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy, self)

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

        t = self.dataset.time_axis 
        tmax = t[-1]
        
        # The many controls on various tabs need configuration of
        # their size, # of digits displayed, increment and min/max. 

        wx_util.configure_spin(self.FloatScale, 70, 4, None, (0.0001, 1000))
        self.FloatScale.multiplier = 1.1
        
        # Slider values
        self.SliderTop.SetRange(1, 1)
        self.SliderTop.SetValue(1)

        # Settings Tab values
        vals = ['Model1', 'Model2']
        self.ChoiceModel.Clear()
        self.ChoiceModel.AppendItems( vals )

        wx_util.configure_spin(self.SpinCalcFloor,    60, min_max=(-1000,1000))
        wx_util.configure_spin(self.SpinCalcCeil,     60, min_max=(-1000,1000))
        wx_util.configure_spin(self.SpinMriFloor,     60, min_max=(-1000,1000))
        wx_util.configure_spin(self.SpinMriCeil,      60, min_max=(-1000,1000))

        self.ButtonCalcReset.SetSize(wx.Size(40,-1))
        self.ButtonMriReset.SetSize(wx.Size(40,-1))

        # There's a lot of ways to change sliders -- dragging the thumb,
        # clicking on either side of the thumb, using the arrow keys to 
        # move one tick at a time, and hitting home/end. Fortunately all
        # platforms cook these down into a simple "the value changed" event.
        # Unfortunately it has different names depending on the platform.
        if "__WXMAC__" in wx.PlatformInfo:
            event = wx.EVT_SCROLL_THUMBRELEASE
        else:
            event = wx.EVT_SCROLL_CHANGED
            
        self.Bind(event, self.on_slider_changed_top, self.SliderTop)   
        

    def populate_controls(self):
        """ 
        Populates the widgets with relevant values from the data object. 
        It's meant to be called when a new data object is loaded.
        
        This function trusts that the data object it is given doesn't violate
        any rules. Whatever is in the data object gets slapped into the 
        controls, no questions asked. 
        
        """
        dataset = self.dataset

        #############################################################
        # Global controls            
        #############################################################
        
        self.TextSource.SetValue(self.dataset.data_sources[0])

        self.ChoiceModel.SetStringSelection('Integral')

        self.SpinCalcFloor.SetValue(self.ranges_calc['Integral'][0])
        self.SpinCalcCeil.SetValue(self.ranges_calc['Integral'][1])
        self.SpinMriFloor.SetValue(self.ranges_mri[0])
        self.SpinMriCeil.SetValue(self.ranges_mri[1])


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
                                        naxes=2,
                                        data=[],
                                        vertOn=True, 
                                        horizOn=True
                                     )
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.image, 1, wx.LEFT | wx.CENTER | wx.EXPAND)
        self.PanelImage.SetSizer(sizer)
        self.image.Fit()              

        self.view.dataymax = 150.0
        self.view.set_vertical_scale_abs(150.0)
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
            if event_id in (util_menu.ViewIds.ZERO_LINE_PLOT_SHOW,
                            util_menu.ViewIds.ZERO_LINE_PLOT_TOP,
                            util_menu.ViewIds.ZERO_LINE_PLOT_MIDDLE,
                            util_menu.ViewIds.ZERO_LINE_PLOT_BOTTOM,
                            util_menu.ViewIds.XAXIS_SHOW,
                           ):
                self.view.update_axes()
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


    # def on_menu_view_output(self, event):
    #
    #     event_id = event.GetId()
    #
    #     formats = { util_menu.ViewIds.VIEW_TO_PNG : "PNG",
    #                 util_menu.ViewIds.VIEW_TO_SVG : "SVG",
    #                 util_menu.ViewIds.VIEW_TO_EPS : "EPS",
    #                 util_menu.ViewIds.VIEW_TO_PDF : "PDF",
    #               }
    #
    #     if event_id in formats:
    #         format = formats[event_id]
    #         lformat = format.lower()
    #         filter_ = "%s files (*.%s)|*.%s" % (format, lformat, lformat)
    #         figure = self.view.figure
    #
    #         filename = common_dialogs.save_as("", filter_)
    #
    #         if filename:
    #             msg = ""
    #             try:
    #                 figure.savefig( filename,
    #                                 dpi=300,
    #                                 facecolor='w',
    #                                 edgecolor='w',
    #                                 orientation='portrait',
    #                                 papertype='letter',
    #                                 format=None,
    #                                 transparent=False)
    #             except IOError:
    #                 msg = """I can't write the file "%s".""" % filename
    #
    #             if msg:
    #                 common_dialogs.message(msg, style=common_dialogs.E_OK)
    #
    #     outype2 = { util_menu.ViewIds.MASK_TO_MOSAIC : "mask",
    #                 util_menu.ViewIds.FITS_TO_MOSAIC : "fits",
    #               }
    #
    #
    #     outype3 = { util_menu.ViewIds.MASK_TO_STRIP : "mask",
    #                 util_menu.ViewIds.FITS_TO_STRIP : "fits",
    #               }
    #
    #     if event_id in outype3:
    #         from matplotlib import pyplot as plt
    #
    #         self.top.statusbar.SetStatusText((" Outputting to Strip ..."), 1)
    #
    #         outype = outype3[event_id]
    #         if outype == 'mask':
    #             labels = ['Mask']
    #         elif outype == 'fits':
    #             labels = ['Integral', 'First Point']
    #         datas = []
    #         for key in labels:
    #             datas.append(self.dataset.result_maps[key])
    #
    #         filetypes, exts, filter_index = self.image.canvas._get_imagesave_wildcards()
    #         default_file = self.image.canvas.get_default_filename()
    #         dlg = wx.FileDialog(self, "Save to file", "", default_file,
    #                             filetypes, wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
    #         dlg.SetFilterIndex(filter_index)
    #         if dlg.ShowModal() == wx.ID_OK:
    #             dirname  = dlg.GetDirectory()
    #             filename = dlg.GetFilename()
    #             formt    = exts[dlg.GetFilterIndex()]
    #             basename, ext = os.path.splitext(filename)
    #             if ext.startswith('.'):
    #                 ext = ext[1:]
    #             if ext in ('svg', 'pdf', 'ps', 'eps', 'png') and formt!=ext:
    #                 #looks like they forgot to set the image type drop
    #                 #down, going with the extension.
    #                 warnings.warn('extension %s did not match the selected image type %s; going with %s'%(ext, formt, ext), stacklevel=0)
    #                 formt = ext
    #
    #             if outype == 'mask':
    #                 filename = basename+'_mask_strips.'+ext
    #             if outype == 'fits':
    #                 filename = basename+'_fits_strips.'+ext
    #
    #             data = datas
    #             nrow = len(datas)
    #             ncol = data[0].shape[-1]
    #             dpi  = 100
    #
    #             dim0 = data[0].shape[0]
    #             dim1 = data[0].shape[1]
    #
    #             xstr  = self.chop_x
    #             ystr  = self.chop_y
    #             xend  = dim0 - xstr
    #             yend  = dim1 - ystr
    #
    #             xsize = dim0 - self.chop_x*2
    #             ysize = dim1 - self.chop_y*2
    #
    #             xsiz = float(xsize * ncol) / float(dpi)
    #             ysiz = float(ysize * nrow) / float(dpi)
    #
    #             figure = plt.figure(dpi=dpi,figsize=(xsiz,ysiz))
    #
    #             axes = []
    #             for j in range(nrow):
    #                 for i in range(ncol):
    #                     axes.append(figure.add_subplot(nrow,ncol,ncol*j+i+1))
    #
    #             for axis in axes:
    #                 axis.xaxis.set_visible(False)
    #                 axis.yaxis.set_visible(False)
    #
    #             figure.subplots_adjust( left=0,right=1, bottom=0,top=1, wspace=0.0,hspace=0.0 )
    #
    #             cmap = self.cmap_results
    #
    #             for j in range(nrow):
    #
    #                 if outype == 'mask' or (data[j].min() == data[j].max() == 0):
    #                     vmin = 0.0
    #                     vmax = 1.0
    #                 else:
    #                     vmin = np.nanmin(data[j])
    #                     vmax = np.nanmax(data[j])
    #
    #                 for i in range(ncol):
    #                     im = data[j][ystr:yend,xstr:xend,i]
    #                     if labels[j] == 'Delay1':
    #                         # lower values outside mask to min value for clearer images
    #                         msk = datas[0][ystr:yend,xstr:xend,i]
    #                         im = im.copy()
    #                         im[msk<=0] = vmin
    #                     axes[j*ncol+i].imshow(im, cmap=cmap, vmax=vmax, vmin=vmin, aspect='equal', origin='upper')
    #
    #             try:
    #                 plt.savefig(os.path.join(dirname, filename), dpi=dpi, bbox_inches='tight', pad_inches=0)
    #                 plt.close()
    #             except Exception as e:
    #                 plt.close()
    #                 dialog = wx.MessageDialog(parent  = self,
    #                                           message = str(e),
    #                                           caption = 'Matplotlib backend_wx error',
    #                                           style=wx.OK | wx.CENTRE)
    #                 dialog.ShowModal()
    #                 dialog.Destroy()
    #
    #
    #
    #         self.top.statusbar.SetStatusText((" "), 1)
    #




    ########## Widget Event Handlers ####################    
    
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
        # dims = self.dataset.dims
        # tmp  = max(0, min(dims[3]-1, tmp))      # clip to range
        # self.itime = tmp
        # self.show()

    def on_calc_image(self, event):
        # Results choice changed. Here we allow the control to update itself.
        # If we don't, then there can be a noticeable & confusing pause 
        # between interacting with the control and seeing it actually change.
        wx.CallAfter(self._calc_image_changed)

    def _calc_image_changed(self):
        indx = self.ChoiceCalcImage.GetSelection()
        key  = self.ChoiceCalcImage.GetString(indx)
        self.iresult = key
        self.SpinCalcCeil.SetValue(self.ranges_calc[key][1])
        self.SpinCalcFloor.SetValue(self.ranges_calc[key][0])
        self.show()

    def on_calc_range(self, event):
        indx = self.ChoiceCalcImage.GetSelection()
        key  = self.ChoiceCalcImage.GetString(indx)
        ceil_val  = self.SpinCalcCeil.GetValue()
        floor_val = self.SpinCalcFloor.GetValue()
        self.ranges_calc[key] = [floor_val, ceil_val] if floor_val<ceil else [ceil_val, floor_val]
        self.SpinCalcFloor.SetValue(self.ranges_calc[0])
        self.SpinCalcCeil.SetValue(self.ranges_calc[1])
        self.show()

    def on_calc_reset(self, event):
        indx = self.ChoiceCalcImage.GetSelection()
        key  = self.ChoiceCalcImage.GetString(indx)
        dat  = self.images_calc[key]
        ceil_val  = np.nanmax(dat)
        floor_val = np.nanmin(dat)
        self.ranges_calc[key] = [floor_val, ceil_val] if floor_val<ceil else [ceil_val, floor_val]
        self.SpinCalcFloor.SetValue(self.ranges_calc[0])
        self.SpinCalcCeil.SetValue(self.ranges_calc[1])
        self.show()
        
    def on_mri_range(self, event):
        ceil_val  = self.SpinMriCeil.GetValue()
        floor_val = self.SpinMriFloor.GetValue()
        self.ranges_mri = [floor_val, ceil_val] if floor_val<ceil else [ceil_val, floor_val]
        self.SpinMriFloor.SetValue(self.ranges_mri[0])
        self.SpinMriCeil.SetValue(self.ranges_mri[1])
        self.show()

    def on_mri_reset(self, event):
        dat = self.image_mri
        ceil_val  = dat.max()
        floor_val = dat.min()
        self.ranges_mri = [floor_val, ceil_val]
        self.SpinMriCeil.SetValue(ceil_val)
        self.SpinMriFloor.SetValue(floor_val)
        self.show()

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
        orig = self.dataset.get_frequency_shift(voxel)
        self.dataset.set_frequency_shift(value-orig, voxel)     # send delta shift

    def on_phase0(self, event):
        # phase 0 respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        voxel = self._tab_dataset.voxel
        orig = self.dataset.get_phase_0(voxel)
        # we use the notebook level method to deal with this change because it
        # covers all the actions that need to be taken for manual changes
        poll_labels = [self._tab_dataset.indexAB[0]]
        if self.do_sync:
            poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
        self.top.notebook_datasets.global_poll_phase(poll_labels, value-orig, voxel, do_zero=True)

    def on_phase1(self, event):
        # phase 1 respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        voxel = self._tab_dataset.voxel
        orig = self.dataset.get_phase_1(voxel)
        # we use the notebook level method to deal with this change because it
        # covers all the actions that need to be taken for manual changes
        poll_labels = [self._tab_dataset.indexAB[0]]
        if self.do_sync:
            poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
        self.top.notebook_datasets.global_poll_phase(poll_labels, value-orig, voxel, do_zero=False)

    def on_phase1_zero(self, event):
        # phase 1 zero respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        nb = self.top.notebook_datasets
        poll_labels = [self._tab_dataset.indexAB[0]]
        if self.do_sync:
            poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
        nb.global_poll_sync_event(poll_labels, value, event='phase1_zero')

    def on_phase1_pivot(self, event):
        # phase 1 pivot respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        nb = self.top.notebook_datasets
        poll_labels = [self._tab_dataset.indexAB[0]]
        if self.do_sync:
            poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
        nb.global_poll_sync_event(poll_labels, value, event='phase1_pivot')

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
        tab.view.canvas.draw()


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
        phase1 = tab.block.get_phase_1(voxel)
        tab.view.set_phase_1(phase1, index=[0], absolute=True, no_draw=True)
        tab.view.canvas.draw()


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
        self.plot_results = self.block.chain.run(voxel, entry=entry, status=self.chain_status)

        # if self.fit_mode == 'all':
        #     voxel = self.dataset.get_all_voxels()  # list of tuples, with mask != 0
        #     entry = 'all'
        #     self.plot_results = self.dataset.chain.run(voxel, entry=entry, status=self.chain_status)

                        
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
            self.view.update(no_draw=True, set_scale=not self._scale_intialized)

            if not self._scale_intialized:
                self._scale_intialized = True

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
        
        dat1 = self.image_mri[:,:, voxel[2], self.itime]
        dat2 = self.image_calc[self.iresult][:,:, voxel[2]]

        data1 =  [{'data'      : dat1,
                   'cmap'      : cm.gray,
                   'alpha'     : 1.0,
                   'vmax'      : self.ranges_mri[1],
                   'vmin'      : self.ranges_mri[0],
                   'keep_norm' : False         }] 

        data2 =  [{'data'      : dat2,
                   'cmap'      : self.cmap_results,
                   'alpha'     : 1.0,
                   'vmax'      : self.ranges_calc[self.iresult][1],     # ignores NaN values
                   'vmin'      : self.ranges_calc[self.iresult][0],
                   'keep_norm' : False          }] 

        data = [data1,data2]
        self.image.set_data(data, keep_norm=keep_norm)
        self.image.update(no_draw=True, keep_norm=keep_norm)
        self.image.canvas.draw()


    def default_mri(self):
        return dist(256)

    def default_calc(self):
        return {'Integral':dist(24), 'First Point':dist(24)}

