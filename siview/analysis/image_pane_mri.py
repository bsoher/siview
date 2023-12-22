#!/usr/bin/env python
"""
  Copyright (c) 2014-2022 Brian J Soher - All Rights Reserved

  Redistribution and use in source and binary forms, with or without
  modification, are not permitted without explicit permission.

Original image_panel_toolbar.py was expansion of matplotlib embed in wx example
see http://matplotlib.org/examples/user_interfaces/embedding_in_wx4.html

image_pane_mri <- image_panel_toolbar_multifov <- image_panel_toolbar

image_pane_mri.py, allows users to display one or more images in vertical or
horizontal arrangement of axes. A toolbar with custom icons is attached to the
bottom that allow the user to pan/zoom, width/level, show crosshairs, save
figures, and undo/home the images in the axes. Note. multiple axes are not
linked for pan/zoom operations in this version. This allows images of different
dimensions/fovs to be displayed. If 'fov' values are provided, then crosshair
locations are displayed appropriately in each image.

This is embedded in a sizer with controls for what images are loaded into
each canvas/axes, and what ceil/floor values are applied when data is loaded.

Brian J. Soher, Duke University, April, 2014
Update - 27 November 2023
- reworked width/level functionality to be internal to NavToolbarMri object
- added the original common\image_panel_mri.py to analysis\image_pane_mri.py

"""

# Python modules

# 3rd party modules
import wx
import numpy as np
import matplotlib
import matplotlib.cm as cm

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure

# Our modules
from siview.analysis.auto_gui.image_pane import ImagePaneUI
from siview.common.wx_gravy.image_panel_mri import ImagePanelMri
from siview.common.wx_gravy.nav_toolbar_mri import NavToolbarMri

WIDMAX = 4096
LEVSTR =  128
WIDSTR =  255



class ImagePaneMri(ImagePaneUI):

    def __init__(self,
                 parent,
                 tab,
                 tab_dataset,
                 naxes=1,
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
        """
        The ImagePanel has a Figure and a Canvas and 'n' Axes. The user defines
        the number of axes on Init and this number cannot be changed thereafter.
        However, the user can change the number of axes displayed in the Figure.

        Axes are specified on Init because the zoom and widlev actions
        need an axes to attach to initialize properly.

        on_size events simply set a flag, and the actual resizing of the figure is
        triggered by an Idle event.

        """
        _EVENT_DEBUG = False  # Set to True to print messages to stdout during events.

        self.statusbar = tab.top.statusbar

        ImagePaneUI.__init__( self, parent, **kwargs )

        # tab is the containing widget for this plot_panel, it is used
        # in resize events, the tab attribute is the AUI Notebook tab
        # that contains this plot_panel

        self.tab = tab
        self.top = wx.GetApp().GetTopWindow()
        self.tab_dataset = tab_dataset

        self.figure = Figure(figsize=(4,4), dpi=100)

        self.last_x = 0
        self.last_y = 0
        self.vertOn = vertOn
        self.horizOn = horizOn
        self.lcolor = lcolor
        self.lw = lw
        self.cmap       = [cmap    for i in range(naxes)]
        self.imageid    = [None    for i in range(naxes)]
        self.fov        = [1.0     for i in range(naxes)]
        self.naxes = naxes
        self.axes = []

        self.init_image_panel(naxes, data, layout, vertOn, horizOn, color, lcolor, lw)



    # EVENT FUNCTIONS -----------------------------------------------

    def init_image_panel(self, naxes, data, layout, vertOn, horizOn, color, lcolor, lw):

        # Create required naxes and add to figure, also keep a permanent ref
        # to each axes so they can be added or removed from the figure as the
        # user requests 1-N axes be displayed. TODO - bjs this may be outdated?

        if layout == 'vertical':
            self.axes.append(self.figure.add_subplot(naxes, 1, 1))
            if naxes > 1:
                for i in range(naxes - 1):
                    self.axes.append(self.figure.add_subplot(naxes, 1, i + 2))
        else:
            self.axes.append(self.figure.add_subplot(1, naxes, 1))
            if naxes > 1:
                for i in range(naxes - 1):
                    self.axes.append(self.figure.add_subplot(1, naxes, i + 2))

        self.all_axes = list(self.axes)

        self.canvas = FigureCanvas(self.PanelImagePlot, -1, self.figure)
        self.canvas.SetMinSize(wx.Size(1, 1))
        self.figure.subplots_adjust(left=0.0, right=1.0,
                                    bottom=0.0, top=1.0,
                                    wspace=0.0, hspace=0.0)

        # for images we don't show x or y axis values
        for axes in self.axes:
            axes.set_adjustable('box')
            axes.xaxis.set_visible(False)
            axes.yaxis.set_visible(False)

        self.set_color(color)
        self.set_axes_color()

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        if layout == 'vertical':
            self.sizer_canvas = wx.BoxSizer(wx.VERTICAL)
            self.sizer_canvas.Add(self.canvas, 1, wx.EXPAND, 10)
        else:
            self.sizer_canvas = wx.BoxSizer(wx.HORIZONTAL)
            self.sizer_canvas.Add(self.canvas, 1, wx.EXPAND, 10)

        self.sizer.Add(self.sizer_canvas, 1, wx.TOP | wx.LEFT | wx.EXPAND)

        # Capture the paint message
        wx.EvtHandler.Bind(self, wx.EVT_PAINT, self.on_paint) # bjs self.PanelImagePlot??

        self.toolbar = NavToolbarMri(self.canvas, self,
                                     vertOn=vertOn,
                                     horizOn=horizOn,
                                     lcolor=lcolor, lw=lw)
        self.toolbar.Realize()
        if wx.Platform == '__WXMAC__':
            # Mac platform (OSX 10.3, MacPython) does not seem to cope with
            # having a toolbar in a sizer. This work-around gets the buttons
            # back, but at the expense of having the toolbar at the top
            self.PanelImagePlot.SetToolBar(self.toolbar)
        else:
            self.sizer.Add(self.toolbar, 0, wx.EXPAND)

        # update the axes menu on the toolbar
        self.toolbar.update()

        if not data or len(data) != naxes:
            data = self._default_data()
        self.set_data(data)
        self.update(no_draw=False)  # we don't have a canvas yet


        self.PanelImagePlot.SetSizer(self.sizer)
        self.PanelImagePlot.Fit()

        # link scroll events, but only handle if on_scroll() overloaded by user
        self.scroll_id = self.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.keypress_id = self.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.keyrelease_id = self.canvas.mpl_connect('key_release_event', self.on_key_release)
        self.shift_is_held = False
        self.select_is_held = False

    # =======================================================
    #
    #           Internal Helper Functions
    #
    # =======================================================

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
        iplot = self.get_plot_index(event)
        self.on_scroll(event.button, event.step, iplot)

    def _default_data(self):
        data = []
        for i in range(self.naxes):
            data.append({'data': self.dist(24), 'fov': 240.0})
        return data

    def _dist(self, n, m=None):
        """ a rectangular array where each pixel = euclidian distance from the origin. """
        n1 = n
        m1 = n if m is None else m
        x = np.array([val ** 2 if val < (n1 - val) else (n1 - val) ** 2 for val in np.arange(n1)])
        a = np.ndarray((n1, m1), float)  # Make array
        for i in range(int((m1 / 2) + 1)):  # Row loop
            a[i, :] = np.sqrt(x + i ** 2.0)  # Euclidian distance
            if i != 0: a[m1 - i, :] = a[i, :]  # Symmetrical
        return a

    def dist(self, nx, ny=None):
        '''  Implements the IDL dist() function in Python '''
        if ny is None:
            ny = nx
        x = np.linspace(start=-nx / 2, stop=nx / 2 - 1, num=nx)
        y = np.linspace(start=-ny / 2, stop=ny / 2 - 1, num=ny)
        xx = x + 1j * y[:, np.newaxis]
        out = np.roll(np.roll(np.abs(xx), int(nx/2), 1), int(ny/2), 0)
        return out

    def dist3(self, nx, ny=None, nz=1):
        ''' Implements the IDL dist() function in Python '''
        if nz==1:
            return self.dist(nx, ny=ny)

        if ny is None:
            ny = nx
        x = np.linspace(start=-nx / 2, stop=nx / 2 - 1, num=nx)
        y = np.linspace(start=-ny / 2, stop=ny / 2 - 1, num=ny)
        xx = x + 1j * y[:, np.newaxis]
        r2d = np.roll(np.roll(np.abs(xx), int(nx/2), 1), int(ny/2), 0)

        z = np.linspace(start=-nz / 2, stop=nz / 2 - 1, num=nz)
        z = -1 * (np.abs(z) - nz/2)

        out = r2d * z[:, None, None]

        return out

    def on_paint(self, event):
        # this is necessary or the embedded MPL canvas does not show
        self.canvas.draw_idle()
        event.Skip()

    def get_plot_index(self, event):
        for i, axes in enumerate(self.axes):
            if axes == event.inaxes:
                return i
        return None


    #=======================================================
    #
    #           Default Event Handlers
    #
    #=======================================================

    def on_splitter(self, event):
        self.tab.on_splitter(event)

    def on_scroll(self, button, step, iplot):
        xvox, yvox, zvox = self.tab_dataset.voxel
        step = 1 if step > 0 else -1
        dims = self.tab.dataset.spectral_dims
        tmp = self.tab_dataset.voxel[2] + step
        tmp = tmp if tmp > 0 else 0
        tmp = tmp if tmp < dims[3] - 1 else dims[3] - 1
        self.tab_dataset.voxel[2] = tmp
        zvox = tmp
        # self.tab.process()
        # self.tab.plot()
        # self.tab.show()
        # self.top.statusbar.SetStatusText( " Cursor X,Y,Slc=%i,%i,%i" % (xvox,yvox,zvox), 0)
        # self.top.statusbar.SetStatusText( " Plot X,Y,Slc=%i,%i,%i"   % (xvox,yvox,zvox), 3)

    def on_motion(self, xloc, yloc, xpos, ypos, iplot):
        xloc  = int(xloc)
        yloc  = int(yloc)
        iplot = int(iplot)
        val   = self.data[iplot]['data'][yloc, xloc]
        self.top.statusbar.SetStatusText(" Value = %s" % (str(val),), 0)
        self.top.statusbar.SetStatusText(" X,Y = %i,%i" % (int(round(xloc+1)), int(round(yloc+1))), 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" ", 3)

        if self.select_is_held:
            if xloc == self.last_x and yloc == self.last_y:  # minimize event calls
                return
            self.tab_dataset.SpinX.SetValue(xloc+1)
            self.tab_dataset.SpinY.SetValue(yloc+1)
            self.last_x = xloc
            self.last_y = yloc
            self.tab.plot_dynamic(xloc, yloc)
            #self.tab_dataset.set_voxel(dynamic=True)

    def on_select(self, xloc, yloc, xpos, ypos, iplot):
        npts, xdim, ydim, zdim, _, _ = self.tab.dataset.spectral_dims
        xpos = int(round(xdim * xpos/self.fov[iplot]))
        ypos = int(round(ydim * ypos / self.fov[iplot]))
        if xpos == self.last_x and ypos == self.last_y:  # minimize event calls
            return
        self.tab_dataset.SpinX.SetValue(xpos + 1)
        self.tab_dataset.SpinY.SetValue(ypos + 1)
        self.last_x = xpos
        self.last_y = ypos
        self.tab_dataset.on_voxel_change()

    def on_panzoom_release(self, xloc, yloc, xpos, ypos):
        xvox, yvox, zvox = self.tab_dataset.voxel
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText(" ", 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" Plot X,Y,Slc=%i,%i,%i" % (xvox, yvox, zvox), 3)

    def on_panzoom_motion(self, xloc, yloc, xpos, ypos, iplot):
        axes = self.axes[iplot]
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
        self.top.statusbar.SetStatusText(" Width = %i " % (self.toolbar.width[iplot],), 1)
        self.top.statusbar.SetStatusText(" Level = %i " % (self.toolbar.level[iplot],), 2)
        self.top.statusbar.SetStatusText(" Plot X,Y,Slc=%i,%i,%i" % (xvox, yvox, zvox), 3)


    # Image Control events ---------------------------------------

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
        self.tab.show()

    def on_slice_index1(self, event):
        wx.CallAfter(self._slice_index_changed1)

    def _slice_index_changed1(self):
        tmp = self.SpinSliceIndex1.GetValue() - 1
        dims = self.tab.stack_sources[self.tab.stack1_select]['data'].shape
        tmp = max(0, min(dims[3] - 1, tmp))  # clip to range
        self.SpinSliceIndex1.SetValue(tmp)
        self.tab.stack_sources[self.tab.stack1_select]['slice'] = tmp
        self.tab.show()

    def on_slice_index2(self, event):
        wx.CallAfter(self._slice_index_changed1)

    def _slice_index_changed2(self):
        tmp = self.SpinSliceIndex2.GetValue() - 1
        dims = self.tab.stack_sources[self.tab.stack2_select]['data'].shape
        tmp = max(0, min(dims[3] - 1, tmp))  # clip to range
        self.SpinSliceIndex2.SetValue(tmp)
        self.tab.stack_sources[self.tab.stack2_select]['slice'] = tmp
        self.tab.show()

    def on_stack_range1(self, event):
        ceil_val = self.FloatStackCeil1.GetValue()
        floor_val = self.FloatStackFloor1.GetValue()
        tmp = [floor_val, ceil_val] if floor_val < ceil_val else [ceil_val, floor_val]
        self.FloatStackCeil1.SetValue(tmp[1])
        self.FloatStackFloor1.SetValue(tmp[0])
        d = self.tab.stack_sources[self.tab.stack1_select]
        d['floor'] = tmp[0]
        d['ceil'] = tmp[1]
        self.tab.show()

    def on_stack_range2(self, event):
        ceil_val = self.FloatStackCeil2.GetValue()
        floor_val = self.FloatStackFloor2.GetValue()
        tmp = [floor_val, ceil_val] if floor_val < ceil_val else [ceil_val, floor_val]
        self.FloatStackCeil2.SetValue(tmp[1])
        self.FloatStackFloor2.SetValue(tmp[0])
        d = self.tab.stack_sources[self.tab.stack2_select]
        d['floor'] = tmp[0]
        d['ceil'] = tmp[1]
        self.tab.show()

    def on_stack_reset1(self, event):
        d = self.tab.stack_sources[self.tab.stack1_select]
        d['floor'] = np.nanmin(d['data'])
        d['ceil'] = np.nanmax(d['data'])
        self.FloatStackFloor1.SetValue(d['floor'])
        self.FloatStackCeil1.SetValue(d['ceil'])
        self.tab.show()

    def on_stack_reset2(self, event):
        d = self.tab.stack_sources[self.tab.stack2_select]
        d['floor'] = np.nanmin(d['data'])
        d['ceil'] = np.nanmax(d['data'])
        self.FloatStackFloor2.SetValue(d['floor'])
        self.FloatStackCeil2.SetValue(d['ceil'])
        self.tab.show()


    # =======================================================
    #
    #           User Accessible Data Functions
    #
    # =======================================================

    def set_data(self, data, index=None):
        """
        User can set data into one or all axes using this method.

        If index is not None, only one ndarray is passed in data.

        If index is None, a list of self.naxes ndarrays is in data to replace
        all data in all axes.

        Example 1 - Data is a list of dicts

            raw  = {'data'  : image1,          # 2D numpy array
                    'fov'   : 240.0 }          # float, in [mm]
            fit  = {'data' : image2,           # 2D numpy array
                    'fov'   : 240.0 }          # float, in [mm]
            data = [raw, fit]
            self.image.set_data(data)
            self.image.update(set_scale=not self._scale_intialized, no_draw=True)
            self.image.canvas.draw()

        Example 2 - Data is a list with a single numpy array, other parameters
                    will use existing/default values

            data = [image1,]            # 2D numpy array
            data = [data,]
            self.image.set_data(data)    # alpha defaults to 1.0
            self.image.update(set_scale=not self._scale_intialized, no_draw=True)
            self.image.canvas.draw()

        """
        for i, dat in enumerate(data):
            if isinstance(dat, dict):
                # Dict in this item, but ensure all keys are present
                if 'data' not in list(dat.keys()):
                    raise ValueError("must have a data array in the dict sent to set_data()")
                if 'cmap' not in list(dat.keys()):
                    dat['cmap'] = self.cmap[i]
                else:
                    self.cmap[i] = dat['cmap']
                if 'fov' not in dat.keys():
                    dat['fov'] = self.fov[i]
                else:
                    self.fov[i] = dat['fov']
            else:
                # Only numpy array, so add all default values
                dat = {'data': dat, 'cmap': self.cmap[i], 'fov': self.fov[i]    }
                data[i] = dat

        for i, dat in enumerate(data):
            if len(dat['data'].shape) != 2:
                raise ValueError("Numpy array in data position "+str(i)+" is not 2D")

        if index:
            if index < 0 or index >= self.naxes:
                raise ValueError("index must be within that number of axes in the plot_panel")
            self.data[index] = data[0]
        else:
            if len(data) != self.naxes:
                raise ValueError("data must be a list with naxes number of items")
            self.data = data


    def update(self, index=None, no_draw=False):
        """
        Convenience function that runs through all the typical steps needed
        to refresh the screen after a set_data().

        The set_scale option is typically used only once to start set the
        bounding box to reasonable bounds for when a zoom box zooms back
        out.

        """
        self.update_images(index=index)
        if not no_draw:
            self.canvas.draw_idle()


    def update_images(self, index=None, force_bounds=False):
        """ Sets the data from the image numpy arrays into the axes. """

        indices = self.parse_indices(index)
        for i in indices:
            axes = self.all_axes[i]

            d = self.data[i]
            data = d['data'].copy()
            cmap = d['cmap']

            # Explicit set origin here so the user rcParams value is not used.
            axes.cla()
            self.imageid[i] = axes.imshow(data, cmap=cmap, aspect='equal', origin='upper')
            if self.vertOn:
                self.imageid[i].axes.add_line(self.toolbar.vlines[i])
            if self.horizOn:
                self.imageid[i].axes.add_line(self.toolbar.hlines[i])


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
                        raise ValueError("index in list outside naxes range")
                else:
                    raise ValueError("too many index entries")
            else:
                if index < self.naxes:
                    indices = [index,]
                else:
                    raise ValueError("scalar index outside naxes range")

        return indices

    # =======================================================
    #
    #           User Accessible Display Functions
    #
    # =======================================================

    def set_color(self, rgbtuple=None):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
        clr = [c / 255. for c in rgbtuple]
        self.figure.set_facecolor(clr)
        self.figure.set_edgecolor(clr)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))

    def set_axes_color(self, rgbtuple=None):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
        clr = [c / 255. for c in rgbtuple]
        for axis in self.all_axes:
            axis.spines['bottom'].set_color(clr)
            axis.spines['top'].set_color(clr)
            axis.spines['right'].set_color(clr)
            axis.spines['left'].set_color(clr)



# Test Code ------------------------------------------------------------------

class MyFrame(wx.Frame):
    def __init__(self, title="New Title Please", size=(350, 200)):

        wx.Frame.__init__(self, None, title=title, pos=(150, 150), size=size)
        self.statusbar = self.CreateStatusBar(4, 0)
        self.top = self

        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.nb = wx.Notebook(self, -1, style=wx.BK_BOTTOM)

        panel0 = wx.Panel(self.nb, -1)
        panel1 = wx.Panel(panel0, -1)
        panel2 = wx.Panel(panel0, -1)

        label_11 = wx.StaticText(panel1, wx.ID_ANY, "Source :")
        self.TextData = wx.TextCtrl(panel1, wx.ID_ANY, "", style=wx.TE_READONLY)
        label_1_copy = wx.StaticText(panel1, wx.ID_ANY, "  Voxel - X :")
        self.SpinX = wx.SpinCtrl(panel1, wx.ID_ANY, "1", min=1, max=32, style=wx.SP_ARROW_KEYS | wx.SP_WRAP | wx.TE_PROCESS_ENTER)
        self.SpinX.SetMinSize((60, -1))
        label_2 = wx.StaticText(panel1, wx.ID_ANY, " Y :")
        self.SpinY = wx.SpinCtrl(panel1, wx.ID_ANY, "1", min=1, max=32, style=wx.SP_ARROW_KEYS | wx.SP_WRAP | wx.TE_PROCESS_ENTER)
        self.SpinY.SetMinSize((60, -1))
        self.label_3 = wx.StaticText(panel1, wx.ID_ANY, " Z :")
        self.SpinZ = wx.SpinCtrl(panel1, wx.ID_ANY, "1", min=1, max=16, style=wx.SP_ARROW_KEYS | wx.SP_WRAP | wx.TE_PROCESS_ENTER)
        self.SpinZ.SetMinSize((60, -1))
        label_4 = wx.StaticText(panel1, wx.ID_ANY, " Scale:")
        label_4.SetMinSize((42, 21))
        self.FloatScale = wx.SpinCtrlDouble(panel1, wx.ID_ANY, initial=0.0, min=0.0, max=100.0, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        self.FloatScale.SetDigits(3)
        self.FloatScale.SetMinSize((100, -1))


        sizer_30 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_30.Add(label_11, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        sizer_30.Add(self.TextData, 3, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 3)
        sizer_30.Add((30, 20), 0, wx.EXPAND, 0)
        sizer_30.Add(label_1_copy, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        sizer_30.Add(self.SpinX, 0, wx.EXPAND, 0)
        sizer_30.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)
        sizer_30.Add(self.SpinY, 0, wx.EXPAND, 0)
        sizer_30.Add(self.label_3, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)
        sizer_30.Add(self.SpinZ, 0, wx.EXPAND, 0)
        sizer_30.Add(label_4, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)
        sizer_30.Add(self.FloatScale, 0, wx.EXPAND, 0)

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(sizer_30, 0, wx.ALL | wx.EXPAND, 4)
        panel1.SetSizer(sizer_2)


        data1 = {'data': self.dist(32), 'fov': 240.0}
        data2 = {'data': self.dist(128), 'fov': 240.0, 'cmap': cm.hsv}
        data = [data1, data2]

        # tab_dataset = self here for this example only
        self.image = ImagePaneMri(panel2, self, self,
                                  naxes=2, data=data, layout='vertical',
                                  cmap=cm.gray, color=None, bgcolor="#ffffff",
                                  vertOn=True, horizOn=True,
                                  lcolor='gold', lw=0.5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.image, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        panel2.SetSizer(sizer)
        self.image.Fit()

        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(panel1, 0, wx.ALL | wx.EXPAND, 4)
        sizer_1.Add(panel2, 1, wx.ALL | wx.EXPAND, 4)
        panel0.SetSizer(sizer_1)
        self.nb.AddPage(panel0, "One")

    @property
    def voxel(self):
        return [self.SpinX.GetValue() - 1,
                self.SpinY.GetValue() - 1,
                self.SpinZ.GetValue() - 1]

    def on_voxel_change(self):
        print('on_voxel_change called in MyFrame...')

    def on_splitter(self, event):
        print('on_splitter called in MyFrame...')

    def on_close(self, event):
        dlg = wx.MessageDialog(self,
                               "Do you really want to close this application?",
                               "Confirm Exit", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            self.Destroy()

    def dist(self, n, m=None):
        """ a rectangular array where each pixel = euclidian distance from the origin. """
        n1 = n
        m1 = m if m else n
        x = np.array([val ** 2 if val < (n1 - val) else (n1 - val) ** 2 for val in np.arange(n1)])
        a = np.ndarray((n1, m1), float)  # Make array
        for i in range(int((m1 / 2) + 1)):  # Row loop
            a[i, :] = np.sqrt(x + i ** 2.0)  # Euclidian distance
            if i != 0: a[m1 - i, :] = a[i, :]  # Symmetrical
        return a


if __name__ == '__main__':
    app = wx.App(False)
    frame = MyFrame(title='WxPython and Matplotlib bjs', size=(600, 600))
    frame.Show()
    app.MainLoop()