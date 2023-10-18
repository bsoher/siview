#!/usr/bin/env python

# Copyright (c) 2014-2022 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules
import wx
import siview.common.image_panel_toolbar as image_panel_toolbar
        

class ImagePanelSiview(image_panel_toolbar.ImagePanelToolbar2):
    
    def __init__(self, parent, tab, tab_siview, **kwargs):

        self.statusbar = tab.top.statusbar
        
        image_panel_toolbar.ImagePanelToolbar2.__init__( self, parent, **kwargs )

        # tab is the containing widget for this plot_panel, it is used
        # in resize events, the tab attribute is the AUI Notebook tab
        # that contains this plot_panel

        self.tab   = tab  
        self.tab_siview = tab_siview
        self.top   = wx.GetApp().GetTopWindow()
        
        self.set_color( (255,255,255) )


    # EVENT FUNCTIONS -----------------------------------------------
    
    def on_motion(self, xloc, yloc, iplot):
       
        xvox, yvox, zvox = self.tab.voxel
        xloc  = int(xloc)
        yloc  = int(yloc)
        iplot = int(iplot)
        value = self.data[iplot][0]['data'][yloc][xloc]
        self.top.statusbar.SetStatusText( " Cursor X,Y,Slc=%i,%i,%i" % (round(xloc),round(yloc),zvox), 0)
        self.top.statusbar.SetStatusText( " Cursor Value = %s" % (str(value), ), 1)
        self.top.statusbar.SetStatusText( " " , 2)
        self.top.statusbar.SetStatusText( " Plot X,Y,Slc=%i,%i,%i" % (xvox,yvox,zvox), 3)
        
    
    def on_scroll(self, button, step, iplot):

        xvox, yvox, zvox = self.tab.voxel
        step = 1 if step>0 else -1
        dims = self.tab.dataset.dims
        tmp = self.tab.voxel[2] + step
        tmp = tmp if tmp>0 else 0
        tmp = tmp if tmp<dims[2]-1 else dims[2]-1
        self.tab.voxel[2] = tmp
        zvox = tmp
        self.tab.process()
        self.tab.plot()
        self.tab.show()
        self.top.statusbar.SetStatusText( " Cursor X,Y,Slc=%i,%i,%i" % (xvox,yvox,zvox), 0)
        self.top.statusbar.SetStatusText( " Plot X,Y,Slc=%i,%i,%i"   % (xvox,yvox,zvox), 3)


    def on_select(self, xloc, yloc, iplot):
        self.tab.voxel[0] = int(round(xloc))
        self.tab.voxel[1] = int(round(yloc))
        self.tab.process()
        self.tab.plot()
       
            
    def on_panzoom_release(self, xloc, yloc):
        xvox, yvox, zvox = self.tab.voxel
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" ", 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText( " Plot X,Y,Slc=%i,%i,%i" % (xvox,yvox,zvox), 3)


    def on_panzoom_motion(self, xloc, yloc, iplot):
        axes = self.axes[iplot]
        xmin,xmax = axes.get_xlim()
        ymax,ymin = axes.get_ylim()         # max/min flipped here because of y orient top/bottom
        xdelt, ydelt = xmax-xmin, ymax-ymin
        
        self.top.statusbar.SetStatusText(( " X-range = %.1f to %.1f" % (xmin, xmax)), 0)
        self.top.statusbar.SetStatusText(( " Y-range = %.1f to %.1f" % (ymin, ymax)), 1)
        self.top.statusbar.SetStatusText(( " delta X,Y = %.1f,%.1f " % (xdelt,ydelt )), 2)
        self.top.statusbar.SetStatusText(( " Area = %i " % (xdelt*ydelt, )), 3)


    def on_level_release(self, xloc, yloc):
        xvox, yvox, zvox = self.tab.voxel
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" ", 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText( " Plot X,Y,Slc=%i,%i,%i" % (xvox,yvox,zvox), 3)


    def on_level_press(self, xloc, yloc, iplot):
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" ", 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" ", 3)

        
    def on_level_motion(self, xloc, yloc, iplot):
        xvox, yvox, zvox = self.tab.voxel
        self.top.statusbar.SetStatusText( " " , 0)
        self.top.statusbar.SetStatusText( " Width = %i " % (self.width[iplot],), 1)
        self.top.statusbar.SetStatusText( " Level = %i " % (self.level[iplot],), 2)
        self.top.statusbar.SetStatusText( " Plot X,Y,Slc=%i,%i,%i" % (xvox,yvox,zvox), 3)

            
    
        
  
    
