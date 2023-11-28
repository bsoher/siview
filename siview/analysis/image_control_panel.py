#!/usr/bin/env python

# Copyright (c) 2014-2022 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

# 3rd party modules
import wx

# Our modules
from siview.analysis.auto_gui.image_pane import ImagePaneUI
from siview.analysis.image_panel_siview import ImagePanelSiview


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

        self.image = ImagePanelSiview( self.PanelImagePlot,
                                       self.tab,
                                       self.tab_dataset,
                                       naxes=2,
                                       data=[],
                                       vertOn=True,
                                       horizOn=True,
                                       layout='horizontal',
                                      )
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.image, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.PanelImagePlot.SetSizer(sizer)
        self.image.Fit()


    # EVENT FUNCTIONS -----------------------------------------------

    def on_splitter(self, event):
        self.tab.on_splitter(event)



  
    
