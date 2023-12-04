#!/usr/bin/env python

# Copyright (c) 2014-2022 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.

# NOTE NOTE NOTE - bjs - deprecated for SIView
# This was the first attempt to add an 'MRI pane' to the spectral plot notebook
# for displaying MRI and calculated images like 'integral across the ref lines'
# to facilitate moving around the spatial voxels of the MRSI.  It had issues.
# Mainly, ImagePaneUI is created in wxglade, but it needed to add a ImagePanelMri
# to a blank panel to show the images. The events from the ImagePanelMri nav
# toolbar ought to be handled at the ImageControlPane level since it has access
# to the TabSpectral and Dataset refs. However, I could not figure out a slick
# way to inherently do this without a hack like:
# self.image.on_scroll = self.on_scroll
# So, instead I created ImagePaneMri object (image_pane_mri.py in analysis dir)
# where I directly create the Figure/Canvas/Axes in that object. Thus the events
# can be controlled at that level.  No import of another module either (other
# than the nav toolbar).


# Python modules

# 3rd party modules
import wx
import matplotlib.cm as cm

# Our modules
from siview.analysis.auto_gui.image_pane import ImagePaneUI
from siview.common.wx_gravy.image_panel_mri import ImagePanelMri


class ImageControlPanel(ImagePaneUI):
    
    def __init__(self, parent, tab, tab_dataset, **kwargs):

        self.statusbar = tab.top.statusbar
        
        ImagePaneUI.__init__( self, parent, **kwargs )

        # tab is the containing widget for this plot_panel, it is used
        # in resize events, the tab attribute is the AUI Notebook tab
        # that contains this plot_panel

        self.tab = tab
        self.top = wx.GetApp().GetTopWindow()
        self.tab_dataset = tab_dataset

        self.image = ImagePanelMri(self,
                                   naxes=2,
                                   data=[],
                                   cmap=cm.gray,
                                   vertOn=True,
                                   horizOn=True,
                                   layout='horizontal',
                                  )
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.image, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.PanelImagePlot.SetSizer(sizer)
        self.image.Fit()

        self.last_x = 0
        self.last_y = 0

        # # de-reference ImagePanelMri events to methods in this object
        # self.image.on_scroll = self.on_scroll
        # self.image.on_motion = self.on_motion
        # self.image.on_select = self.on_select
        # self.image.on_panzoom_release = self.on_panzoom_release
        # self.image.on_panzoom_motion = self.on_panzoom_motion
        # self.image.on_level_press = self.on_level_press
        # self.image.on_level_release = self.on_level_release
        # self.image.on_level_motion = self.on_level_motion


    # EVENT FUNCTIONS -----------------------------------------------

    def on_splitter(self, event):
        self.tab.on_splitter(event)

    def on_scroll(self, button, step, iplot):
        xvox, yvox, zvox = self.tab_dataset.voxel
        step = 1 if step > 0 else -1
        dims = self.tab.dataset.spectral_dims
        tmp = self.tab_dataset.voxel[2] + step
        tmp = tmp if tmp > 0 else 0
        tmp = tmp if tmp < dims[2] - 1 else dims[2] - 1
        self.tab_dataset.voxel[2] = tmp
        zvox = tmp
        # self.tab.process()
        # self.tab.plot()
        # self.tab.show()
        # self.top.statusbar.SetStatusText( " Cursor X,Y,Slc=%i,%i,%i" % (xvox,yvox,zvox), 0)
        # self.top.statusbar.SetStatusText( " Plot X,Y,Slc=%i,%i,%i"   % (xvox,yvox,zvox), 3)

    def on_motion(self, xloc, yloc, xpos, ypos, iplot):
        value = self.image.data[iplot][0]['data'][int(round(xloc))][int(round(yloc))]
        self.top.statusbar.SetStatusText(" Value = %s" % (str(value),), 0)
        self.top.statusbar.SetStatusText(" X,Y = %i,%i" % (int(round(xloc)), int(round(yloc))), 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" ", 3)

    def on_select(self, xloc, yloc, xpos, ypos, iplot):
        xloc = int(round(xloc))
        yloc = int(round(yloc))
        if xloc == self.last_x and yloc == self.last_y:  # minimize event calls
            return
        self.tab_dataset.SpinX.SetValue(xloc + 1)
        self.tab_dataset.SpinY.SetValue(yloc + 1)
        self.last_x = xloc
        self.last_y = yloc
        self.tab_dataset.on_voxel_change()

    def on_panzoom_release(self, xloc, yloc, xpos, ypos):
        xvox, yvox, zvox = self.tab_dataset.voxel
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" ", 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" Plot X,Y,Slc=%i,%i,%i" % (xvox, yvox, zvox), 3)

    def on_panzoom_motion(self, xloc, yloc, xpos, ypos, iplot):
        axes = self.image.axes[iplot]
        xmin, xmax = axes.get_xlim()
        ymax, ymin = axes.get_ylim()  # max/min flipped here because of y orient top/bottom
        xdelt, ydelt = xmax - xmin, ymax - ymin

        self.top.statusbar.SetStatusText((" X-range = %.1f to %.1f" % (xmin, xmax)), 0)
        self.top.statusbar.SetStatusText((" Y-range = %.1f to %.1f" % (ymin, ymax)), 1)
        self.top.statusbar.SetStatusText((" delta X,Y = %.1f,%.1f " % (xdelt, ydelt)), 2)
        self.top.statusbar.SetStatusText((" Area = %i " % (xdelt * ydelt,)), 3)

    def on_level_release(self, xloc, yloc, xpos, ypos):
        xvox, yvox, zvox = self.tab_dataset.voxel
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" ", 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" Plot X,Y,Slc=%i,%i,%i" % (xvox, yvox, zvox), 3)

    def on_level_press(self, xloc, yloc, xpos, ypos, iplot):
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" ", 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" ", 3)

    def on_level_motion(self, xloc, yloc, xpos, ypos, iplot, wid, lev):
        xvox, yvox, zvox = self.tab_dataset.voxel
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" Width = %i " % (self.image.width[iplot],), 1)
        self.top.statusbar.SetStatusText(" Level = %i " % (self.image.level[iplot],), 2)
        self.top.statusbar.SetStatusText(" Plot X,Y,Slc=%i,%i,%i" % (xvox, yvox, zvox), 3)

    # Image Stack events ---------------------------------------

    def on_source_stack1(self, event):
        # We allow control to update itself to avoid a noticeable & confusing
        # pause between clicking the control and seeing it actually change.
        wx.CallAfter(self._source_stack1_changed)

    def _source_stack1_changed(self):
        key = self.ComboSourceStack1.GetStringSelection()
        if key == self.tab.stack1_select: return
        self.tab.stack1_select = key
        d = self.tab.stack_sources[key]
        self.FloatStackCeil1.SetValue(d['ceil'])
        self.FloatStackFloor1.SetValue(d['floor'])
        self.tab.process_image()
        self.tab.show()

    def on_source_stack2(self, event):
        wx.CallAfter(self._source_stack2_changed)

    def _source_stack2_changed(self):
        key = self.ComboSourceStack2.GetStringSelection()
        if key == self.tab.stack2_select: return
        self.tab.stack2_select = key
        d = self.tab.stack_sources[key]
        self.FloatStackCeil2.SetValue(d['ceil'])
        self.FloatStackFloor2.SetValue(d['floor'])
        self.tab.process_image()
        self.tab.show()

    def on_slice_index1(self, event):
        wx.CallAfter(self._slice_index_changed1)

    def _slice_index_changed1(self):
        tmp = self.SpinSliceIndex1.GetValue() - 1
        dims = self.tab.stack_sources[self.tab.stack1_select]['data'].shape
        tmp = max(0, min(dims[3] - 1, tmp))  # clip to range
        self.SpinSliceIndex1.SetValue(tmp)
        self.tab.stack_sources[self.tab.stack1_select]['slice'] = tmp
        self.tab.process_image()
        self.tab.show()

    def on_slice_index2(self, event):
        wx.CallAfter(self._slice_index_changed2)

    def _slice_index_changed2(self):
        tmp = self.SpinSliceIndex2.GetValue() - 1
        dims = self.tab.stack_sources[self.tab.stack2_select]['data'].shape
        tmp = max(0, min(dims[3] - 1, tmp))  # clip to range
        self.SpinSliceIndex2.SetValue(tmp)
        self.tab.stack_sources[self.tab.stack1_select]['slice'] = tmp
        self.tab.process_image()
        self.tab.show()

    def on_stack_range1(self, event):
        ceil_val = self.FloatStackCeil1.GetValue()
        floor_val = self.FloatStackFloor1.GetValue()
        tmp = [floor_val, ceil_val] if floor_val < ceil_val else [ceil_val, floor_val]
        self.FloatStackCeil1.SetValue(tmp[0])
        self.FloatStackFloor1.SetValue(tmp[1])
        d = self.tab.stack_sources[self.tab.stack1_select]
        d['floor'] = tmp[0]
        d['ceil'] = tmp[1]
        self.process_image()
        self.show()

    def on_stack_range2(self, event):
        ceil_val = self.FloatStackCeil2.GetValue()
        floor_val = self.FloatStackFloor2.GetValue()
        tmp = [floor_val, ceil_val] if floor_val < ceil_val else [ceil_val, floor_val]
        self.FloatStackCeil2.SetValue(tmp[0])
        self.FloatStackFloor2.SetValue(tmp[1])
        d = self.tab.stack_sources[self.tab.stack2_select]
        d['floor'] = tmp[0]
        d['ceil'] = tmp[1]
        self.tab.process_image()
        self.tab.show()


    def on_stack_reset1(self, event):
        d = self.tab.stack_sources[self.tab.stack1_select]
        d['floor'] = np.nanmin(d['data'])
        d['ceil'] = np.nanmax(d['data'])
        self.FloatStackFloor1.SetValue(d['floor'])
        self.FloatStackCeil1.SetValue(d['ceil'])
        self.tab.process_image()
        self.tab.show()

    def on_stack_reset2(self, event):
        d = self.tab.stack_sources[self.tab.stack2_select]
        d['floor'] = np.nanmin(d['data'])
        d['ceil'] = np.nanmax(d['data'])
        self.FloatStackFloor2.SetValue(d['floor'])
        self.FloatStackCeil2.SetValue(d['ceil'])
        self.tab.process_image()
        self.tab.show()

    # def on_source_stack1(self, event):
    #     self.tab.on_source_stack1(event)
    #
    # def on_source_stack2(self, event):
    #     self.tab.on_source_stack2(event)
    #
    # def on_slice_index1(self, event):
    #     self.tab.on_slice_index1(event)
    #
    # def on_slice_index2(self, event):
    #     self.tab.on_slice_index2(event)
    #
    # def on_calc_range1(self, event):
    #     self.tab.on_calc_range1(event)
    #
    # def on_calc_range2(self, event):
    #     self.tab.on_calc_range2(event)
    #
    # def on_calc_reset1(self, event):
    #     self.tab.on_calc_reset1(event)
    #
    # def on_calc_reset2(self, event):
    #     self.tab.on_calc_reset2(event)
        
    
    def on_calc_reset2(self, event):
        self.tab.on_calc_reset2(event)


