#!/usr/bin/env python

# Copyright (c) 2014-2022 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


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

#        self.image = ImagePanelMri(self.PanelImagePlot,
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

    def on_source_stack1(self, event):  
        self.tab.on_source_stack1(event)
        
    def on_source_stack2(self, event):
        self.tab.on_source_stack2(event)
        
    def on_slice_index1(self, event):
        self.tab.on_slice_index1(event)

    def on_slice_index2(self, event):
        self.tab.on_slice_index2(event)

    def on_calc_range1(self, event):
        self.tab.on_calc_range1(event)

    def on_calc_range2(self, event):
        self.tab.on_calc_range2(event)

    def on_calc_reset1(self, event):
        self.tab.on_calc_reset1(event)

    def on_calc_reset2(self, event):
        self.tab.on_calc_reset2(event)


