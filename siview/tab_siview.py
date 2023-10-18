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
try:
    import pydicom
except ImportError:
    import dicom as pydicom
import numpy as np
import matplotlib as mpl
import matplotlib.cm as cm
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas


# Our modules
import siview.prefs as prefs
import siview.util_menu as util_menu
import siview.plot_panel_siview as plot_panel_siview
import siview.image_panel_siview as image_panel_siview
import siview.default_content as default_content

import siview.constants as const

import siview.auto_gui.siview as siview_ui

import siview.common.wx_util as wx_util
import siview.common.common_dialogs as common_dialogs




#------------------------------------------------------------------------------

class TabSiview(siview_ui.SiviewUI):
    
    def __init__(self, outer_notebook, top, dataset=None, out_dicom=None):

        siview_ui.SiviewUI.__init__(self, outer_notebook)
        
        # global attributes

        self.top                = top
        self.parent             = outer_notebook
        self.dataset            = dataset
        self.out_dicom          = out_dicom     # list of DICOM files from one series

        self._prefs = prefs.PrefsMain()

        # Plot parameters
        self.dataymax       = 1.0       # used for zoom out
        self.voxel          = [0,0,0]   # x,y only, z in islice
        self.itime          = 0         # 4th dim index for top/bottom
        self.iresult        = 'Mask'
        self.fit_mode       = 'display' # 'display' only, fit 'current' voxel, or fit 'all' voxels
        self.chop_x         = 0
        self.chop_y         = 0
        
        if   self._prefs.cmap_autumn : self.cmap_results = cm.autumn
        elif self._prefs.cmap_blues  : self.cmap_results = cm.Blues
        elif self._prefs.cmap_jet    : self.cmap_results = cm.jet
        elif self._prefs.cmap_rdbu   : self.cmap_results = cm.RdBu
        elif self._prefs.cmap_gray   : self.cmap_results = cm.gray
        elif self._prefs.cmap_rdylbu : self.cmap_results = cm.RdYlBu

        self.set_image_ranges()

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

    def set_image_ranges(self):
        if self.dataset:
            self.time_range = [self.dataset.data.min(), self.dataset.data.max()]
            keys = list(self.dataset.result_maps.keys())
            self.map_ranges = {}
            for key in ['Mask','Peak', 'R1', 'R2', 'Delay1', 'Delay2', 'Base', 'Chis', 'Badfit']:
                vmax = np.nanmax(self.dataset.result_maps[key])
                vmin = np.nanmin(self.dataset.result_maps[key])
                self.map_ranges[key] = [vmin,vmax]
        else:
            self.time_range = [0,100]
            self.map_ranges = {}
            for key in ['Mask','Peak', 'R1', 'R2', 'Delay1', 'Delay2', 'Base', 'Chis', 'Badfit']:
                self.map_ranges[key] = [0,1]

        indx = self.ChoiceResults.GetSelection()
        key  = self.ChoiceResults.GetString(indx)
        self.SpinMapCeil.SetValue(self.map_ranges[key][1])
        self.SpinMapFloor.SetValue(self.map_ranges[key][0])

        

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
        dims_top    = dataset.dims
        dims_bottom = len(list(dataset.result_maps.keys()))

        t = self.dataset.time_axis 
        tmax = t[-1]
        
        # we set the max range for these guis based on the max x-axis value
        const_delay1_min   = (const.GUI_DELAY1_MIN[0],tmax)
        const_delay1_max   = (const.GUI_DELAY1_MAX[0],tmax)
        const_delay1_start = (const.GUI_DELAY1_START[0],tmax)
        const_delay2_min   = (const.GUI_DELAY2_MIN[0],tmax)
        const_delay2_max   = (const.GUI_DELAY2_MAX[0],tmax)
        const_delay2_start = (const.GUI_DELAY2_START[0],tmax)
        
        # The many controls on various tabs need configuration of 
        # their size, # of digits displayed, increment and min/max. 

        wx_util.configure_spin(self.FloatScale, 70, 4, None, (0.0001, 1000))
        self.FloatScale.multiplier = 1.1
        
        # Slider values
        self.SliderTop.SetRange(1, dims_top[-1])
        self.SliderTop.SetValue(1)

        # Settings Tab values
        vals = ['Exponential Rate Decay', 'Exponential Washin Only',] # 'Exponential Base Decay']
        self.ChoiceTimeCourseModel.Clear()        
        self.ChoiceTimeCourseModel.AppendItems( vals )

        #vals = ['Even', 'Symmetric Half-Sine', 'Asymmetric Half-Sine']
        vals = ['Even', 'Asymmetric Half-Sine']
        self.ChoiceWeightFunction.Clear()        
        self.ChoiceWeightFunction.AppendItems( vals )

        wx_util.configure_spin(self.FloatWeightScale, 60, 1, None, (0.0001, 1000))
        wx_util.configure_spin(self.SpinMapFloor,     60, min_max=(-1000,1000))
        wx_util.configure_spin(self.SpinMapCeil,      60, min_max=(-1000,1000))
        wx_util.configure_spin(self.SpinTimeFloor,    60, min_max=(-1000,1000))
        wx_util.configure_spin(self.SpinTimeCeil,     60, min_max=(-1000,1000))

        self.ButtonMapReset.SetSize(wx.Size(40,-1))
        self.ButtonTimeReset.SetSize(wx.Size(40,-1))

        wx_util.configure_spin(self.SpinPeakMin,     70, min_max=const.GUI_PEAK_MIN)    #(1,500))
        wx_util.configure_spin(self.SpinPeakStart,   70, min_max=const.GUI_PEAK_START)  #(1,500))
        wx_util.configure_spin(self.SpinPeakMax,     70, min_max=const.GUI_PEAK_MAX)    #(1,500))
        wx_util.configure_spin(self.SpinRate1Min,    70, min_max=const.GUI_RATE1_MIN)   #(0,600))        
        wx_util.configure_spin(self.SpinRate1Start,  70, min_max=const.GUI_RATE1_START) #(0,600))
        wx_util.configure_spin(self.SpinRate1Max,    70, min_max=const.GUI_RATE1_MAX)   #(0,600))
        wx_util.configure_spin(self.SpinRate2Min,    70, min_max=const.GUI_RATE2_MIN)   #(0,600))        
        wx_util.configure_spin(self.SpinRate2Start,  70, min_max=const.GUI_RATE2_START) #(0,600))
        wx_util.configure_spin(self.SpinRate2Max,    70, min_max=const.GUI_RATE2_MAX)   #(0,600))
        wx_util.configure_spin(self.SpinDelay1Min,   70, min_max=const_delay1_min)      #(-100,tmax))        
        wx_util.configure_spin(self.SpinDelay1Start, 70, min_max=const_delay1_start)    #(-100,tmax))
        wx_util.configure_spin(self.SpinDelay1Max,   70, min_max=const_delay1_max)      #(-100,tmax))
        wx_util.configure_spin(self.SpinDelay2Min,   70, min_max=const_delay2_min)      #(-100,tmax))        
        wx_util.configure_spin(self.SpinDelay2Start, 70, min_max=const_delay2_start)    #(-100,tmax))
        wx_util.configure_spin(self.SpinDelay2Max,   70, min_max=const_delay2_max)      #(-100,tmax))
        wx_util.configure_spin(self.SpinBaseMin,     70, min_max=const.GUI_BASE_MIN)    #(0,100))        
        wx_util.configure_spin(self.SpinBaseStart,   70, min_max=const.GUI_BASE_START)  #(0,100))
        wx_util.configure_spin(self.SpinBaseMax,     70, min_max=const.GUI_BASE_MAX)    #(0,100))
        
        wx_util.configure_spin(self.SpinCanvasChopX, 70, min_max=(0,10))
        wx_util.configure_spin(self.SpinCanvasChopY, 70, min_max=(0,10))

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
        
        self.hide_siview_widgets(self.dataset.time_course_model != 'Exponential Rate Decay')        


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

        self.ChoiceTimeCourseModel.SetStringSelection(self.dataset.time_course_model)
        self.ChoiceWeightFunction.SetStringSelection(self.dataset.weight_function)
        self.FloatWeightScale.SetValue(self.dataset.weight_scale)

        self.SpinMapFloor.SetValue(self.map_ranges['Mask'][0])
        self.SpinMapCeil.SetValue(self.map_ranges['Mask'][1])
        self.SpinTimeFloor.SetValue(self.time_range[0])
        self.SpinTimeCeil.SetValue(self.time_range[1])

        self.SpinPeakMin.SetValue(self.dataset.peak_min)
        self.SpinPeakStart.SetValue(self.dataset.peak_start)
        self.SpinPeakMax.SetValue(self.dataset.peak_max)
        self.SpinRate1Min.SetValue(self.dataset.rate1_min)
        self.SpinRate1Start.SetValue(self.dataset.rate1_start)
        self.SpinRate1Max.SetValue(self.dataset.rate1_max)
        self.SpinRate2Min.SetValue(self.dataset.rate2_min)
        self.SpinRate2Start.SetValue(self.dataset.rate2_start)
        self.SpinRate2Max.SetValue(self.dataset.rate2_max)
        self.SpinDelay1Min.SetValue(self.dataset.delay1_min)
        self.SpinDelay1Start.SetValue(self.dataset.delay1_start)
        self.SpinDelay1Max.SetValue(self.dataset.delay1_max)
        self.SpinDelay2Min.SetValue(self.dataset.delay2_min)
        self.SpinDelay2Start.SetValue(self.dataset.delay2_start)
        self.SpinDelay2Max.SetValue(self.dataset.delay2_max)
        self.SpinBaseMin.SetValue(self.dataset.base_min)
        self.SpinBaseStart.SetValue(self.dataset.base_start)
        self.SpinBaseMax.SetValue(self.dataset.base_max)


        #############################################################
        # Dataset View setup 
        #############################################################

        self.view = plot_panel_siview.PlotPanelSiview(  
                                        self.PanelPlot, 
                                        self,
                                        self.parent,
                                        naxes=1,
                                        zoom='box', 
                                        middle=True,
                                        do_zoom_select_event=True,
                                        do_zoom_motion_event=True,
                                        do_middle_select_event=True,
                                        do_middle_motion_event=True,
                                        do_scroll_event=True,
                                        props_zoom=dict(alpha=0.2, facecolor='yellow'),
                                        xscale_bump=0.0,
                                        yscale_bump=0.05,
                                        data=[],
                                        prefs=self._prefs,
                                        xtitle='Time [sec]'
                                     )
        
        # weird work around for Wx issue where it can't initialize and get RGBA buffer because height = 0?
        self.PanelPlot.SetSize((6,8))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.view, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.PanelPlot.SetSizer(sizer)
        self.view.Fit() 
        
        
        self.image = image_panel_siview.ImagePanelSiview(  
                                        self.PanelImage, 
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


    def on_menu_view_output(self, event):

        event_id = event.GetId()

        formats = { util_menu.ViewIds.VIEW_TO_PNG : "PNG",
                    util_menu.ViewIds.VIEW_TO_SVG : "SVG", 
                    util_menu.ViewIds.VIEW_TO_EPS : "EPS", 
                    util_menu.ViewIds.VIEW_TO_PDF : "PDF", 
                  }

        if event_id in formats:
            format = formats[event_id]
            lformat = format.lower()
            filter_ = "%s files (*.%s)|*.%s" % (format, lformat, lformat)
            figure = self.view.figure

            filename = common_dialogs.save_as("", filter_)

            if filename:
                msg = ""
                try:
                    figure.savefig( filename,
                                    dpi=300, 
                                    facecolor='w', 
                                    edgecolor='w',
                                    orientation='portrait', 
                                    papertype='letter', 
                                    format=None,
                                    transparent=False)
                except IOError:
                    msg = """I can't write the file "%s".""" % filename
                
                if msg:
                    common_dialogs.message(msg, style=common_dialogs.E_OK)

        outype2 = { util_menu.ViewIds.MASK_TO_MOSAIC : "mask",
                    util_menu.ViewIds.FITS_TO_MOSAIC : "fits", 
                  }

        if event_id in outype2:
            from matplotlib import pyplot as plt
            
            self.top.statusbar.SetStatusText((" Outputting to Mosaic ..."), 1)
            
            outype = outype2[event_id]
            if outype == 'mask':
                labels = ['Mask']
            elif outype == 'fits':
                labels = ['Peak', 'R1', 'R2', 'Delay1', 'Delay2', 'Base', 'Chis', ]
            datas = []
            for key in labels:
                datas.append(self.dataset.result_maps[key])

            filetypes, exts, filter_index = self.image.canvas._get_imagesave_wildcards()
            default_file = self.image.canvas.get_default_filename()
            dlg = wx.FileDialog(self, "Save to file", "", default_file,
                                filetypes, wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
            dlg.SetFilterIndex(filter_index)
            if dlg.ShowModal() == wx.ID_OK:
                dirname  = dlg.GetDirectory()
                filename = dlg.GetFilename()
                formt = exts[dlg.GetFilterIndex()]
                basename, ext = os.path.splitext(filename)
                if ext.startswith('.'):
                    ext = ext[1:]
                if ext in ('svg', 'pdf', 'ps', 'eps', 'png') and formt!=ext:
                    #looks like they forgot to set the image type drop
                    #down, going with the extension.
                    warnings.warn('extension %s did not match the selected image type %s; going with %s'%(ext, formt, ext), stacklevel=0)
                    formt = ext

                for data,label in zip(datas, labels):
                    nslc = data.shape[-1] 
                    ncol = 4
                    nrow = int(nslc / ncol) 
                    if nslc % ncol:
                        nrow += 1
                    
                    dpi  = 100
                    
                    dim0 = data[0].shape[0]
                    dim1 = data[0].shape[1]
    
                    xstr  = self.chop_x
                    ystr  = self.chop_y
                    xend  = dim0 - xstr
                    yend  = dim1 - ystr
    
                    xsize = dim0 - self.chop_x*2
                    ysize = dim1 - self.chop_y*2

                    xsiz = float(xsize * ncol) / float(dpi)
                    ysiz = float(ysize * nrow) / float(dpi)
    
                    figure = plt.figure(dpi=dpi,figsize=(xsiz,ysiz))  
                    
                    naxes  = nslc  
                    axes   = []
                    for i in range(naxes):
                        axes.append(figure.add_subplot(nrow,ncol,i+1))
     
                    for axis in axes:
                        axis.xaxis.set_visible(False)
                        axis.yaxis.set_visible(False)
                     
                    figure.subplots_adjust( left=0,right=1, bottom=0,top=1, wspace=0.0,hspace=0.0)
                     
                    if outype == 'mask' or (data.min() == data.max() == 0):
                        vmin = 0.0
                        vmax = 1.0
                    else:                    
                        vmin = np.nanmin(data[data != 0])
                        vmax = np.nanmax(data[data != 0])
                    cmap = self.cmap_results
    
                    for i in range(nslc):
                        im = data[ystr:yend,xstr:xend,i]
                        if label == 'Delay1':
                            # lower values outside mask to min value for clearer images
                            msk = datas[0][ystr:yend,xstr:xend,i]
                            im = im.copy()
                            im[msk<=0] = vmin
                        axes[i].imshow(im, cmap=cmap, vmax=vmax, vmin=vmin, aspect='equal', origin='upper') 
                    
                    try:
                        filename = basename+'_'+label+'.'+ext
                        plt.savefig(os.path.join(dirname, filename), dpi=dpi, bbox_inches='tight', pad_inches=0)
                        plt.close()
                    except Exception as e:
                        plt.close()
                        dialog = wx.MessageDialog(parent  = self,
                                                  message = str(e),
                                                  caption = 'Matplotlib backend_wx error',
                                                  style=wx.OK | wx.CENTRE)
                        dialog.ShowModal()
                        dialog.Destroy()
            self.top.statusbar.SetStatusText((" "), 1)

        outype3 = { util_menu.ViewIds.MASK_TO_STRIP : "mask",
                    util_menu.ViewIds.FITS_TO_STRIP : "fits", 
                  }

        if event_id in outype3:
            from matplotlib import pyplot as plt
            
            self.top.statusbar.SetStatusText((" Outputting to Strip ..."), 1)
            
            outype = outype3[event_id]
            if outype == 'mask':
                labels = ['Mask']
            elif outype == 'fits':
                labels = ['Peak', 'R1', 'R2', 'Delay1', 'Delay2', 'Base', 'Chis', 'Badfit']
            datas = []
            for key in labels:
                datas.append(self.dataset.result_maps[key])

            filetypes, exts, filter_index = self.image.canvas._get_imagesave_wildcards()
            default_file = self.image.canvas.get_default_filename()
            dlg = wx.FileDialog(self, "Save to file", "", default_file,
                                filetypes, wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
            dlg.SetFilterIndex(filter_index)
            if dlg.ShowModal() == wx.ID_OK:
                dirname  = dlg.GetDirectory()
                filename = dlg.GetFilename()
                formt    = exts[dlg.GetFilterIndex()]
                basename, ext = os.path.splitext(filename)
                if ext.startswith('.'):
                    ext = ext[1:]
                if ext in ('svg', 'pdf', 'ps', 'eps', 'png') and formt!=ext:
                    #looks like they forgot to set the image type drop
                    #down, going with the extension.
                    warnings.warn('extension %s did not match the selected image type %s; going with %s'%(ext, formt, ext), stacklevel=0)
                    formt = ext

                if outype == 'mask':
                    filename = basename+'_mask_strips.'+ext
                if outype == 'fits':
                    filename = basename+'_fits_strips.'+ext
                    
                data = datas
                nrow = len(datas)
                ncol = data[0].shape[-1]    
                dpi  = 100
                
                dim0 = data[0].shape[0]
                dim1 = data[0].shape[1]

                xstr  = self.chop_x
                ystr  = self.chop_y
                xend  = dim0 - xstr
                yend  = dim1 - ystr

                xsize = dim0 - self.chop_x*2
                ysize = dim1 - self.chop_y*2

                xsiz = float(xsize * ncol) / float(dpi)
                ysiz = float(ysize * nrow) / float(dpi)

                figure = plt.figure(dpi=dpi,figsize=(xsiz,ysiz))  
                
                axes = []
                for j in range(nrow):
                    for i in range(ncol):
                        axes.append(figure.add_subplot(nrow,ncol,ncol*j+i+1))
 
                for axis in axes:
                    axis.xaxis.set_visible(False)
                    axis.yaxis.set_visible(False)                    
                
                figure.subplots_adjust( left=0,right=1, bottom=0,top=1, wspace=0.0,hspace=0.0 )
                 
                cmap = self.cmap_results 

                for j in range(nrow):
                    
                    if outype == 'mask' or (data[j].min() == data[j].max() == 0):
                        vmin = 0.0
                        vmax = 1.0
                    else:                    
                        vmin = np.nanmin(data[j])
                        vmax = np.nanmax(data[j]) 
                    
                    for i in range(ncol):
                        im = data[j][ystr:yend,xstr:xend,i]
                        if labels[j] == 'Delay1':
                            # lower values outside mask to min value for clearer images
                            msk = datas[0][ystr:yend,xstr:xend,i]
                            im = im.copy()
                            im[msk<=0] = vmin
                        axes[j*ncol+i].imshow(im, cmap=cmap, vmax=vmax, vmin=vmin, aspect='equal', origin='upper') 
                
                try:
                    plt.savefig(os.path.join(dirname, filename), dpi=dpi, bbox_inches='tight', pad_inches=0)
                    plt.close()
                except Exception as e:
                    plt.close()
                    dialog = wx.MessageDialog(parent  = self,
                                              message = str(e),
                                              caption = 'Matplotlib backend_wx error',
                                              style=wx.OK | wx.CENTRE)
                    dialog.ShowModal()
                    dialog.Destroy() 

        outype4 = { util_menu.ViewIds.MRI_TO_VSTRIP : "vert",
                    util_menu.ViewIds.MRI_TO_HSTRIP : "horiz", 
                  }

        if event_id in outype4:
            from matplotlib import pyplot as plt
            
            self.top.statusbar.SetStatusText((" Outputting MRIs to Strip ..."), 1)
            
            filetypes, exts, filter_index = self.image.canvas._get_imagesave_wildcards()
            default_file = self.image.canvas.get_default_filename()
            dlg = wx.FileDialog(self, "Save to file", "", default_file,
                                filetypes, wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
            dlg.SetFilterIndex(filter_index)
            if dlg.ShowModal() == wx.ID_OK:
                dirname  = dlg.GetDirectory()
                filename = dlg.GetFilename()
                formt    = exts[dlg.GetFilterIndex()]
                basename, ext = os.path.splitext(filename)
                if ext.startswith('.'):
                    ext = ext[1:]
                if ext in ('svg', 'pdf', 'ps', 'eps', 'png') and formt!=ext:
                    #looks like they forgot to set the image type drop
                    #down, going with the extension.
                    warnings.warn('extension %s did not match the selected image type %s; going with %s'%(ext, formt, ext), stacklevel=0)
                    formt = ext

                outype = outype4[event_id]

                data = self.dataset.data
                dims = list(data.shape)
                vmin = np.nanmin(data)
                vmax = np.nanmax(data) 

                if outype == 'vert':
                    filename = basename+'_mri_slices_vertical.'+ext
                    label = "MRI Strip Slices Vertical"
                    nrow = dims[3]      # time
                    ncol = dims[2]      # slice
                
                elif outype == 'horiz':
                    filename = basename+'_mri_slices_horizontal.'+ext
                    label = "MRI Strip Slices Horizontal"
                    nrow = dims[2]      # slice
                    ncol = dims[3]      # time

                dpi   = 100
                xstr  = self.chop_x
                ystr  = self.chop_y
                xend  = dims[0] - xstr
                yend  = dims[1] - ystr
                cmap  = cm.gray
                xsize = data.shape[0] - (2*xstr)
                ysize = data.shape[1] - (2*ystr)
                xsiz  = float(xsize * ncol) / float(dpi)
                ysiz  = float(ysize * nrow) / float(dpi)

                figure = plt.figure(dpi=dpi,figsize=(xsiz,ysiz))  
                
                axes = []
                for j in range(nrow):
                    for i in range(ncol):
                        axes.append(figure.add_subplot(nrow,ncol,ncol*j+i+1))
 
                for axis in axes:
                    axis.xaxis.set_visible(False)
                    axis.yaxis.set_visible(False)                    
                
                figure.subplots_adjust( left=0,right=1, bottom=0,top=1, wspace=0.0,hspace=0.0 )
                 
                for j in range(nrow):
                    for i in range(ncol):
                        if outype == 'vert':
                            im = data[ystr:yend,xstr:xend,i,j]
                        elif outype == 'horiz':
                            im = data[ystr:yend,xstr:xend,j,i]
                        axes[j*ncol+i].imshow(im, cmap=cmap, 
                                                  vmax=vmax, 
                                                  vmin=vmin, 
                                                  aspect='equal', 
                                                  origin='upper') 
                
                try:
                    plt.savefig(os.path.join(dirname, filename), dpi=dpi, bbox_inches='tight', pad_inches=0)
                    plt.close()
                except Exception as e:
                    plt.close()
                    dialog = wx.MessageDialog(parent  = self,
                                              message = str(e),
                                              caption = 'Matplotlib backend_wx error',
                                              style=wx.OK | wx.CENTRE)
                    dialog.ShowModal()
                    dialog.Destroy() 

            
            self.top.statusbar.SetStatusText((" "), 1)              

    def on_menu_output_by_slice(self, event):
        """
        Output values from the fitting results array into a CSV based text
        file. 
        
        This method organizes the output serially by voxel value. We loop
        through x,y,z value (x changing fastest) and write a result to the 
        text array if the mask value is non-zero. All fitting values are
        written to the same voxel line as are the mask and image value.
        
        """
        patid = self.dataset.patient_id
        sdesc = self.dataset.series_description
        path  = self.dataset.output_path
        default_fbase = os.path.join(path, patid+'_'+sdesc)
            
        filename_left  = default_fbase+'_Left_Masked_XYZV.csv'
        filename_right = default_fbase+'_Right_Masked_XYZV.csv'
        
        lines_left, lines_right = self.dataset.get_output_text_by_slice()
        
        lines_left = "\n".join(lines_left)
        lines_left = lines_left.encode("utf-8")
        if (wx.Platform == "__WXMSW__"):
            lines_left = lines_left.replace(b"\n", b"\r\n")
        open(filename_left, "wb").write(lines_left)
        
        lines_right = "\n".join(lines_right)
        lines_right = lines_right.encode("utf-8")
        if (wx.Platform == "__WXMSW__"):
            lines_right = lines_right.replace(b"\n", b"\r\n")
        open(filename_right, "wb").write(lines_right)

        #else:
            # User clicked cancel on the "save as" dialog
                    

    def on_menu_output_by_voxel(self, event):
        """
        Output values from the fitting results array into a CSV based text
        file. 
        
        This method organizes the output serially by voxel value. We loop
        through x,y,z value (x changing fastest) and write a result to the 
        text array if the mask value is non-zero. All fitting values are
        written to the same voxel line as are the mask and image value.
        
        """
        default_fname = "siview_output_as_csv2_by_voxel"
        filetype_filter = "CSV (*.csv)|*.csv"
        
        filename = common_dialogs.save_as(filetype_filter=filetype_filter,
                                          default_filename=default_fname)
        if filename:
            
            lines = self.dataset.get_output_text_by_voxel()
                       
            lines = "\n".join(lines)
            lines = lines.encode("utf-8")
            if (wx.Platform == "__WXMSW__"):
                lines = lines.replace(b"\n", b"\r\n")
            open(filename, "wb").write(lines)

        #else:
            # User clicked cancel on the "save as" dialog



    def on_menu_output_to_dicom(self, event): 

        try:
            self.dataset.do_results_output_dicom()
        except Exception as e:
            msg_title = "SIView - Output Results to DICOM"
            msg = "Error(mri_dataset::do_results_output_dicom): Can not get default DICOM headers for output. Returning \n%s" % str(e)
            r = common_dialogs.message(msg, msg_title, common_dialogs.X_OK)
            return
            

    def set_mask(self, mask):
        dims =  self.dataset.result_maps['Mask'].shape
        msg = ''
        if mask.shape != dims:
            msg = 'New mask is different shape than Image1 spatial dims.'

        if msg:
            common_dialogs.message(msg, default_content.APP_NAME+" - New Mask", common_dialogs.E_OK)
        else:
            self.dataset.result_maps['Mask'] = mask
            self.show()
            

    ########## Widget Event Handlers ####################    
    
    def on_scale(self, event):
        view = self.view
        scale = self.FloatScale.GetValue()
        if scale > view.vertical_scale:
            view.set_vertical_scale(1.0, scale_mult=1.1)
        else:
            view.set_vertical_scale(-1.0, scale_mult=1.1)
        self.FloatScale.SetValue(view.vertical_scale)


    def on_slider_changed_top(self, event):
        # Top slider changed. Here we allow the control to update itself.
        # If we don't, then there can be a noticeable & confusing pause 
        # between interacting with the control and seeing it actually change.
        wx.CallAfter(self._slider_changed_top)

    def _slider_changed_top(self):
        tmp  = self.SliderTop.GetValue() - 1
        dims = self.dataset.dims
        tmp  = max(0, min(dims[3]-1, tmp))      # clip to range
        self.itime = tmp
        self.show()


    def on_results(self, event):
        # Results choice changed. Here we allow the control to update itself.
        # If we don't, then there can be a noticeable & confusing pause 
        # between interacting with the control and seeing it actually change.
        wx.CallAfter(self._slider_changed_bottom)

    def _slider_changed_bottom(self):
        indx = self.ChoiceResults.GetSelection()
        key  = self.ChoiceResults.GetString(indx)
        self.iresult = key
        self.SpinMapCeil.SetValue(self.map_ranges[key][1])
        self.SpinMapFloor.SetValue(self.map_ranges[key][0])
        self.show()

    def on_map_range(self, event):
        indx = self.ChoiceResults.GetSelection()
        key  = self.ChoiceResults.GetString(indx)
        ceil_val  = self.SpinMapCeil.GetValue()
        floor_val = self.SpinMapFloor.GetValue()
        self.map_ranges[key] = (floor_val, ceil_val)
        self.show()

    def on_map_reset(self, event):
        indx = self.ChoiceResults.GetSelection()
        key  = self.ChoiceResults.GetString(indx)
        dat  = self.dataset.result_maps[key][:,:,:]
        ceil_val  = np.nanmax(dat)
        floor_val = np.nanmin(dat)
        self.map_ranges[key] = [floor_val, ceil_val]
        self.SpinMapCeil.SetValue(ceil_val)
        self.SpinMapFloor.SetValue(floor_val)
        self.show()
        
    def on_time_range(self, event):
        ceil_val  = self.SpinTimeCeil.GetValue()
        floor_val = self.SpinTimeFloor.GetValue()
        self.time_range = [floor_val, ceil_val]
        self.show()

    def on_time_reset(self, event):
        dat = self.dataset.data
        ceil_val  = self.dataset.data.max()
        floor_val = self.dataset.data.min()
        self.time_range = [floor_val, ceil_val]
        self.SpinTimeCeil.SetValue(ceil_val)
        self.SpinTimeFloor.SetValue(floor_val)
        self.show()

    def on_time_course_model(self, event):
        indx = self.ChoiceTimeCourseModel.GetSelection()
        key  = self.ChoiceTimeCourseModel.GetString(indx)
        self.dataset.time_course_model = key
        self.dataset.assign_functions()
        if self.dataset.time_course_model == "Exponential Rate Decay":
            self.hide_siview_widgets(False)
        elif self.dataset.time_course_model == "Exponential Washin Only":
            self.hide_siview_widgets(True)
        
    def on_weight_function(self, event):
        indx = self.ChoiceWeightFunction.GetSelection()
        key  = self.ChoiceWeightFunction.GetString(indx)
        self.dataset.weight_function = key

    def on_weight_scale(self, event):
        val = self.FloatWeightScale.GetValue() 
        self.dataset.weight_scale = val

    def on_peak_min(self, event):
        self.check_limits()

    def on_peak_start(self, event):
        self.check_limits()

    def on_peak_max(self, event):
        self.check_limits()

    def on_delay1_min(self, event):
        self.check_limits()

    def on_delay1_start(self, event):
        self.check_limits()

    def on_delay1_max(self, event):
        self.check_limits()

    def on_delay2_min(self, event):
        self.check_limits()

    def on_delay2_start(self, event):
        self.check_limits()

    def on_delay2_max(self, event):
        self.check_limits()

    def on_rate1_min(self, event):
        self.check_limits()

    def on_rate1_start(self, event):
        self.check_limits()

    def on_rate1_max(self, event):
        self.check_limits()

    def on_rate2_min(self, event):
        self.check_limits()

    def on_rate2_start(self, event):
        self.check_limits()

    def on_rate2_max(self, event):
        self.check_limits()

    def on_base_min(self, event):
        self.check_limits()

    def on_base_start(self, event):
        self.check_limits()

    def on_base_max(self, event):
        self.check_limits()

    def on_reset_mask(self, event):
        #self.dataset.reset_mask()
        self.dataset.make_mask()

    def on_fit_all(self, event):
        self.top.statusbar.SetStatusText((" Fitting All Voxels "), 1)
        self.fit_mode = 'all'
        self.process()
        self.set_image_ranges()
        self.plot()
        self.top.statusbar.SetStatusText((" "), 1)
        self.show()

    def on_fit_slice(self, event):
        self.fit_mode = 'slice'
        self.process()
        self.set_image_ranges()
        self.plot()
        self.show()

    def on_fit_current(self, event):
        self.fit_mode = 'current'
        self.process()
        self.set_image_ranges()
        self.plot()
        self.show()

    def on_chop(self, event):
        self.chop_x = self.SpinCanvasChopX.GetValue()
        self.chop_y = self.SpinCanvasChopY.GetValue()
        self.show()


    def hide_siview_widgets(self, flag=False):
        
        if flag:
            self.LabelDelay2.Disable()
            self.SpinDelay2Min.Disable()
            self.SpinDelay2Start.Disable()
            self.SpinDelay2Max.Disable()
            self.LabelRate2.Disable()
            self.SpinRate2Min.Disable()
            self.SpinRate2Start.Disable()
            self.SpinRate2Max.Disable()
        else:
            self.LabelDelay2.Enable()
            self.SpinDelay2Min.Enable()
            self.SpinDelay2Start.Enable()
            self.SpinDelay2Max.Enable()
            self.LabelRate2.Enable()
            self.SpinRate2Min.Enable()
            self.SpinRate2Start.Enable()
            self.SpinRate2Max.Enable()
    
    ##### Internal helper functions  ##########################################
    
    def check_limits(self):
        
        ids = [(self.SpinPeakMin,self.SpinPeakStart,self.SpinPeakMax),
               (self.SpinDelay1Min,self.SpinDelay1Start,self.SpinDelay1Max),
               (self.SpinDelay2Min,self.SpinDelay2Start,self.SpinDelay2Max),
               (self.SpinRate1Min,self.SpinRate1Start,self.SpinRate1Max),
               (self.SpinRate2Min,self.SpinRate2Start,self.SpinRate2Max),
               (self.SpinBaseMin,self.SpinBaseStart,self.SpinBaseMax),]
        
        for id in ids:
            vals = [id[0].GetValue(),id[1].GetValue(),id[2].GetValue()]
            vsort = sorted(vals)
            id[0].SetValue(vsort[0])
            id[1].SetValue(vsort[1])
            id[2].SetValue(vsort[2]) 
            
        self.dataset.peak_min     = self.SpinPeakMin.GetValue()
        self.dataset.peak_start   = self.SpinPeakStart.GetValue()
        self.dataset.peak_max     = self.SpinPeakMax.GetValue()
        self.dataset.rate1_min    = self.SpinRate1Min.GetValue()
        self.dataset.rate1_start  = self.SpinRate1Start.GetValue()
        self.dataset.rate1_max    = self.SpinRate1Max.GetValue()
        self.dataset.rate2_min    = self.SpinRate2Min.GetValue()
        self.dataset.rate2_start  = self.SpinRate2Start.GetValue()
        self.dataset.rate2_max    = self.SpinRate2Max.GetValue()
        self.dataset.delay1_min   = self.SpinDelay1Min.GetValue()
        self.dataset.delay1_start = self.SpinDelay1Start.GetValue()
        self.dataset.delay1_max   = self.SpinDelay1Max.GetValue()
        self.dataset.delay2_min   = self.SpinDelay2Min.GetValue()
        self.dataset.delay2_start = self.SpinDelay2Start.GetValue()
        self.dataset.delay2_max   = self.SpinDelay2Max.GetValue()
        self.dataset.base_min     = self.SpinBaseMin.GetValue()
        self.dataset.base_start   = self.SpinBaseStart.GetValue()
        self.dataset.base_max     = self.SpinBaseMax.GetValue()


    def chain_status(self, msg, slot=1):
        self.top.statusbar.SetStatusText((msg), slot)


    def process_and_display(self, initialize=False):
        
        self.process()
        self.plot(initialize=initialize)
        self.show(keep_norm=not initialize)


    def process(self):
        """ 
        Converts spectral (metabolite, macromolecule and noise) signals from 
        ideal time basis functions to spectral domain peaks by applying a line
        shape envelope, scaling and phasing and then applying the FFT.
        
        """
        if self.fit_mode == 'display':
            self.plot_results = self.dataset.get_fit_plot(self.voxel)
        elif self.fit_mode == 'current':
            voxel = [self.voxel]
            entry = 'one'
            self.plot_results = self.dataset.chain.run(voxel, entry=entry, status=self.chain_status)
        elif self.fit_mode == 'slice':
            voxel = self.dataset.get_all_voxels_by_slice(self.voxel[2])  # list of tuples, with mask != 0
            entry = 'slice'
            self.plot_results = self.dataset.chain.run(voxel, entry=entry, status=self.chain_status)
        elif self.fit_mode == 'all':
            voxel = self.dataset.get_all_voxels()  # list of tuples, with mask != 0
            entry = 'all'
            self.plot_results = self.dataset.chain.run(voxel, entry=entry, status=self.chain_status)
        self.fit_mode = 'display'
            
                        
    def plot(self, is_replot=False, initialize=False):

        if not self.plotting_enabled: 
            return
        
        if self.dataset == None:
            return
        
        voxel = self.voxel
        
        t = self.dataset.time_axis #/ 60.0  # time in sec
        
        line1 = self.dataset.data[voxel[1],voxel[0],voxel[2],:]
        data1 = {'data' : line1, 
                 'xaxis_values' : t,
                 'line_color_real' : 'black'
                }

        data2 = {'data' : self.plot_results, 
                 'xaxis_values' : t,
                 'line_color_real' : 'green'
                }

        data3 = {'data' : line1-self.plot_results, 
                 'xaxis_values' : t,
                 'line_color_real' : 'black'
                }
        
        data =  [[data1, data2, data3]] 

        self.view.set_data(data)
        self.view.update(no_draw=True)
        self.view.canvas.draw()


    def show(self, keep_norm=True):

        if not self.plotting_enabled: 
            return
        
        if self.dataset == None:
            return
    
        voxel = self.voxel
        
        dat1 = self.dataset.data[:,:, voxel[2], self.itime]
        dat2 = self.dataset.result_maps[self.iresult][:,:, voxel[2]]
        dat2mm = self.dataset.result_maps[self.iresult][:,:,:]

#         # we want to refer to time rates in sec and 1/sec so we multiply by 60 
#         # here as data was fitted with time set as minutes for the model's sake
#         if (self.iresult in ['R1','R2','Delay1','Delay2']):
#             dat2 = dat2.copy() * 60
#             dat2mm = dat2mm.copy() * 60

        data1 =  [{'data'      : dat1,
                   'cmap'      : cm.gray,
                   'alpha'     : 1.0,
#                   'vmax'      : self.dataset.data.max(),
#                   'vmin'      : self.dataset.data.min(),
                   'vmax'      : self.time_range[1],
                   'vmin'      : self.time_range[0],
                   'keep_norm' : False         }] 

        data2 =  [{'data'      : dat2,
                   'cmap'      : self.cmap_results,
                   'alpha'     : 1.0,
#                   'vmax'      : np.nanmax(dat2mm),     # ignores NaN values
#                   'vmin'      : np.nanmin(dat2mm),
                   'vmax'      : self.map_ranges[self.iresult][1],     # ignores NaN values
                   'vmin'      : self.map_ranges[self.iresult][0],
                   'keep_norm' : False          }] 

        data = [data1,data2]
        self.image.set_data(data, keep_norm=keep_norm)
        self.image.update(no_draw=True, keep_norm=keep_norm)
        self.image.canvas.draw()


        
            
