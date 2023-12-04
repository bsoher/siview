#!/usr/bin/env python
"""
Separating out NavigationToolbar3Wx from image_panel_toolbar.py

This will allow me to start from NavigationToolbar2 code and add without
having to monkey patch.

Brian J. Soher, Duke University, 2023

"""
# Python modules
import time
import pathlib
from enum import Enum, IntEnum
from contextlib import contextmanager
from collections import namedtuple
from weakref import WeakKeyDictionary

# third party modules
import wx
import numpy as np
import matplotlib as mpl
import matplotlib.cm as cm
from matplotlib import (backend_tools as tools, cbook)
from wx.lib.embeddedimage import PyEmbeddedImage


LEVMAX =  2048
LEVMIN = -2048
WIDMAX =  4096
WIDMIN =     1
WIDSTR =   255
LEVSTR =   128

#------------------------------------------------------------------------------
# NavToolbarMri
#
# This toolbar is specific to use in canvases that display MRI images.
#
#------------------------------------------------------------------------------

class MouseButton(IntEnum):
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    BACK = 8
    FORWARD = 9

class _Mode(str, Enum):
    NONE  = ""
    PAN   = "pan/zoom"
    ZOOM  = "zoom rect"
    LEVEL = 'width/level'

    def __str__(self):
        return self.value

    @property
    def _navigate_mode(self):
        return self.name if self is not _Mode.NONE else None


class NavToolbarMri(wx.ToolBar):
    """
    Based on NavigationToolbar2 in backend_bases.py
    - Base class for the navigation cursor, version 2.

    Backends must implement a canvas that handles connections for
    'button_press_event' and 'button_release_event'.  See
    :meth:`FigureCanvasBase.mpl_connect` for more information.

    They must also define

      :meth:`save_figure`
         save the current figure

      :meth:`draw_rubberband` (optional)
         draw the zoom to rect "rubberband" rectangle

      :meth:`set_history_buttons` (optional)
         you can change the history back / forward buttons to
         indicate disabled / enabled state.

    and override ``__init__`` to set up the toolbar -- without forgetting to
    call the base-class init.  Typically, ``__init__`` needs to set up toolbar
    buttons connected to the `home`, `back`, `forward`, `pan`, `zoom`, and
    `save_figure` methods and using standard icons in the "images" subdirectory
    of the data path.

    That's it, we'll do the rest!
    """
    # list of toolitems to add to the toolbar, format is:
    # (
    #   text,           # the text of the button (often not visible to users)
    #   tooltip_text,   # the tooltip shown on hover (where possible)
    #   image_file,     # name of the image for the button (without the extension)
    #   name_of_method, # name of the method in NavigationToolbar2 to call
    # )
    toolitems = (
        ('Home', 'Reset original view', 'nav3_home', 'home'),
        ('Back', 'Back to  previous view', 'nav3_back', 'back'),
        ('Forward', 'Forward to next view', 'nav3_forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'nav3_move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'nav3_zoom_to_rect', 'zoom'),
        ('Level','Set width/level with right mouse up/down', 'nav3_contrast', 'level'),
        ('Crosshairs', 'Track mouse movement with crossed lines', 'nav3_crosshair', 'crosshairs'),
        (None, None, None, None),
        ('Subplots', 'Configure subplots', 'nav3_subplots', 'configure_subplots'),
        ('Save', 'Save the figure', 'nav3_filesave', 'save_figure'),
      )
    
    
    def __init__(self,
                 canvas,
                 parent,
                 vertOn=False,
                 horizOn=False,
                 lcolor='gold',
                 lw=0.5,
                 style=wx.TB_BOTTOM ):

        wx.ToolBar.__init__(self, canvas.GetParent(), -1)

        # bjs - from backend_wx.py NavigationToolbar2Wx

        if 'wxMac' in wx.PlatformInfo:
            self.SetToolBitmapSize((24, 24))
        self.wx_ids = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.AddSeparator()
                continue

            bmp = nav3_catalog[image_file].GetBitmap()

            self.wx_ids[text] = wx.NewIdRef()
            if text in ['Pan', 'Level', 'Crosshairs']:
                self.AddCheckTool(self.wx_ids[text], ' ', bmp, shortHelp=text, longHelp=tooltip_text)
            elif text in ['Zoom', 'Subplots']:
                pass  # don't want this in my toolbar
                # NB. bjs - this is not tested
                # self.AddTool(self.wx_ids[text], bitmap=bmp, bmpDisabled=wx.NullBitmap, label=text, shortHelp=text, longHelp=tooltip_text, kind=(wx.ITEM_NORMAL))
            else:
                self.AddTool(self.wx_ids[text], bitmap=bmp, bmpDisabled=wx.NullBitmap, label=text, shortHelp=text, longHelp=tooltip_text)

            self.Bind(wx.EVT_TOOL, getattr(self, callback), id=self.wx_ids[text])

        self.Realize()

        # bjs - from backend_bases.py NavigationToolbar2

        self.canvas = canvas
        canvas.toolbar = self
        self._nav_stack = cbook.Stack()
        # This cursor will be set after the initial draw.
        self._last_cursor = tools.Cursors.POINTER

        self._id_press     = self.canvas.mpl_connect( 'button_press_event', self.zoom_pan_level_handler)
        self._id_release   = self.canvas.mpl_connect( 'button_release_event', self.zoom_pan_level_handler)
        self._id_drag      = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)
        self._id_ax_leave  = self.canvas.mpl_connect( 'axes_leave_event', self.leave)
        self._id_fig_leave = self.canvas.mpl_connect( 'figure_leave_event', self.leave)
        self._pan_info   = None
        self._zoom_info  = None
        self._level_info = None

        self.mode = _Mode.NONE  # a mode string for the status bar
        self.set_history_buttons()

        # bjs-start

        self.naxes = len(self.canvas.figure.get_axes())
        self.parent = parent
        self.statusbar = wx.GetApp().GetTopWindow().statusbar
        self.prevxy = [0,0]
        self.widmax = 4096
        self.widmin = 1
        self.levmax = 2048
        self.levmin = -2048
        self.nstep_cmap = 256.0   # number of levels in the cmap
        self.width = [float(WIDSTR) for a in range(self.naxes)]
        self.level = [float(LEVSTR) for a in range(self.naxes)]

        # TODO bjs - this setup fails if AxesImage is updated by imshow() with different cmap
        self.cmap_default = cm.gray
        self.cmap  = [None for a in range(self.naxes)]
        for i, ax in enumerate(self.canvas.figure.get_axes()):
            if ax.images:
                self.cmap[i] = ax.images[0].get_cmap()

        # set up control params for crosshair functionality
        self._crosshairs = False
        self.vertOn  = vertOn
        self.horizOn = horizOn
        self.vlines = []
        self.hlines = []
        if vertOn:  self.vlines = [ax.axvline(0, visible=False, color=lcolor, lw=lw)
                                   for ax in self.canvas.figure.get_axes()]
        if horizOn: self.hlines = [ax.axhline(0, visible=False, color=lcolor, lw=lw)
                                   for ax in self.canvas.figure.get_axes()]


    def home(self, *args):
        """
        Restore the original view.

        For convenience of being directly connected as a GUI callback, which
        often get passed additional parameters, this method accepts arbitrary
        parameters, but does not use them.
        """
        self._nav_stack.home()
        self.set_history_buttons()
        self._update_view()

    def back(self, *args):
        """
        Move back up the view lim stack.

        For convenience of being directly connected as a GUI callback, which
        often get passed additional parameters, this method accepts arbitrary
        parameters, but does not use them.
        """
        self._nav_stack.back()
        self.set_history_buttons()
        self._update_view()

    def forward(self, *args):
        """
        Move forward in the view lim stack.

        For convenience of being directly connected as a GUI callback, which
        often get passed additional parameters, this method accepts arbitrary
        parameters, but does not use them.
        """
        self._nav_stack.forward()
        self.set_history_buttons()
        self._update_view()

    def update(self):
        """Reset the Axes stack."""
        self._nav_stack.clear()
        self.set_history_buttons()

    def push_current(self):
        """Push the current view limits and position onto the stack."""
        self._nav_stack.push(
            WeakKeyDictionary(
                {ax: (ax._get_view(),
                      # Store both the original and modified positions.
                      (ax.get_position(True).frozen(),
                       ax.get_position().frozen()))
                 for ax in self.canvas.figure.axes}))
        self.set_history_buttons()


    def _update_view(self):
        """
        Update the viewlim and position from the view and position stack for
        each Axes.
        """
        nav_info = self._nav_stack()
        if nav_info is None:
            return
        # Retrieve all items at once to avoid any risk of GC deleting an Axes
        # while in the middle of the loop below.
        items = list(nav_info.items())
        for ax, (view, (pos_orig, pos_active)) in items:
            ax._set_view(view)
            # Restore both the original and modified positions
            ax._set_position(pos_orig, 'original')
            ax._set_position(pos_active, 'active')
        self.canvas.draw_idle()


    @contextmanager
    def _wait_cursor_for_draw_cm(self):
        """
        Set the cursor to a wait cursor when drawing the canvas.

        In order to avoid constantly changing the cursor when the canvas
        changes frequently, do nothing if this context was triggered during the
        last second.  (Optimally we'd prefer only setting the wait cursor if
        the *current* draw takes too long, but the current draw blocks the GUI
        thread).
        """
        self._draw_time, last_draw_time = (
            time.time(), getattr(self, "_draw_time", -np.inf))
        if self._draw_time - last_draw_time > 1:
            try:
                self.canvas.set_cursor(tools.Cursors.WAIT)
                yield
            finally:
                self.canvas.set_cursor(self._last_cursor)
        else:
            yield

    @staticmethod
    def _mouse_event_to_message(event):
        if event.inaxes and event.inaxes.get_navigate():
            try:
                s = event.inaxes.format_coord(event.xdata, event.ydata)
            except (ValueError, OverflowError):
                pass
            else:
                s = s.rstrip()
                artists = [a for a in event.inaxes._mouseover_set
                           if a.contains(event)[0] and a.get_visible()]
                if artists:
                    a = cbook._topmost_artist(artists)
                    if a is not event.inaxes.patch:
                        data = a.get_cursor_data(event)
                        if data is not None:
                            data_str = a.format_cursor_data(data).rstrip()
                            if data_str:
                                s = s + '\n' + data_str
                return s
        return ""

    def _update_buttons_checked(self):
        # from backend_wx.py - bjs update for Level
        if "Pan" in self.wx_ids:
            self.ToggleTool(self.wx_ids["Pan"], self.mode.name == "PAN")
        if "Zoom" in self.wx_ids:
            self.ToggleTool(self.wx_ids["Zoom"], self.mode.name == "ZOOM")
        if "Level" in self.wx_ids:
            self.ToggleTool(self.wx_ids["Level"], self.mode.name == "LEVEL")

    def leave(self, event):
        """ Turn off the xrosshairs as we move mouse outside axes or figure """
        for line in self.vlines+self.hlines: line.set_visible(False)
        self.canvas.draw_idle()

    def crosshairs(self, *args):
        """
        Toggle the crosshairs tool to show vertical and
        horizontal lines that track the mouse motion, or not.

        """
        if self._crosshairs:
            self._crosshairs = False
            if 'Crosshairs' in list(self.wx_ids.keys()):
                self.ToggleTool(self.wx_ids['Crosshairs'], False)
        else:
            self._crosshairs = True
            if 'Crosshairs' in list(self.wx_ids.keys()):
                self.ToggleTool(self.wx_ids['Crosshairs'], True)

    def zoom_pan_level_handler(self, event):
        if self.mode == _Mode.PAN:
            if event.name == "button_press_event":
                self.press_pan(event)
            elif event.name == "button_release_event":
                self.release_pan(event)
        if self.mode == _Mode.ZOOM:
            if event.name == "button_press_event":
                self.press_zoom(event)
            elif event.name == "button_release_event":
                self.release_zoom(event)
        if self.mode == _Mode.LEVEL:
            if event.name == "button_press_event":
                self.press_level(event)
            elif event.name == "button_release_event":
                self.release_level(event)
        if self.mode == _Mode.NONE:
            if event.name == "button_press_event":
                self.press_local(event)
            elif event.name == "button_release_event":
                self.release_local(event)

    def pan(self, *args):
        """
        Toggle the pan/zoom tool.

        Pan with left button, zoom with right.
        """
        if not self.canvas.widgetlock.available(self):
            return
        if self.mode == _Mode.PAN:
            self.mode = _Mode.NONE
            self.canvas.widgetlock.release(self)
        else:
            self.mode = _Mode.PAN
            self.canvas.widgetlock(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self.mode._navigate_mode)
        self._update_buttons_checked()

    _PanInfo = namedtuple("_PanInfo", "button axes cid")

    def press_pan(self, event):
        """Callback for mouse button press in pan/zoom mode."""
        if (event.button not in [MouseButton.LEFT, MouseButton.RIGHT]
                or event.x is None or event.y is None):
            return
        axes = [(i,a) for i,a in enumerate(self.canvas.figure.get_axes())
                if a.in_axes(event) and a.get_navigate() and a.can_pan()]
        if not axes:
            return
        if self._nav_stack() is None:
            self.push_current()  # set the home button to this view
        for ax in axes:
            ax[1].start_pan(event.x, event.y, event.button)
        self.canvas.mpl_disconnect(self._id_drag)
        id_drag = self.canvas.mpl_connect("motion_notify_event", self.drag_pan)
        self._pan_info = self._PanInfo( button=event.button, axes=axes, cid=id_drag)

        for line in self.vlines + self.hlines:
            line.set_visible(False)
        self.canvas.draw_idle()

    def drag_pan(self, event):
        """Callback for dragging in pan/zoom mode."""
        for ax in self._pan_info.axes:
            # Using the recorded button at the press is safer than the current
            # button, as multiple buttons can get pressed during motion.
            ax[1].drag_pan(self._pan_info.button, event.key, event.x, event.y)
        self.canvas.draw_idle()

        xloc, yloc, xpos, ypos = self.get_bounded_xyloc(event)
        iplot = self._pan_info.axes[0][0]
        self.parent.on_panzoom_motion(xloc, yloc, xpos, ypos, iplot)

    def release_pan(self, event):
        """Callback for mouse button release in pan/zoom mode."""
        if self._pan_info is None:
            return
        self.canvas.mpl_disconnect(self._pan_info.cid)
        self._id_drag = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)
        for ax in self._pan_info.axes:
            ax[1].end_pan()
        self.canvas.draw_idle()
        self._pan_info = None
        self.push_current()

        xloc, yloc, xpos, ypos = self.get_bounded_xyloc(event)
        self.parent.on_panzoom_release(xloc, yloc, xpos, ypos)

    def zoom(self, *args):
        if not self.canvas.widgetlock.available(self):
            return
        """Toggle zoom to rect mode."""
        if self.mode == _Mode.ZOOM:
            self.mode = _Mode.NONE
            self.canvas.widgetlock.release(self)
        else:
            self.mode = _Mode.ZOOM
            self.canvas.widgetlock(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self.mode._navigate_mode)
        self._update_buttons_checked()

    _ZoomInfo = namedtuple("_ZoomInfo", "direction start_xy axes cid cbar")

    def press_zoom(self, event):
        """Callback for mouse button press in zoom to rect mode."""
        if (event.button not in [MouseButton.LEFT, MouseButton.RIGHT]
                or event.x is None or event.y is None):
            return
        axes = [a for a in self.canvas.figure.get_axes()
                if a.in_axes(event) and a.get_navigate() and a.can_zoom()]
        # NB. bjs - too complex to add (i, a) info at this point for zoom,
        #  can look at it again in future when more time to plan
        if not axes:
            return
        if self._nav_stack() is None:
            self.push_current()  # set the home button to this view
        id_zoom = self.canvas.mpl_connect( "motion_notify_event", self.drag_zoom)
        # A colorbar is one-dimensional, so we extend the zoom rectangle out
        # to the edge of the Axes bbox in the other dimension. To do that we
        # store the orientation of the colorbar for later.
        if hasattr(axes[0], "_colorbar"):
            cbar = axes[0]._colorbar.orientation
        else:
            cbar = None
        self._zoom_info = self._ZoomInfo(
            direction="in" if event.button == 1 else "out",
            start_xy=(event.x, event.y), axes=axes, cid=id_zoom, cbar=cbar)

        for line in self.vlines + self.hlines:
            line.set_visible(False)
        self.canvas.draw_idle()

    def drag_zoom(self, event):
        """Callback for dragging in zoom mode."""
        start_xy = self._zoom_info.start_xy
        ax = self._zoom_info.axes[0]
        (x1, y1), (x2, y2) = np.clip(
            [start_xy, [event.x, event.y]], ax.bbox.min, ax.bbox.max)
        key = event.key
        # Force the key on colorbars to extend the short-axis bbox
        if self._zoom_info.cbar == "horizontal":
            key = "x"
        elif self._zoom_info.cbar == "vertical":
            key = "y"
        if key == "x":
            y1, y2 = ax.bbox.intervaly
        elif key == "y":
            x1, x2 = ax.bbox.intervalx

        self.draw_rubberband(event, x1, y1, x2, y2)
        # NB. bjs - no parent event call here, yet ...

    def release_zoom(self, event):
        """Callback for mouse button release in zoom to rect mode."""
        if self._zoom_info is None:
            return

        # We don't check the event button here, so that zooms can be cancelled
        # by (pressing and) releasing another mouse button.
        self.canvas.mpl_disconnect(self._zoom_info.cid)
        self.remove_rubberband()

        start_x, start_y = self._zoom_info.start_xy
        key = event.key
        # Force the key on colorbars to ignore the zoom-cancel on the
        # short-axis side
        if self._zoom_info.cbar == "horizontal":
            key = "x"
        elif self._zoom_info.cbar == "vertical":
            key = "y"
        # Ignore single clicks: 5 pixels is a threshold that allows the user to
        # "cancel" a zoom action by zooming by less than 5 pixels.
        if ((abs(event.x - start_x) < 5 and key != "y") or
                (abs(event.y - start_y) < 5 and key != "x")):
            self.canvas.draw_idle()
            self._zoom_info = None
            return

        for i, ax in enumerate(self._zoom_info.axes):
            # Detect whether this Axes is twinned with an earlier Axes in the
            # list of zoomed Axes, to avoid double zooming.
            twinx = any(ax.get_shared_x_axes().joined(ax, prev)
                        for prev in self._zoom_info.axes[:i])
            twiny = any(ax.get_shared_y_axes().joined(ax, prev)
                        for prev in self._zoom_info.axes[:i])
            ax._set_view_from_bbox(
                (start_x, start_y, event.x, event.y),
                self._zoom_info.direction, key, twinx, twiny)

        # legacy code from NavigationToolbar2Wx
        try:
            del self.lastrect
        except AttributeError:
            pass

        self.canvas.draw_idle()
        self._zoom_info = None
        self.push_current()
        # NB. bjs - no parent event call here, yet ...


    def level(self, *args):
        """
        Toggle the width/level tool.

        Change image with right button up/down left/right
        """
        if not self.canvas.widgetlock.available(self):
            return
        if self.mode == _Mode.LEVEL:
            self.mode = _Mode.NONE
            self.canvas.widgetlock.release(self)
        else:
            self.mode = _Mode.LEVEL
            self.canvas.widgetlock(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self.mode._navigate_mode)
        self._update_buttons_checked()

    _LevelInfo = namedtuple("_LevelInfo", "button axes cid")

    def press_level(self, event):
        """Callback for mouse button press in width/level mode."""

        if (event.button not in [MouseButton.RIGHT,]
                or event.x is None or event.y is None):
            return
        axes = [(i,a) for i,a in enumerate(self.canvas.figure.get_axes())
                if a.in_axes(event) and a.get_navigate()]
        if not axes:
            return

        if self._nav_stack() is None:
            self.push_current()  # set the home button to this view

        self._xypress = []
        for item in axes:
            self._xypress.append([item[1], item[0], event.x, event.y])

        self.canvas.mpl_disconnect(self._id_drag)
        id_drag = self.canvas.mpl_connect("motion_notify_event", self.drag_level)
        self._level_info = self._LevelInfo( button=event.button, axes=axes, cid=id_drag)
        self.prevxy = event.x, event.y

        for line in self.vlines + self.hlines:
            line.set_visible(False)
        self.canvas.draw_idle()

        xloc, yloc, xpos, ypos = self.get_bounded_xyloc(event)
        self.parent.on_level_press(xloc, yloc, xpos, ypos, axes[0][0])

    def drag_level(self, event):
        """Callback for dragging in width/level mode."""

        xprev, yprev = self.prevxy
        xdelt = int((event.x - xprev))
        ydelt = int((event.y - yprev))

        for item in self._level_info.axes:
            indx, ax = item

            if abs(ydelt) >= abs(xdelt):
                self.level[indx] = max(LEVMIN, min(LEVMAX, self.level[indx]+ydelt))
            else:
                self.width[indx] = max(WIDMIN, min(WIDMAX, self.width[indx]+xdelt))

            wid = self.width[indx]
            lev = self.level[indx]

            npts = self.levmax - self.levmin    # typical 8192
            nstep = float(self.nstep_cmap)
            cmarr = (np.arange(npts) + self.levmin) * (1.0/wid) + 0.5  # .5 is ctr of cmap range
            cmarr = np.roll(cmarr, int(lev - LEVSTR))
            cmarr = cmarr[int((npts-nstep)*0.5):int((npts+nstep)*0.5)]
            cmarr = np.clip(cmarr, 0.0, 1.0)

            cmap_base = self.cmap[indx] if self.cmap[indx] is not None else self.cmap_default
            ax.images[0].set(cmap=ListedColormap(cmap_base(cmarr)))

            self.prevxy = [event.x, event.y]

        self.canvas.draw_idle()

        xloc, yloc, xpos, ypos = self.get_bounded_xyloc(event)
        iplot = self._level_info.axes[0][0]
        self.parent.on_level_motion(xloc, yloc, xpos, ypos, iplot, wid, lev)

    def release_level(self, event):
        """Callback for mouse button release in width/level mode."""
        if self._level_info is None:
            return
        if self._level_info.button != 3:
            return
        self.canvas.mpl_disconnect(self._level_info.cid)
        self._id_drag = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)

        self.canvas.draw_idle()
        self._level_info = None

        xloc, yloc, xpos, ypos = self.get_bounded_xyloc(event)
        self.parent.on_level_release(xloc, yloc, xpos, ypos)

    def press_local(self, event):
        # no toggle buttons on, but maybe we want to show crosshairs
        self.parent.select_is_held = True
        if self._crosshairs:
            for line in self.vlines + self.hlines:
                line.set_visible(True)
        self.canvas.draw_idle()

    def release_local(self, event):
        # no toggle buttons on
        self.parent.select_is_held = False
        xloc, yloc, xpos, ypos = self.get_bounded_xyloc(event)
        # find out what plot we released in
        iplot = self.get_plot_index(event)
        self.parent.on_select(xloc, yloc, xpos, ypos, iplot)

    def mouse_move(self, event):

        self._update_cursor(event)
        if not event.inaxes:
            return

        xloc, yloc, xpos, ypos = self.get_bounded_xyloc(event)
        iplot = self.get_plot_index(event)

        if iplot is not None:
            self.parent.on_motion(xloc, yloc, xpos, ypos, iplot)

            axes = self.canvas.figure.get_axes()

            if self._crosshairs and self.vertOn:
                for i, line in enumerate(self.vlines):
                    x0, y0, x1, y1 = axes[i].dataLim.bounds
                    fov = self.parent.fov[i] if hasattr(self.parent, 'fov') else 1.0
                    xtmp = x1 * xpos / fov
                    line.set_xdata((xtmp, xtmp))
                    line.set_visible(True)
            if self._crosshairs and self.horizOn:
                for i, line in enumerate(self.hlines):
                    x0, y0, x1, y1 = axes[i].dataLim.bounds
                    fov = self.parent.fov[i] if hasattr(self.parent, 'fov') else 1.0
                    ytmp = y1 * ypos / fov
                    line.set_ydata((ytmp, ytmp))
                    line.set_visible(True)
            self.canvas.draw_idle()

    def get_bounded_xyloc(self, event):
        """
        Remember, imshow defaults to the center of each voxel being the integer
        x,y location. So far left is -0.5 so that center of first voxel is 0.0
        and similarly far right is 23.5 (-0.5 start + 24 total points).

        Here we want to return a value between 0 and 23.99999 that can be int()
        to 0-23 for reporting voxel number and data values.

        """
        if not event.inaxes:
            return 0,0,0,0

        xloc, yloc = event.xdata, event.ydata
        
        # bound these values to be inside the size of the image.
        # - a pan event could yield negative locations.
        x0, y0, x1, y1 = event.inaxes.dataLim.bounds

        xloc = xloc+0.5
        yloc = yloc+0.5
        xloc = max(0, min(x1*0.99999, xloc))
        yloc = max(0, min(y1*0.99999, yloc))

        iplot = self.get_plot_index(event)

        xfov = self.parent.fov[iplot] if hasattr(self.parent, 'fov') else 1.0
        yfov = self.parent.fov[iplot] if hasattr(self.parent, 'fov') else 1.0
        xpos = xfov * (xloc / x1)
        ypos = yfov * (yloc / y1)

        return xloc,yloc,xpos,ypos

    def get_plot_index(self, event):
        for i, axes in enumerate(self.canvas.figure.get_axes()):
            if axes == event.inaxes:
                return i
        return None

    def get_canvas(self, frame, fig):
        # saw this in NavigationToolbar2WxAgg, so included here
        return FigureCanvasWxAgg(frame, -1, fig)

    def _update_cursor(self, event):
        """
        Update the cursor after a mouse move event or a tool (de)activation.
        """
        if self.mode and event.inaxes and event.inaxes.get_navigate():
            if (self.mode == _Mode.ZOOM and self._last_cursor != tools.Cursors.SELECT_REGION):
                self.canvas.set_cursor(tools.Cursors.SELECT_REGION)
                self._last_cursor = tools.Cursors.SELECT_REGION
            elif (self.mode == _Mode.PAN and self._last_cursor != tools.Cursors.MOVE):
                self.canvas.set_cursor(tools.Cursors.MOVE)
                self._last_cursor = tools.Cursors.MOVE
            elif (self.mode == _Mode.LEVEL and self._last_cursor != tools.Cursors.SELECT_REGION):
                self.canvas.set_cursor(tools.Cursors.SELECT_REGION)
                self._last_cursor = tools.Cursors.SELECT_REGION
        elif self._last_cursor != tools.Cursors.POINTER:
            self.canvas.set_cursor(tools.Cursors.POINTER)
            self._last_cursor = tools.Cursors.POINTER


    #-------------------------------------------------------

    def set_status_bar(self, statusbar):
        self.statusbar = statusbar

    def set_history_buttons(self):
        # from backend_wx.py
        can_backward = self._nav_stack._pos > 0
        can_forward = self._nav_stack._pos < len(self._nav_stack._elements) - 1
        if 'Back' in self.wx_ids:
            self.EnableTool(self.wx_ids['Back'], can_backward)
        if 'Forward' in self.wx_ids:
            self.EnableTool(self.wx_ids['Forward'], can_forward)

    def draw_rubberband(self, event, x0, y0, x1, y1):
        """
        Draw a rectangle rubberband to indicate zoom limits.
        Note that it is not guaranteed that ``x0 <= x1`` and ``y0 <= y1``.
        """
        # from backend_wx.py
        height = self.canvas.figure.bbox.height
        self.canvas._rubberband_rect = (x0, height - y0, x1, height - y1)
        self.canvas.Refresh()

    def remove_rubberband(self):
        # from backend_wx.py
        self.canvas._rubberband_rect = None
        self.canvas.Refresh()

    def save_figure(self, *args):
        # from backend_wx.py
        #
        # Fetch the required filename and file type.
        filetypes, exts, filter_index = self.canvas._get_imagesave_wildcards()
        default_file = self.canvas.get_default_filename()
        dialog = wx.FileDialog(
            self.canvas.GetParent(), "Save to file",
            mpl.rcParams["savefig.directory"], default_file, filetypes,
            wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        dialog.SetFilterIndex(filter_index)
        if dialog.ShowModal() == wx.ID_OK:
            path = pathlib.Path(dialog.GetPath())
#            _log.debug('%s - Save file path: %s', type(self), path)
            fmt = exts[dialog.GetFilterIndex()]
            ext = path.suffix[1:]
            if ext in self.canvas.get_supported_filetypes() and fmt != ext:
                pass
                # # looks like they forgot to set the image type drop
                # # down, going with the extension.
                # _log.warning('extension %s did not match the selected '
                #              'image type %s; going with %s',
                #              ext, fmt, ext)
                fmt = ext
            # Save dir for next time, unless empty str (which means use cwd).
            if mpl.rcParams["savefig.directory"]:
                mpl.rcParams["savefig.directory"] = str(path.parent)
            try:
                self.canvas.figure.savefig(path, format=fmt)
            except Exception as e:
                dialog = wx.MessageDialog(
                    parent=self.canvas.GetParent(), message=str(e),
                    caption='Matplotlib error')
                dialog.ShowModal()
                dialog.Destroy()

    def configure_subplots(self, *args):
        if hasattr(self, "subplot_tool"):
            self.subplot_tool.figure.canvas.manager.show()
            return
        # This import needs to happen here due to circular imports.
        from matplotlib.figure import Figure
        with mpl.rc_context({"toolbar": "none"}):  # No navbar for the toolfig.
            manager = type(self.canvas).new_manager(Figure(figsize=(6, 3)), -1)
        manager.set_window_title("Subplot configuration tool")
        tool_fig = manager.canvas.figure
        tool_fig.subplots_adjust(top=0.9)
        self.subplot_tool = widgets.SubplotTool(self.canvas.figure, tool_fig)
        cid = self.canvas.mpl_connect( "close_event", lambda e: manager.destroy())

        def on_tool_fig_close(e):
            self.canvas.mpl_disconnect(cid)
            del self.subplot_tool

        tool_fig.canvas.mpl_connect("close_event", on_tool_fig_close)
        manager.show()
        return self.subplot_tool





# ***************** Embed Icon Catalog Starts Here *******************

nav3_catalog = {}
nav3_index = []


#----------------------------------------------------------------------
nav3_crosshair = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAAIBJREFUWEftlVEKgCAQBfcgXau/TtB9OkF/XbJ8sBsimlToFryB"
    "+RJxQGXl70yqG5vqBgMYwAAGrGpXhuBYEGvNwUF7Qaw1xwJSXgVgotmDuhL3XQtYgum+nHPw"
    "xD3gDrWA5lhAzi4B7t8wBvcN3bAH5QYDGMAABmCiPZ5qH0DkAEnpVB1zVLSlAAAAAElFTkSu"
    "QmCC")
nav3_index.append('nav3_crosshair')
nav3_catalog['nav3_crosshair'] = nav3_crosshair
getnav3_crosshairData = nav3_crosshair.GetData
getnav3_crosshairImage = nav3_crosshair.GetImage
getnav3_crosshairBitmap = nav3_crosshair.GetBitmap
getnav3_crosshairIcon = nav3_crosshair.GetIcon


#----------------------------------------------------------------------
nav3_back = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAAmNJREFUSEutlbuL1FAUxhPB3dUBFRlmnC1URIvNYx55zmtzkgXZ"
    "cWYndq4gCGJtY+VfYCNoZ2FhY2lloY0gdlY2i1hspwhi4WPEKVZ30e9mb+KdMUrGzcCPJOee"
    "831z7wknkuGFBdOsy4ZRk9nVcYzoGmNZDdnwhgWTQhP0warphaqxPNgf1zUataTOsn7XSuxn"
    "0vl1i4bXfL81z1lg1y5RAfHLEHwGvoOfU3wFDy1aW9mtaya1DKLmXKlUigwuInEHYleCoLnA"
    "sGmtg9grLpSFxw6dOxnXM2AwXy6XEwOW9AMmF8BV3G/x2Cy8xx9riwbiDuIkJrwjPM/KZ5sG"
    "5t92kBebLTp7dC8GY/AWfBFiE1gU3mIGlUols8E2iu7jjLvLvldgR+AH7QM4DhXxm1gfTeWP"
    "0fRK1h18wKvox81Lw6H+aeS9FOtgfD2rwRsInEkTFnFptYTc10Ld02KxmPmINrHlE2nCIjhC"
    "F7nbvOZTvdOXZ2nyhku9xTRhEeQ9imswhg7DIKzjvG6DOxx2Pw1fG15KExVhObEBZtai5DiW"
    "HASt1OT/wab+krCDIzAwczVAs8vcYFTvDmTJtvM1wMtwihs8j17TvI8IPRgyA/TsRjTsXDdv"
    "g/AeDLbQi+PcwM7NgH0TIP4NJneTYZeXAWbUQYg/Ae/Q6GPJsMujB21/5RCEH4Ax5pbHYsIO"
    "9mYAwR6EN8CI3cfxxIDtgCj6SPMP9yT/WvOozUbDR/ACo1ubWPOac9GwYz9N06RarSrpui4p"
    "ylL0HMNi1ar+x5qu714xDkpGp7dPURRJVdUkrmkqlCXpF1KpYNTIER0eAAAAAElFTkSuQmCC")
nav3_index.append('nav3_back')
nav3_catalog['nav3_back'] = nav3_back
getnav3_backData = nav3_back.GetData
getnav3_backImage = nav3_back.GetImage
getnav3_backBitmap = nav3_back.GetBitmap
getnav3_backIcon = nav3_back.GetIcon

#----------------------------------------------------------------------
nav3_contrast = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAASFJREFUSEvNlUEOgjAQRYG1J2GnNzDs4AZuPYbn4TBwCYgegZ3B"
    "6jzTEpHSgrHGl/yElOlMOzNto38gEe1ER9FJi2/G+PcxGxHOLqL7jM4ibLBdxV5kddz3vWqa"
    "RpVlqfI8v8VxzDi2zFnEQXQVTZyjd6qqUmmaKvnHHOY6YRWzzpGNrutUlmUmyOxOyKMr30/N"
    "QRC9E3xYa0KxrE5f5aKua5UkCXb4GkG7eVePfBRFwS7orlEL09NWh+/yQXdp261ogIMzcWaT"
    "j7ZtTQB8DizKP/LBOdG2ozp8M4CxHQUInqLgRQ7eprCoDi5cBw2CXxUQ9LIzrL2ub2uuawOr"
    "sKbrGw+OgTxSLDpiEkjr4yfzFdqNnubg4AzxzdikFX9MFD0Aw8HVrGb5SeoAAAAASUVORK5C"
    "YII=")
nav3_index.append('nav3_contrast')
nav3_catalog['nav3_contrast'] = nav3_contrast
getnav3_contrastData = nav3_contrast.GetData
getnav3_contrastImage = nav3_contrast.GetImage
getnav3_contrastBitmap = nav3_contrast.GetBitmap
getnav3_contrastIcon = nav3_contrast.GetIcon

#----------------------------------------------------------------------
nav3_filesave = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlw"
    "SFlzAAACXwAAAl8BvoUoWgAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoA"
    "AAPeSURBVEiJtVZNa11VFF17n3OTlzRNk7ZobasUpRRttShNxCIIFhT8AB1YodiBTpyIHzMR"
    "q1J/geBAcFhURHGig86EOChKBlVLW8W2Vhqr+Whi09j3cvfey8F9X0mboKgHDufec89be6+1"
    "1+Y8IYn/c2QAWHvwjf0A7iKoAtlMoIpKEGA0z7JrxrJ3AqAAQfIHACGqR+ePHD4vA88ceofk"
    "bnrUBRx66cqXI7t2rAEJdJETMkAKQKK9TVbnUKX09bnA+3L3rABSDPTPp6J4KAMY3T2QdPvG"
    "Dbd8cnriYn//YAyuu1GqABSKACQBAcFqv8UHrIIKwCBqE9PcKpDHR3b2fTF+Ok2pvpBB9uzc"
    "csPwy/sf3vbpq+/OzD/x4kJt123m5lqaq5mJmambS+mubqYWgfCAh1erBzwM4/WzMjxxMb9y"
    "4NHasZNnbdIxnAnI5yfO/fzVyffmPOVQCMJD3F3cHWcuTqVfp+cSSSFDEY6ggBFNGR0ksWlo"
    "gCrEd5OXr+549s06c4HejeuRAchc6NVZZ6ki64UU8xALiofL2Pj3PT9+eyK3ZGlVv1WIVkVG"
    "9464CoKqNClCVBUAM0hhsACZqJJFpJm9SXjIU/v2NsoHRkorXctwCXdEVLJEGDwC4YSAmDh1"
    "QSBVsbptqmQUIBOILAxxN3F3eLh8eHSsdvL4idR2U9tYHRYAcN/9e0wFAQi6PjCDEAQLkkkU"
    "BURb+ouby77RO8t77rg1IiDBAD0QjGYNAhFBBjDYV3Dm/HRlqe5Gq6zHgqSSyH82GnrpSp1m"
    "puEuOSUZXtPPIFlJ45UsJFpyhQcW3WFBqfqtYtuSSBhRgNQorfxo7PgCSAkyAdQIauX3TlZs"
    "NllnqeQKEGC785s1IIRkBqkIw++TM7MkMhiZwYzlnP/hyAAFEQUJBZhIJgQT+e/BwWaRSWYS"
    "ClLBNvh/MjKBVh8oQQWhAJDCVSL+HgMBLBV+zWan0aLAMjm2S33w3j23a73eEGssggLknEmy"
    "ck7X/OnML3oqrZ++LoMm8DWZ9vb2yGOPPMiPP/gsfXNsPAHAweeeLrfcvDmsLGFmMDOUZYnJ"
    "S3OBhevkD1BXY27uYHRcZ+ZwM7g7zBzWfMYqt+KqAdwM0fXjpcDWfsbK+CsHEAHNDIyuAOZL"
    "gN2tYrlKBBWVYkUG7oiuxqwYdIDNDL4CA1FVCBpZVN+qrVv7dv2P+aXeJ8TMsHnrJpq5iwJ9"
    "/TV2A7ckk/a9X5U2FYX2Dq09rykdEpIYOPD6a4x4nqQ1T+Kmy1MbBntSDrK6kpvrskmSsthY"
    "xG+btk1ApPp3oXpBU3py/sjhhb8AKRQO9CWsy6YAAAAASUVORK5CYII=")
nav3_index.append('nav3_filesave')
nav3_catalog['nav3_filesave'] = nav3_filesave
getnav3_filesaveData = nav3_filesave.GetData
getnav3_filesaveImage = nav3_filesave.GetImage
getnav3_filesaveBitmap = nav3_filesave.GetBitmap
getnav3_filesaveIcon = nav3_filesave.GetIcon

#----------------------------------------------------------------------
nav3_forward = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAAp9JREFUSEutlruLE0Ecx2cFvWhARUJiLFREi8vmua88LrezOZCL"
    "yWXtVBAEsbax8i+wEbSzsLCxtLLQRhA7K5tDLOwUQSx8nGhxeqLf32QmmVtHTRYDH7Lze313"
    "5rf5bRh9XLduEZ43/g4Cx2o0apbj1MTaWR7udMPYdnm8CgbAdcJR1vMawq+gPBGv8sI4y/L5"
    "POO8tSuK2guSTBS1xLXH11ZQ7B74DH4m+AYee3x0oct5dpo7rgP7ZZefPssKhQIJLPR6rYwi"
    "4KeOIvmBVuxfPPf52pLKR/GLsP2AwDm1g4kAAjtwvtWSZ2UThS+BM7j+PrZBQN+Bz4cuHB9l"
    "Qhpw1/HmdK0JtPnJAzC+nDr/BxAoFotCwOPxdXOQ4BN4Db5qthmQO0BTizAkkzcgeg3HZke9"
    "zm46wuUozKJHXdjvwL+ViDcgBZBwJeF8FvDBcdV4E3iEI8S9S+QlgEAul2NYPNIcL5p8NW8q"
    "qoMbOIHYV1qeAQjUlwYWFh+kcQtH0DQV1MGRHkHsDA8EBPBz3qcZ75sK6jR5/xDi1rWcvwAB"
    "zBhKEAb8SM6biupQDHp2U3LDwMSHmnXawX4l4PPBoqloOtqZIPAsVu8OqQcbJIDmFszBaSAB"
    "1xKPKYo/IQE075g5OA3tjO9DgIYdzusqCeB8R+bgNMgjIgGc/WEIYBrGt83BaWhnmk0IqGGH"
    "4rcg8oXeBeaEeSEB35oMOzT4IATegIeYOXvMSfMgBdQOyIj5EkKAht7dTrSy9/ekeZA90AUI"
    "iPQhQI/tOl1vT5oH2QMadmFIL3160Y/BiC5D4Cl4H/KO/BOwHbopzukF/2ef2AF9ymUblFml"
    "Uma2bbNSqcScpf4OjJG8stM3USotYl1h1WpFfCu77qvVqmLNGGO/AGh8YNRvhAXSAAAAAElF"
    "TkSuQmCC")
nav3_index.append('nav3_forward')
nav3_catalog['nav3_forward'] = nav3_forward
getnav3_forwardData = nav3_forward.GetData
getnav3_forwardImage = nav3_forward.GetImage
getnav3_forwardBitmap = nav3_forward.GetBitmap
getnav3_forwardIcon = nav3_forward.GetIcon

#----------------------------------------------------------------------
nav3_home = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAAZVJREFUSEvt0s8rRFEUwPFJKdn5D8ggv2M7M7GwlZ2lEmG2ysZO"
    "WbCd0pP8KAuFspJZTVZEQ5kykgXlx0KRhfzMr+/xzsub65lmJgtqTn163XPPPfe9+64v0wiF"
    "JxuwihX4Nf07QcN23OIOj7hGi07LfAGKXYp0Kn0EByxZPIgXHKEKTTjFE7qljmc13l0Snw3S"
    "Bc0LKZzSBevBsCVNZmGhBtt4wxhqkfkGNC+hKKbFM2jEsY5FMhS26ngu6nhTn45EoG9CuxnB"
    "ZCUO8YohtOEG7gbiEgGMQr7EPee9AROtuIL80A704hnuxW736EQXHjQnvh8RyR7IjztDM+Rs"
    "zTfzIl86jBDkqySXDPRbdmPOW67YuE7soBzLOs6G/Cu5Zfs6jkhvefNpTUjTMmzpOBcxmpby"
    "jOp4TjaIYAT1OIG5KFsHqICcypJ9TgQDuTleC3KxoW2/guS5UeSQGyX33LQHr3rheYt+2iCu"
    "JSlBXo7Uq17kN/ijG1wYRY78BnaQ/P8brCHuYV5LUoK836hz7GLBrvL5PgBCeDcVgEdDxQAA"
    "AABJRU5ErkJggg==")
nav3_index.append('nav3_home')
nav3_catalog['nav3_home'] = nav3_home
getnav3_homeData = nav3_home.GetData
getnav3_homeImage = nav3_home.GetImage
getnav3_homeBitmap = nav3_home.GetBitmap
getnav3_homeIcon = nav3_home.GetIcon

#----------------------------------------------------------------------
nav3_move = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAAQlJREFUSEu1kzEOwjAUQ3swDgATOzssSAyIAQYWRiZWNgaOwP2C"
    "HMnVj3FoI7XDq1In307y2y6lNCtWrLHcnhNQ/R9WdMD4+HhnWkKsqND89vpkWkKsGFHz1hAr"
    "ktP9mRabQ2a1u/TmGFPHGq2LWNEBMwZgrPM1rOh2NRRQO8mPgHt1Buv9tb8WjHUeuutJ8cKG"
    "uoAhUOMa3w9ork10uyXxVPwINCQ/ormCYi5WMOdqYkheOHsAiCGTXxFhCAqiPgbUqDkoFgEs"
    "cAFxt+5U0NUcFC9k1h+txlBADSsS7ApmgE0E8SOo7ZxYMcLG05y4hjqsqGjIWHNgRQdDWsyB"
    "FWvAuMUcWHE6UvcF5OFXiwd3+VIAAAAASUVORK5CYII=")
nav3_index.append('nav3_move')
nav3_catalog['nav3_move'] = nav3_move
getnav3_moveData = nav3_move.GetData
getnav3_moveImage = nav3_move.GetImage
getnav3_moveBitmap = nav3_move.GetBitmap
getnav3_moveIcon = nav3_move.GetIcon

#----------------------------------------------------------------------
nav3_subplots = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAA+1J"
    "REFUeJzllX9I3GUcx1/P57mv+lXvXHqet7mltmW3dUxd6CxbCFYjaqwxKTYY9c+I1qDRInA2"
    "0mZQG6zBQon9EUGMYKxFi9BBNGgbK7o4ZhblLtDlneg58w517PT77Y/z9C5//DH6rzc8PPB5"
    "vt/36/k8n+cH/N90DLgIrL9Xg0/8fr/d0NBgA4tbEzaHl4hntgtAQcpQpbv7/X772rVriAgA"
    "tm1jWRbd3d2cvnCa/LZ8VjlWMd49jq/fx9GjR+f/jUajAJw/f57W1tYgUAPgSAe4XC5CoRDD"
    "w8PzEICTXSfR7Zo1s2sokRKyG7O5/ONlPB97qKurAyA7OxutNY2NjXg8nuqRkREWAVIzvn37"
    "Nv39/fNxdUcRfilMmPB8LD8/n1u5t0gkEhlrvGfPHlLmSwJmZ2dJJBKEsx5k1HwIw9Csf3kX"
    "PkNjOARjrs8yNIZDYxtCYZ5BYZ6B32tSlDWVAVwyAwARlTR0CNFQgNH+ACIKLQrRCi2CiOKJ"
    "7TtYu6WGGRu0ZJR0McCyLG7cuEFnZyfmA49R8fTD/HzuBFM3v6egoIDR0VHuc1cBMBL5Ca/X"
    "y+c/XOTm9mZeONhC66FXccrd5QGDg4N0fd2FHBfi70UwHMJv335GR0cHPp+Pnp4ecr1PAhD5"
    "3UVzczPj4+O88eZb7H29lbHcQaZ3SnKjTtMAXJU0/w8nqyZxvuNko3vj3BJpAEzTxLIsDMOg"
    "cssGKrdswDRNRATTNJmMT+DQgtPhZFP1JpzHnVBJB7B7IYPVVKsXFW7DTaku5RcVwnAk+bFY"
    "jL6+PoqLixkJfgVAeXk5vb29C0vhEBzKQYVZgdvlJt4Wh708vgCI8LbdYl+JnYkxVjaGKOYB"
    "bW1ti4qXrvb2drQWojNRZuwZxnrG4Cw3gY/Sa3C1yCwi50wOgdoAIhsoLcxZ0ThdWhRqCi6d"
    "vETsbAzgEDCZXgPcbjcHDhxgW3Qbm2rqERFWr72fYDC4rHEwGMS7rgzRwr5nD7L/kf2poUn4"
    "1y6CZEFra2v5Y9qFaEXL8S6e2bGT4b8GlwR415Xx/qdfIFp4blczrrt/Z4wvAqQkohARNm/d"
    "xrkrvyYPmChQc00UtpL53lIKewmfZQFaFFoLCQtOHHmNoYE/USp5UpUCMy+fV44co3JzDTYK"
    "y07e1alvlgSEw8nLzOPx8FRVFV6vB4BTVpSyM4X4i/2U55QTmg5x/YPrFN8ZYWthpuHExAoZ"
    "RCKRLwOBwPNNTU3E43Hi8ThKKfbt3sep9lNY71oMGUMMfTNEXVYdPp+PgYGBuaxURr+cqvLy"
    "8sZZ7rV6FFsdViu+aPX19Tbw3YqUFZR6k0vu1eA/1z/VL1jv1/scBwAAAABJRU5ErkJggg==")
nav3_index.append('nav3_subplots')
nav3_catalog['nav3_subplots'] = nav3_subplots
getnav3_subplotsData = nav3_subplots.GetData
getnav3_subplotsImage = nav3_subplots.GetImage
getnav3_subplotsBitmap = nav3_subplots.GetBitmap
getnav3_subplotsIcon = nav3_subplots.GetIcon

#----------------------------------------------------------------------
nav3_zoom_to_rect = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAABR1JREFUSEutVGtMk2cUJouJJILOG0JpQegNENzcdFMRskk0kXiB"
    "6XQqZG7BuelwOieTuIkM1IkWuSioXJQWCpaWgqWWQeUuAtLa0lY7oEBLuXhDf7Dwgx/P3q/7"
    "foww3HQ+yZOcnPd8z7m833ucXgW7o/c4c3n8cIYnU+Ds7CycOXOmcOFCN8Gy997fvXz5B850"
    "2OuBx/Pb68vm2GP27UdJaRm0uk7oOo2oUChx+MhR+AUseerhwThIh/93fH/02Cy3Re7C7bui"
    "odGb0GcbxJ2OTsjVLSiraUFjux69VjsedFnw9bffgcHwVActfXcW/fm/w5PJEh46Gk8E+pBX"
    "fhsp0lqUa7pwz/oEGttTVOosSJU3IFtWDVNXL5LPCuDpyVTTn78c3ot9IiK2bkeH/gESCxRQ"
    "mmzoGR2D5fkfsLygSWzKV9s9jJMiJdq0RsTsO4DFPr4vH9f1whszmCwvg7rxLpKECkiNNtRa"
    "n6LBPorGoedoGnrhYCMh5asj3SjMQ0gghTS1asHm8uy7oj6f/uJ9fdmrPiNzL7qpxqlqLURG"
    "O0q6RlBqeQxZ7xOU9f1FypYSH3VWaLLjfL0RObIq7I89BCaT9QktNxUeDIYgPSsHPxdU4kyT"
    "Genaflw2DiL34TDyzcO4Zh5xkLIp32XTIASafvxYY8DBnAoUFMvgwfAU03JT4e7uoRLLlIi9"
    "rkKc2oSktl6c1w0grdOOiyTRJcIMgx0p921IuNePw8092FNlRGRJKyIzyyGrvA2Wl7eelpsK"
    "NoerLyIJvshT4ZtbesTf6UZSRz/OaK34lYie0dpwithJGitJ0If41l7E1pkRJdcgIrsSpSTB"
    "IneP6RNQ/3NuoQx785SIuanFseZunCaCAv0AqZx0YBpyMJN0kqq3OxLHk5i9ivuIylGiSKYC"
    "efHTJ3BzW5R+POkcThSSDio0OEk6yCDjySUzF3U9grjnsYOUnUd81FliSzcOKLSIE6mQkpmL"
    "BQsWTn8HZC18vC48AjkSJfZL7iCp6XdcJTOXEFGF9RlUA6OoIqwkNuW7ahhAMok5IGtFtuQW"
    "tu7cQz243bTcVLDZnJB58xdMCLKFOFdajYTqTlzR9EHePYJaItwy/MJByqZ8V8nZSfIHJd+o"
    "wcX8EvLQ2I83bYn855Xh4uISxvMPGo+JjcN1SSVyxRW4IK9DesMDlBrIg+t9hHb7MwcpW0p8"
    "GY0PcU5ej7ziCqwMCQOL5bWNlpsMSpzNDxi7cKUQDXe1sJBFJlHcxsVrEhSrGlBQ24E6sx3G"
    "wWcwDY2ioWsIwjoNxFVNyC6QYs3aDZg9Z04iLTcZlDjHL3A8lYg3t+tgtQ+jtvkeTpy9BJYP"
    "B1FfHcYVURmKylSQquohrap32Hmkwy9jj4HrHzTh7b04jpabDErch+s/lnpZhKY2HWyDIzCY"
    "LRDLf8O6jdvw9ty56fPmzU9nevuOvrMiGCHrNiN0/RYs+zAUPhz+ONm64lWr1wTScpNBiXv5"
    "cMcTUrJQ09jmqNzwsAfF5dXYELEDrq6uWXSoU9GNshkrVwcvDf1obXRwSGh0wJLApWfPp82g"
    "j6fCzz8g2I3hNbbvSCLyyQW13zehXWdyVB4euZOIz87i+/m/RYe/Okj1P6wO24zjpzMhkipR"
    "qlDjErnQ9Zs+dYjTYa8P0kGgN5s/EfdLGpLTchF/KgNrwjbChYzlf1X+d/D4fnFsftDEph0x"
    "CFoR4hCnj94cyLMOcXFxzScb8CcOl/dmKndycvoTX2VtcSgrH/YAAAAASUVORK5CYII=")
nav3_index.append('nav3_zoom_to_rect')
nav3_catalog['nav3_zoom_to_rect'] = nav3_zoom_to_rect
getnav3_zoom_to_rectData = nav3_zoom_to_rect.GetData
getnav3_zoom_to_rectImage = nav3_zoom_to_rect.GetImage
getnav3_zoom_to_rectBitmap = nav3_zoom_to_rect.GetBitmap
getnav3_zoom_to_rectIcon = nav3_zoom_to_rect.GetIcon

        
        


# Test Code ------------------------------------------------------------------

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap
#import matplotlib.pyplot as plt

class CanvasFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, -1, 'WxPython and Matplotlib', size=wx.Size(800,2000))

        naxes = 2
        self.data = [self.dist(256), self.dist(64)]

        self.top = wx.GetApp().GetTopWindow()

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.statusbar = self.CreateStatusBar(4, 0)
        self.axes = []
        self.axes.append(self.figure.add_subplot(2, 1, 1))
        self.axes.append(self.figure.add_subplot(2, 1, 2))

        self.aximg = []
        for i in range(naxes):
            self.aximg.append(self.axes[i].imshow(self.data[i], cmap=cm.gray))
        self.canvas = FigureCanvas(self, -1, self.figure)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.TOP | wx.LEFT | wx.EXPAND)

        self.toolbar = NavToolbarMri(self.canvas, self,
                                     vertOn=True,
                                     horizOn=True,
                                     lcolor='gold',
                                     lw=0.5)
        self.toolbar.Realize()
        # By adding toolbar in sizer, we are able to put it at the bottom
        # of the frame - so appearance is closer to GTK version.
        self.sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)

        # update the axes menu on the toolbar
        self.toolbar.update()
        self.SetSizer(self.sizer)
        self.Fit()


    def on_motion(self, xloc, yloc, xpos, ypos, iplot):
        value = self.data[iplot][int(round(xloc)),int(round(yloc))]
        self.top.statusbar.SetStatusText(" Value = %s" % (str(value),), 0)
        self.top.statusbar.SetStatusText(" X,Y = %i,%i" % (int(round(xloc)), int(round(yloc))), 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" ", 3)

    def on_select(self, xloc, yloc, xpos, ypos, iplot):
        """ placeholder, overload for user defined event handling """
        print('debug::on_select,          xloc='+str(xloc)+'  yloc='+str(yloc)+'  Index = '+str(iplot))

    def on_panzoom_motion(self, xloc, yloc, xpos, ypos, iplot):
        axes = self.axes[iplot]
        xmin, xmax = axes.get_xlim()
        ymax, ymin = axes.get_ylim()  # max/min flipped here because of y orient top/bottom
        xdelt, ydelt = xmax - xmin, ymax - ymin

        self.top.statusbar.SetStatusText((" X-range = %.1f to %.1f" % (xmin, xmax)), 0)
        self.top.statusbar.SetStatusText((" Y-range = %.1f to %.1f" % (ymin, ymax)), 1)
        self.top.statusbar.SetStatusText((" delta X,Y = %.1f,%.1f " % (xdelt, ydelt)), 2)
        self.top.statusbar.SetStatusText(" ", 3)

    def on_panzoom_release(self, xloc, yloc, xpos, ypos):
        """ placeholder, overload for user defined event handling """
        print('debug::on_panzoom_release, xloc='+str(xloc)+'  yloc='+str(yloc))

    def on_level_press(self, xloc, yloc, xpos, ypos, iplot):
        """ placeholder, overload for user defined event handling """
        print('debug::on_level_press,     xloc='+str(xloc)+'  yloc='+str(yloc)+'  Index = '+str(iplot))

    def on_level_release(self, xloc, yloc, xpos, ypos):
        """ placeholder, overload for user defined event handling """
        print('debug::on_level_release,   xloc='+str(xloc)+'  yloc='+str(yloc))

    def on_level_motion(self, xloc, yloc, xpos, ypos, iplot, wid, lev):
        self.top.statusbar.SetStatusText(" ", 0)
        self.top.statusbar.SetStatusText((" Wid = %i  Lev = %i" % (int(wid),int(lev))), 1)
        self.top.statusbar.SetStatusText(" ", 2)
        self.top.statusbar.SetStatusText(" ", 3)

    def dist(self, n, m=None):
        """ a rectangular array where each pixel = euclidian distance from the origin. """
        n1 = n
        m1 = m if m else n
        x = np.array([val**2 if val < (n1-val) else (n1-val)**2 for val in np.arange(n1) ])
        a = np.ndarray((n1,m1),float)   # Make array
        for i in range(int((m1/2)+1)):  # Row loop
            a[i,:] = np.sqrt(x + i**2.0)     # Euclidian distance
            if i != 0: a[m1-i,:] = a[i,:]    # Symmetrical
        return a

class App(wx.App):
    def OnInit(self):
        """Create the main window and insert the custom frame."""
        frame = CanvasFrame()
        frame.Show(True)
        return True


if __name__ == "__main__":
    app = App()
    app.MainLoop()
