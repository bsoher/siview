#!/usr/bin/env python
"""
Original image_panel_toolbar.py was expansion of matplotlib embed in wx example
see http://matplotlib.org/examples/user_interfaces/embedding_in_wx4.html

image_panel_mri <- image_panel_toolbar_multifov <- image_panel_toolbar

image_panel_mri.py, allows users to display one or more images in vertical or
horizontal arrangement of axes. A toolbar with custom icons is attached to the
bottom that allow the user to pan/zoom, width/level, show crosshairs, save
figures, and undo/home the images in the axes. Note. multiple axes are not
linked for pan/zoom operations in this version. This allows images of different
dimensions/fovs to be displayed. If 'fov' values are provided, then crosshair
locations are displayed appropriately in each image.

Brian J. Soher, Duke University, April, 2014
Update - 31 July 2022 - Py3 and Newer wx
Update - 7 November 2023
Update - 27 November 2023
- reworked width/level functionality to be internal to NavToolbarMri object


"""
# Python modules

import os
from enum import Enum

# third party modules
import wx
import numpy as np
import matplotlib
import matplotlib.cm as cm

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases          import NavigationToolbar2, cursors

from matplotlib.figure    import Figure
from numpy.random         import rand
from wx.lib.embeddedimage import PyEmbeddedImage

# Our modules
from siview.common.wx_gravy.nav_toolbar_mri import NavToolbarMri


LEVMAX =  383
LEVMIN = -127
WIDMAX =  255
WIDMIN =    0
LEVSTR =  128




# MPL widlev example
#
#http://matplotlib.1069221.n5.nabble.com/Pan-zoom-interferes-with-user-specified-right-button-callback-td12186.html


class ImagePanelMri(wx.Panel):
    """
    The ImagePanel has a Figure and a Canvas and 'n' Axes. The user defines
    the number of axes on Init and this number cannot be changed thereafter.
    However, the user can change the number of axes displayed in the Figure.
    
    Axes are specified on Init because the zoom and widlev actions 
    need an axes to attach to initialize properly.  
    
    on_size events simply set a flag, and the actual resizing of the figure is 
    triggered by an Idle event.
    
    """

    _EVENT_DEBUG = False    # Set to True to print messages to stdout during events.

    def __init__(self, parent, naxes=1, 
                               data=None, 
                               cmap=cm.gray, 
                               color=None,
                               bgcolor="#ffffff",
                               vertOn=False,
                               horizOn=False,
                               lcolor='gold', 
                               lw=0.5,
                               layout='vertical',
                               **kwargs):
        
        # initialize Panel
        if 'id' not in list(kwargs.keys()):
            kwargs['id'] = wx.ID_ANY
        if 'style' not in list(kwargs.keys()):
            kwargs['style'] = wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Panel.__init__( self, parent, **kwargs )

        self.figure = Figure(figsize=(4,4), dpi=100)

        self.cmap       = [cm.gray for i in range(naxes)]
        self.imageid    = [None    for i in range(naxes)]
        self.width      = [WIDMAX  for i in range(naxes)]
        self.level      = [LEVSTR  for i in range(naxes)]
        self.vmax       = [WIDMAX  for i in range(naxes)]
        self.vmin       = [LEVSTR  for i in range(naxes)]
        self.vmax_orig  = [WIDMAX  for i in range(naxes)]
        self.vmin_orig  = [LEVSTR  for i in range(naxes)]
        self.fov        = [1.0     for i in range(naxes)]
        
        # here we create the required naxes, add them to the figure, but we
        # also keep a permanent reference to each axes so they can be added
        # or removed from the figure as the user requests 1-N axes be displayed
        self.naxes = naxes   
        self.axes  = []

        if layout == 'vertical':
            self.axes.append(self.figure.add_subplot(naxes,1,1))
            if naxes>1:
                for i in range(naxes-1):
                    self.axes.append(self.figure.add_subplot(naxes,1,i+2)) #, sharex=self.axes[0], sharey=self.axes[0]))
        else:
            self.axes.append(self.figure.add_subplot(1,naxes,1))
            if naxes > 1:
                for i in range(naxes - 1):
                    self.axes.append(self.figure.add_subplot(1,naxes,i+2)) #, sharex=self.axes[0], sharey=self.axes[0]))

        self.all_axes = list(self.axes)
 
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.canvas.SetMinSize(wx.Size(1,1))
        self.figure.subplots_adjust(left=0.0,right=1.0,
                                    bottom=0.0,top=1.0,
                                    wspace=0.0,hspace=0.0)

        # for images we don't show x or y axis values
        for axes in self.axes:
            axes.set_adjustable('box')
            axes.xaxis.set_visible(False)
            axes.yaxis.set_visible(False)

        self.set_color( color )
        self.set_axes_color()

        if not data or len(data) != naxes:
            data = self._default_data()
        self.set_data(data)
        self.update(no_draw=True)   # we don't have a canvas yet

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        if layout == 'vertical':
            self.sizer_canvas = wx.BoxSizer(wx.VERTICAL)
            self.sizer_canvas.Add(self.canvas, 1, wx.EXPAND, 10)
        else:
            self.sizer_canvas = wx.BoxSizer(wx.HORIZONTAL)
            self.sizer_canvas.Add(self.canvas, 1, wx.EXPAND, 10)

        self.sizer.Add(self.sizer_canvas, 1, wx.TOP | wx.LEFT | wx.EXPAND)

        # Capture the paint message
        wx.EvtHandler.Bind(self, wx.EVT_PAINT, self.on_paint)

        self.toolbar = NavToolbarMri(self.canvas, self, vertOn=vertOn,
                                     horizOn=horizOn, lcolor=lcolor, lw=lw)
        self.toolbar.Realize()
        if wx.Platform == '__WXMAC__':
            # Mac platform (OSX 10.3, MacPython) does not seem to cope with
            # having a toolbar in a sizer. This work-around gets the buttons
            # back, but at the expense of having the toolbar at the top
            self.SetToolBar(self.toolbar)
        else:
            self.sizer.Add(self.toolbar, 0, wx.EXPAND)

        # update the axes menu on the toolbar
        self.toolbar.update()
        
        self.SetSizer(self.sizer)
        self.Fit()

        # link scroll events, but only handle if on_scroll() overloaded by user
        self.scroll_id     = self.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.keypress_id   = self.canvas.mpl_connect('key_press_event',   self.on_key_press)
        self.keyrelease_id = self.canvas.mpl_connect('key_release_event', self.on_key_release)
        self.shift_is_held = False
        self.select_is_held = False


    #=======================================================
    #
    #           Internal Helper Functions  
    #
    #=======================================================

    def on_key_press(self, event):
        if event.key == 'shift':
            self.shift_is_held = True
    
    def on_key_release(self, event):
        if event.key == 'shift':
            self.shift_is_held = False

    def _dprint(self, a_string):
        if self._EVENT_DEBUG:
            print(a_string)

    def _on_scroll(self, event):
        """
        This is the internal method that organizes the data that is sent to the
        external user defined event handler for scroll events. In here we 
        determine which axis we are in, then call the (hopefully) overloaded 
        on_scroll() method
        
        """
        if event.inaxes == None: return
        for i, axes in enumerate(self.axes):
            if axes == event.inaxes:
                iplot = i
        self.on_scroll(event.button, event.step, iplot)        


    def _default_data(self):
        data = []
        for i in range(self.naxes):
            data.append( [{'data':self._dist(128), 'fov':240.0},] )
        return data


    def _dist(self, n, m=None):  
        """
        Return a rectangular array in which each pixel = euclidian
        distance from the origin.

        """
        n1 = n
        m1 = n if m is None else m

        x = np.arange(n1)
        x = np.array([val**2 if val < (n1-val) else (n1-val)**2 for val in x ])
        a = np.ndarray((n1,m1),float)

        for i in range(int((m1/2)+1)):      # Row loop
            y = np.sqrt(x + i**2.0)         # Euclidian distance
            a[i,:] = y                      # Insert the row
            if i != 0:
                a[m1-i,:] = y               # Symmetrical

        return a
        

    def on_paint(self, event):
        # this is necessary or the embedded MPL canvas does not show
        self.canvas.draw()
        event.Skip()


    #=======================================================
    #
    #           Default Event Handlers  
    #
    #=======================================================
        
    def on_scroll(self, button, step, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_scroll,     button='+str(button)+'  step='+str(step)+'  Index = '+str(iplot))

    def on_motion(self, xloc, yloc, xpos, ypos, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_motion,          xloc='+str(xloc)+'  yloc='+str(yloc)+'  xpos='+str(xpos)+'  ypos='+str(ypos)+'  Index = '+str(iplot))
        
    def on_select(self, xloc, yloc, xpos, ypos, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_select,          xloc='+str(xloc)+'  yloc='+str(yloc)+'  xpos='+str(xpos)+'  ypos='+str(ypos)+'  Index = '+str(iplot))

    def on_panzoom_release(self, xloc, yloc, xpos, ypos):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_panzoom_release, xloc='+str(xloc)+'  yloc='+str(yloc)+'  xpos='+str(xpos)+'  ypos='+str(ypos))
        
    def on_panzoom_motion(self, xloc, yloc, xpos, ypos, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_panzoom_motion,  xloc='+str(xloc)+'  yloc='+str(yloc)+'  xpos='+str(xpos)+'  ypos='+str(ypos)+'  Index = '+str(iplot))

    def on_level_press(self, xloc, yloc, xpos, ypos, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_level_press,     xloc='+str(xloc)+'  yloc='+str(yloc)+'  xpos='+str(xpos)+'  ypos='+str(ypos)+'  Index = '+str(iplot))

    def on_level_release(self, xloc, yloc, xpos, ypos):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_level_release,   xloc='+str(xloc)+'  yloc='+str(yloc)+'  xpos='+str(xpos)+'  ypos='+str(ypos))

    def on_level_motion(self, xloc, yloc, xpos, ypos, iplot, wid, lev):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_level_motion,    xloc='+str(xloc)+'  yloc='+str(yloc)+'  xpos='+str(xpos)+'  ypos='+str(ypos)+'  Index = '+str(iplot))

    #=======================================================
    #
    #           User Accessible Data Functions  
    #
    #=======================================================

    def set_data(self, data, index=None, keep_norm=False):
        """
        User can set data into one or all axes using this method.
        
        If index is supplied, we assume that only one ndarray is being
        passed in via the data parameter. If no index is supplied then we
        assume that a list of ndarrays the size of self.naxes is being 
        passed in to replace all data in all axes.

        Example 1 - Data is a list of dicts
        
            raw  = {'data'  : raw_data,        # 2D numpy array 
                    'alpha' : 1.0 }            # value 0.0-1.0

            fit  = {'data' : fit_data,         # 2D numpy array 
                    'alpha' : 1.0 }            # value 0.0-1.0

            data = [raw, fit]
            self.view.set_data(data)
            self.view.update(set_scale=not self._scale_intialized, no_draw=True)
            self.view.canvas.draw()

        Example 2 - Data is a single numpy array, the colors dict will use
                    default values set in set_data() method
        
            data = [raw_data,]          # 2D numpy array
            data = [[data]]
            self.view.set_data(data)    # alpha defaults to 1.0
            self.view.update(set_scale=not self._scale_intialized, no_draw=True)
            self.view.canvas.draw()
                    
        """
        for i, item in enumerate(data):
            for j, dat in enumerate(item):
                if isinstance(dat, dict):
                    # Dict in this item, but ensure all keys are present
                    if 'data' not in list(dat.keys()):
                        raise ValueError( "must have a data array in the dict sent to set_data()")
                    if 'alpha' not in list(dat.keys()):
                        dat['alpha'] = 1.0
                    if 'keep_norm' not in list(dat.keys()):
                        dat['keep_norm'] = keep_norm
                    if 'patches' not in list(dat.keys()):
                        dat['patches'] = None
                    if 'lines' not in dat.keys():
                        dat['lines'] = None

                    if 'cmap' not in list(dat.keys()):
                        dat['cmap'] = self.cmap[i]
                    else:
                        self.cmap[i] = dat['cmap']

                    if 'vmax' not in list(dat.keys()):
                        dat['vmax'] = dat['data'].max()
                    else:
                        self.vmax[i] = dat['vmax']

                    if 'vmin' not in list(dat.keys()):
                        dat['vmin'] = dat['data'].min()
                    else:
                        self.vmin[i] = dat['vmin']

                    if 'fov' not in dat.keys():
                        dat['fov'] = self.fov[i]
                    else:
                        self.fov[i] = dat['fov']

                else:
                    # Only data in this item, so add all default values 
                    dat = { 'data'      : dat,
                            'alpha'     : 1.0,
                            'cmap'      : self.cmap[i],
                            'vmax'      : dat.max(),
                            'vmin'      : dat.min(),
                            'keep_norm' : keep_norm,
                            'patches'   : None,
                            'lines'     : None,
                            'fov'       : self.fov[i],
                          }
                        
                item[j] = dat
        
        if index:
            if index < 0 or index >= self.naxes:
                raise ValueError("index must be within that number of axes in the plot_panel")
            
            if data[0][0]['data'].shape != self.data[0][0]['data'].shape:
                raise ValueError( "new data must be a same number of spectral points as existing data")
            
            # even though we are inserting into an index, I want to force users
            # to submit a dict in a list of lists format so it is consistent 
            # with submitting a whole new set of data (below). We just take the
            # first list of dicts from the submitted data and put it in the 
            # index position
            self.data[index] = data[0]
            
        else:
            if len(data) != self.naxes:
                raise ValueError( "data must be a list with naxes number of ndarrays")
            for item in data:
                for dat in item:
                    d = dat['data']
                
                    padding = 2 - len(d.shape)
                    if padding > 0:
                        d.shape = ([1] * padding) + list(d.shape)
                    elif padding == 0:
                        # Nothing to do; data already has correct number of dims
                        pass
                    else:
                        # padding < 0 ==> data has too many dims
                        raise ValueError("Data with shape %s has too many dimensions" % str(item.shape))

            self.data = data

        for i,data in enumerate(self.data):
            if not data[0]['keep_norm']:
                self.vmax_orig[i] = data[0]['vmax']
                self.vmin_orig[i] = data[0]['vmin']
                self.vmax[i]      = data[0]['vmax']
                self.vmin[i]      = data[0]['vmin']
                

    def update(self, index=None, keep_norm=False, no_draw=False):
        """
        Convenience function that runs through all the typical steps needed
        to refresh the screen after a set_data().
        
        The set_scale option is typically used only once to start set the 
        bounding box to reasonable bounds for when a zoom box zooms back 
        out.
        
        """
        self.update_images(index=index)
        if not no_draw:
            self.canvas.draw()

    
    def update_images(self, index=None, force_bounds=False):
        """
        Sets the data from the normalized image numpy arrays into the axes.
        
        We also set the axes dataLim and viewLim ranges here just in case
        the dimensions on the image being displayed has changed. This reset
        allows the zoom reset to work properly.
        
        """
        indices = self.parse_indices(index)
        
        for i in indices:

            axes = self.all_axes[i]
            
            if axes.images:
                yold, xold = axes.images[0].get_array().shape
            else:
                yold, xold = -1,-1

            for item in axes.images:
                item.remove()

            ddict    = self.data[i][0]
            data     = ddict['data'].copy() 
            alpha    = ddict['alpha']
            cmap     = ddict['cmap']
            vmax     = self.vmax[i]
            vmin     = self.vmin[i]
            patches  = ddict['patches']
            lines    = ddict['lines']
                
            xmin, xwid, ymin, ywid = 0, data.shape[1], 0, data.shape[0]
            
            # Explicit set origin here so the user rcParams value is not used. 
            # This keeps us consistent across users.
            self.imageid[i] = axes.imshow(data, cmap=cmap, 
                                                alpha=alpha, 
                                                vmax=vmax, 
                                                vmin=vmin,
                                                aspect='equal',
                                                origin='upper') 
            if patches is not None:
                self.imageid[i].axes.patches = []
                for patch in patches:
                    self.imageid[i].axes.add_patch(patch)
            else:
                for item in self.imageid[i].axes.patches:
                    item.remove()

            if len(self.imageid[i].axes.lines) > 2:
                # should be two lines in here for cursor tracking
                self.imageid[i].axes.lines = self.imageid[i].axes.lines[0:2]
            if lines is not None:
                for line in lines:
                    self.imageid[i].axes.add_line(line)

            if xold != xwid or yold!=ywid or force_bounds: 
                xmin -= 0.5     # this centers the image range to voxel centers
                ymin -= 0.5   
                # Set new bounds for dataLims to x,y extent of data in the 
                # new image. On reset zoom this is how far we reset the limits.
                axes.ignore_existing_data_limits = True
                axes.update_datalim([[xmin,ymin],[xmin+xwid,ymin+ywid]])
#                 # Matches viewLims view limits to the new data. By 
#                 # default, new data and updating causes display to show the 
#                 # entire image. Any zoom setting is lost.
#                 axes.set_xlim((xmin, xmin+xwid), auto=None)
#                 axes.set_ylim((ymin, ymin+ywid), auto=None)
# # 
# #             # may need this line in future if we do overlay
# #                 self.figure.hold(True)
# #             self.figure.hold(False)


    def parse_indices(self, index=None):
        """ 
        Ensure we know what data axes to act upon
         - index can be a list or scalar
         - if list, must be naxes items or less
         - list/scalar values need to be in range of 0 to naxes-1
        
        """
        if index is None:
            indices = list(range(self.naxes))
        else:
            if isinstance(index, list):
                if len(index) <= self.naxes:
                    if all(index < self.naxes):
                        indices = index
                    else:
                        raise ValueError( "index in list outside naxes range")
                else:
                    raise ValueError("too many index entries")
            else:
                if index < self.naxes:
                    indices = [index]
                else:
                    raise ValueError("scalar index outside naxes range")
            
        return indices 


    #=======================================================
    #
    #           User Accessible Display Functions  
    #
    #=======================================================

    def set_color( self, rgbtuple=None ):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ).Get()
        clr = [c/255. for c in rgbtuple]
        self.figure.set_facecolor( clr )
        self.figure.set_edgecolor( clr )
        self.canvas.SetBackgroundColour( wx.Colour( *rgbtuple ) )
        
    def set_axes_color( self, rgbtuple=None ):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ).Get()
        clr = [c/255. for c in rgbtuple]
        for axis in self.all_axes:
            axis.spines['bottom'].set_color(clr)
            axis.spines['top'].set_color(clr) 
            axis.spines['right'].set_color(clr)
            axis.spines['left'].set_color(clr)





# Test Code ------------------------------------------------------------------

class util_CreateMenuBar:
    """
    Example of the menuData function that needs to be in the program
    in which you are creating a Menu
    
        def menuData(self):
            return [("&File", (
                        ("&New",  "New Sketch file",  self.OnNew),
                        ("&Open", "Open sketch file", self.OnOpen),
                        ("&Save", "Save sketch file", self.OnSave),
                        ("", "", ""),
                        ("&Color", (
                            ("&Black",    "", self.OnColor,      wx.ITEM_RADIO),
                            ("&Red",      "", self.OnColor,      wx.ITEM_RADIO),
                            ("&Green",    "", self.OnColor,      wx.ITEM_RADIO),
                            ("&Blue",     "", self.OnColor,      wx.ITEM_RADIO),
                            ("&Other...", "", self.OnOtherColor, wx.ITEM_RADIO))),
                        ("", "", ""),
                        ("About...", "Show about window", self.OnAbout),
                        ("&Quit",    "Quit the program",  self.OnCloseWindow)))]    
    """
    def __init__(self, self2):
        menuBar = wx.MenuBar()
        for eachMenuData in self2.menuData():
            menuLabel = eachMenuData[0]
            menuItems = eachMenuData[1]
            menuBar.Append(self.createMenu(self2, menuItems), menuLabel)
        self2.SetMenuBar(menuBar)

    def createMenu(self, self2, menuData):
        menu = wx.Menu()
        for eachItem in menuData:
            if len(eachItem) == 2:
                label = eachItem[0]
                subMenu = self.createMenu(self2, eachItem[1])
                menu.Append(wx.ID_ANY, label, subMenu)
            else:
                self.createMenuItem(self2, menu, *eachItem)
        return menu

    def createMenuItem(self, self2, menu, label, status, handler, kind=wx.ITEM_NORMAL):
        if not label:
            menu.AppendSeparator()
            return
        menuItem = menu.Append(-1, label, status, kind)
        self2.Bind(wx.EVT_MENU, handler, menuItem)
        
        
class DemoImagePanel(ImagePanelMri):
    """Plots several lines in distinct colors."""

    # Activate event messages
    _EVENT_DEBUG = True
    
    def __init__( self, parent, tab, statusbar, **kwargs ):
        # statusbar has to be here for NavToolbarMultiFov to discover on init()
        self.statusbar = statusbar
        # initiate plotter
        sizer = ImagePanelMri.__init__(  self,
                                         parent,
                                         vertOn=True,
                                         horizOn=True,
                                         lcolor='gold',
                                         lw=0.5,
                                         **kwargs )
        
        self.tab    = tab
        self.top    = wx.GetApp().GetTopWindow()
        self.parent = parent
        self.count  = 0
        
        self.statusbar = statusbar

    def on_motion(self, xloc, yloc, xpos, ypos, iplot):
        value = self.data[iplot][0]['data'][int(round(xloc))][int(round(yloc))]
        self.top.statusbar.SetStatusText( " Value = %s" % (str(value), ), 0)
        self.top.statusbar.SetStatusText( " X,Y = %i,%i" % (int(round(xloc)),int(round(yloc))) , 1)
        self.top.statusbar.SetStatusText( " " , 2)
        self.top.statusbar.SetStatusText( " " , 3)

    def on_panzoom_motion(self, xloc, yloc, xpos, ypos, iplot):
        axes = self.axes[iplot]
        xmin,xmax = axes.get_xlim()
        ymax,ymin = axes.get_ylim()         # max/min flipped here because of y orient top/bottom
        xdelt, ydelt = xmax-xmin, ymax-ymin
        
        self.top.statusbar.SetStatusText(( " X-range = %.1f to %.1f" % (xmin, xmax)), 0)
        self.top.statusbar.SetStatusText(( " Y-range = %.1f to %.1f" % (ymin, ymax)), 1)
        self.top.statusbar.SetStatusText(( " delta X,Y = %.1f,%.1f " % (xdelt,ydelt )), 2)
        self.top.statusbar.SetStatusText( " " , 3)

    def on_level_motion(self, xloc, yloc, xpos, ypos, iplot, wid, lev):
        self.top.statusbar.SetStatusText( " " , 0)
        self.top.statusbar.SetStatusText(( " Width = %i " % (self.width[iplot],)), 1)
        self.top.statusbar.SetStatusText(( " Level = %i " % (self.level[iplot],)), 2)
        self.top.statusbar.SetStatusText(( "wid/lev = %.1f / %.1f" % (wid, lev)),  3)



class MyFrame(wx.Frame):
    def __init__(self, title="New Title Please", size=(350,200)):
 
        wx.Frame.__init__(self, None, title=title, pos=(150,150), size=size)
        self.Bind(wx.EVT_CLOSE, self.on_close)
 
        util_CreateMenuBar(self)

        self.statusbar = self.CreateStatusBar(4, 0)
 
        self.size_small  = 32
        self.size_medium = 128
        self.size_large  = 256
 
        data1 = { 'data'  : self.dist(self.size_small),
                  'alpha' : 1.0
                }

        data2 = { 'data'  : 100-self.dist(self.size_medium),
                  'alpha' : 0.5,
                  'cmap'  : cm.hsv,
                }

        data = [[data1], [data2]]

        # data1 = {'data': self.dist(self.size_medium),
        #          'alpha': 1.0
        #          }
        #
        # data = [[data1],]
         
        self.nb = wx.Notebook(self, -1, style=wx.BK_BOTTOM)
         
        panel1 = wx.Panel(self.nb, -1)
         
        self.view = DemoImagePanel(panel1, self, self.statusbar, naxes=2, data=data)
#        self.view = DemoImagePanel(panel1, self, self.statusbar, naxes=1, data=data)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.view, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        panel1.SetSizer(sizer)
        self.view.Fit()    
     
        self.nb.AddPage(panel1, "One")

    def menuData(self):
        return [("&File", (
                    ("", "", ""),
                    ("&Quit",    "Quit the program",  self.on_close))),
                 ("Tests", (
                     ("Set Small Images - keep norm",  "", self.on_small_images_keep_norm),
                     ("Set Medium Images - keep norm", "", self.on_medium_images_keep_norm),
                     ("Set Large Images - keep norm",  "", self.on_large_images_keep_norm),
                     ("", "", ""),
                     ("Set Small Images",  "", self.on_small_images),
                     ("Set Medium Images", "", self.on_medium_images),
                     ("Set Large Images",  "", self.on_large_images),
                     ("", "", ""),
                     ("Placeholder",    "non-event",  self.on_placeholder)))]       

    def on_close(self, event):
        dlg = wx.MessageDialog(self, 
            "Do you really want to close this application?",
            "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            self.Destroy()

    def on_placeholder(self, event):
        print( "Event handler for on_placeholder - not implemented")


    def on_small_images_keep_norm(self, event):
        self.on_small_images(event, keep_norm=True)

    def on_small_images(self, event, keep_norm=False):

        data1 = { 'data'  : self.dist(self.size_small),
                  'alpha' : 1.0
                }

        data2 = { 'data'  : 100-self.dist(self.size_small),
                  'alpha' : 0.5,
                  'cmap'  : cm.hsv,
                }
        
        data = [[data1], [data2]]

        self.view.set_data(data, keep_norm=keep_norm)
        self.view.update(no_draw=True, keep_norm=keep_norm)
        self.view.canvas.draw()

    def on_medium_images_keep_norm(self, event):
        self.on_medium_images(event, keep_norm=True)

    def on_medium_images(self, event, keep_norm=False):

        data1 = { 'data'  : self.dist(self.size_medium),
                  'alpha' : 1.0
                }

        data2 = { 'data'  : 100-self.dist(self.size_medium),
                  'alpha' : 0.5,
                  'cmap'  : cm.hsv,
                }
        
        data = [[data1], [data2]]

        self.view.set_data(data, keep_norm=keep_norm)
        self.view.update(no_draw=True, keep_norm=keep_norm)
        self.view.canvas.draw()

    def on_large_images_keep_norm(self, event):
        self.on_large_images(event, keep_norm=True)

    def on_large_images(self, event, keep_norm=False):

        data1 = { 'data'  : self.dist(self.size_large),
                  'alpha' : 1.0
                }

        data2 = { 'data'  : 100-self.dist(self.size_large),
                  'alpha' : 0.5,
                  'cmap'  : cm.hsv,
                }
        
        data = [[data1], [data2]]

        self.view.set_data(data, keep_norm=keep_norm)
        self.view.update(no_draw=True, keep_norm=keep_norm)
        self.view.canvas.draw()        
        

    def dist(self, n, m=None):  
        """
        Return a rectangular array in which each pixel = euclidian
        distance from the origin.

        """
        n1 = n
        m1 = m if m else n

        x = np.arange(n1)
        x = np.array([val**2 if val < (n1-val) else (n1-val)**2 for val in x ])
        a = np.ndarray((n1,m1),float)   # Make array

        for i in range(int((m1/2)+1)):  # Row loop
            y = np.sqrt(x + i**2.0)     # Euclidian distance
            a[i,:] = y                  # Insert the row
            if i != 0: a[m1-i,:] = y    # Symmetrical
        return a


#----------------------------------------------------------------
#----------------------------------------------------------------
# Saved code

# class MyNavigationToolbar(NavigationToolbar2WxAgg):
#     """
#     Extend the default wx toolbar with your own event handlers
#     """
#     ON_CUSTOM = wx.NewIdRef()
#     def __init__(self, canvas, cankill):
#          
#         # create the default toolbar
#         NavigationToolbar2WxAgg.__init__(self, canvas)
#  
#         # remove the unwanted button
#         POSITION_OF_CONFIGURE_SUBPLOTS_BTN = 6
#         self.DeleteToolByPos(POSITION_OF_CONFIGURE_SUBPLOTS_BTN) 
#  
#         # for simplicity I'm going to reuse a bitmap from wx, you'll
#         # probably want to add your own.
#         self.AddSimpleTool(self.ON_CUSTOM, _load_bitmap('stock_left.xpm'), 'Click me', 'Activate custom contol')
#         wx.EVT_TOOL(self, self.ON_CUSTOM, self._on_custom)
#  
#     def _on_custom(self, evt):
#         # add some text to the axes in a random location in axes (0,1)
#         # coords) with a random color
#  
#         # get the axes
#         ax = self.canvas.figure.axes[0]
#  
#         # generate a random location can color
#         x,y = tuple(rand(2))
#         rgb = tuple(rand(3))
#  
#         # add the text and draw
#         ax.text(x, y, 'You clicked me',
#                 transform=ax.transAxes,
#                 color=rgb)
#         self.canvas.draw()
#         evt.Skip()



#     def calc_lut_value(self, data, width, level):
#         """Apply Look-Up Table values to data for given width/level values."""
# 
#         conditions = [data <= (level-0.5-(width-1)/2), data > (level-0.5+(width-1)/2)]
#         functions  = [0, 255, lambda data: ((data - (level - 0.5))/(width-1) + 0.5)*(255-0)]   # 3rd function is default
#         lutvalue = np.piecewise(data, conditions, functions)
# 
#         # Convert the resultant array to an unsigned 8-bit array to create
#         # an 8-bit grayscale LUT since the range is only from 0 to 255
#         return np.array(lutvalue, dtype=np.uint8)





if __name__ == '__main__':

    app   = wx.App( False )
    frame = MyFrame( title='WxPython and Matplotlib bjs', size=(600,600) )
    frame.Show()
    app.MainLoop()
