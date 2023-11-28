#!/usr/bin/env python
"""
Separating out NavigationToolbar3Wx from image_panel_toolbar.py

This will allow me to start from NavigationToolbar2 code and add without
having to monkey patch.

Brian J. Soher, Duke University, 2023

"""
# Python modules

import os
import pathlib
from enum import Enum

# third party modules
import wx
import numpy as np
import matplotlib as mpl
import matplotlib.cm as cm
from matplotlib import (backend_tools as tools, cbook)

from matplotlib.backend_bases          import NavigationToolbar2, cursors

from matplotlib.figure    import Figure
from wx.lib.embeddedimage import PyEmbeddedImage


LEVMAX =  383
LEVMIN = -127
WIDMAX =  255
WIDMIN =    0
LEVSTR =  128




# MPL widlev example
#
#http://matplotlib.1069221.n5.nabble.com/Pan-zoom-interferes-with-user-specified-right-button-callback-td12186.html



#------------------------------------------------------------------------------
# NavToolbarMri
#
# This toolbar is specific to use in canvases that display MRI images.
#
#------------------------------------------------------------------------------

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


class NavToolbarMri:
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

      :meth:`set_message` (optional)
         display message

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
    
    
    def __init__(self, canvas, parent, vertOn=False, horizOn=False, lcolor='gold', lw=0.5, coordinates=True):

        wx.ToolBar.__init__(self, canvas.GetParent(), -1, style=style)

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
            if text in ['Pan', 'Level', 'Cursors']:
                self.AddCheckTool(self.wx_ids[text], ' ', bmp, shortHelp=text, longHelp=tooltip_text)
            elif text in ['Zoom', 'Subplots']:
                pass  # don't want this in my toolbar
                # self.AddTool(self.wx_ids[text],       # NB. bjs - this is not tested
                #              bitmap=bmp,              # adapted from backend_wx.py
                #              bmpDisabled=wx.NullBitmap,   # in NavigationToolbar2Wx
                #              label=text,
                #              shortHelp=tooltip_text,
                #              kind=(wx.ITEM_NORMAL))
            else:
                self.AddTool(self.wx_ids[text], ' ', bitmap=bmp, label=text)

            self.Bind(wx.EVT_TOOL, getattr(self, callback), id=self.wx_ids[text])

        self._coordinates = coordinates
        if self._coordinates:
            self.AddStretchableSpace()
            self._label_text = wx.StaticText(self, style=wx.ALIGN_RIGHT)
            self.AddControl(self._label_text)

        self.Realize()

        # bjs - from backend_bases.py NavigationToolbar2

        self.canvas = canvas
        canvas.toolbar = self
        self._nav_stack = cbook.Stack()
        # This cursor will be set after the initial draw.
        self._last_cursor = tools.Cursors.POINTER

        self._id_press   = self.canvas.mpl_connect( 'button_press_event', self.zoom_pan_level_handler)
        self._id_release = self.canvas.mpl_connect( 'button_release_event', self.zoom_pan_level_handler)
        self._id_drag    = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)
        self._pan_info   = None
        self._zoom_info  = None
        self._level_info = None

        self.mode = _Mode.NONE  # a mode string for the status bar
        self.set_history_buttons()

        # bjs-start

        self.parent = parent
        self.statusbar = self.parent.statusbar

        # turn off crosshairs when mouse outside canvas
        self._id_ax_leave  = self.canvas.mpl_connect('axes_leave_event', self.leave)
        self._id_fig_leave = self.canvas.mpl_connect('figure_leave_event', self.leave)

        # set up control params for crosshair functionality
        self._crosshairs = False
        self.vertOn  = vertOn
        self.horizOn = horizOn
        self.vlines = []
        self.hlines = []
        if vertOn:  self.vlines = [ax.axvline(0, visible=False, color=lcolor, lw=lw) for ax in self.parent.axes]
        if horizOn: self.hlines = [ax.axhline(0, visible=False, color=lcolor, lw=lw) for ax in self.parent.axes]


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


    def update(self):
        """Reset the Axes stack."""
        self._nav_stack.clear()
        self.set_history_buttons()


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
            self.set_message("pan unavailable")
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
        axes = [a for a in self.canvas.figure.get_axes()
                if a.in_axes(event) and a.get_navigate() and a.can_pan()]
        if not axes:
            return
        if self._nav_stack() is None:
            self.push_current()  # set the home button to this view
        for ax in axes:
            ax.start_pan(event.x, event.y, event.button)
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
            ax.drag_pan(self._pan_info.button, event.key, event.x, event.y)
        self.canvas.draw_idle()

        xloc, yloc = self.get_bounded_xyloc(event)
        iplot = self._pan_info.axes[0][0]
        self.parent.on_panzoom_motion(xloc, yloc, iplot)


    def release_pan(self, event):
        """Callback for mouse button release in pan/zoom mode."""
        if self._pan_info is None:
            return
        self.canvas.mpl_disconnect(self._pan_info.cid)
        self._id_drag = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)
        for ax in self._pan_info.axes:
            ax.end_pan()
        self.canvas.draw_idle()
        self._pan_info = None
        self.push_current()

        xloc, yloc = self.get_bounded_xyloc(event)
        self.parent.on_panzoom_release(xloc, yloc)


    def zoom(self, *args):
        if not self.canvas.widgetlock.available(self):
            self.set_message("zoom unavailable")
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

        xloc, yloc = self.get_bounded_xyloc(event)


    def level(self, *args):
        """
        Toggle the width/level tool.

        Change image with right button up/down left/right
        """
        if not self.canvas.widgetlock.available(self):
            self.set_message("level unavailable")
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

    _LevelInfo = namedtuple("_LevelInfo", "button axes cid prevx prevy")

    def press_level(self, event):
        """Callback for mouse button press in width/level mode."""

        if (event.button not in [MouseButton.LEFT, MouseButton.RIGHT]
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
        self._level_info = self._LevelInfo( button=event.button, axes=axes, cid=id_drag,
                                            prevx=event.x, prevy=event.y)

        for line in self.vlines + self.hlines:
            line.set_visible(False)
        self.canvas.draw_idle()

        xloc, yloc = self.get_bounded_xyloc(event)
        self.parent.on_level_press(xloc, yloc, axes[0][0])


    def drag_level(self, event):
        """Callback for dragging in width/level mode."""

        for item in self._level_info:
            i, a = item
            xprev, yprev = self._level_info.prevx, self._level_info.prevy

            xdelt = int((event.x - xprev))
            ydelt = int((event.y - yprev))

            if abs(ydelt) >= abs(xdelt):
                self.parent.level[indx] += ydelt
            else:
                self.parent.width[indx] += xdelt

            vmax0 = self.parent.vmax_orig[indx]
            vmin0 = self.parent.vmin_orig[indx]
            wid = max(WIDMIN, min(WIDMAX, self.parent.width[indx]))
            lev = max(LEVMIN, min(LEVMAX, self.parent.level[indx]))
            vtot = vmax0 - vmin0
            vmid = vmin0 + vtot * (lev / WIDMAX)
            vwid = vtot * (wid / WIDMAX)
            vmin = vmid - (vwid / 2.0)
            vmax = vmid + (vwid / 2.0)

            self.parent.vmax[indx] = vmax
            self.parent.vmin[indx] = vmin
            self.parent.width[indx] = wid  # need this in case values were
            self.parent.level[indx] = lev  # clipped by MIN MAX bounds

            self.parent.update_images(index=indx)

            # prep new 'last' location for next event call
            self._level_info.prevx = event.x
            self._level_info.prevy = event.y

        self.canvas.draw_idle()

        xloc, yloc = self.get_bounded_xyloc(event)
        iplot = self._level_info.axes[0][0]
        self.parent.on_level_motion(xloc, yloc, iplot)


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

        xloc, yloc = self.get_bounded_xyloc(event)
        self.parent.on_level_release(xloc, yloc)


    def press_local(self, event):
        # no toggle buttons on, but maybe we want to show crosshairs
        self.parent.select_is_held = True
        if self._cursors:
            for line in self.vlines + self.hlines:
                line.set_visible(True)
        self.canvas.draw_idle()


    def release_local(self, event):
        # no toggle buttons on
        self.parent.select_is_held = False
        xloc, yloc = self.get_bounded_xyloc(event)
        # find out what plot we released in
        iplot = None
        for i, axes in enumerate(self.parent.axes):
            if axes == event.inaxes:
                iplot = i
        self.parent.on_select(xloc, yloc, iplot)


    def mouse_move(self, event):
        self._update_cursor(event)

        # bjs - comment out for now
        # self.set_message(self._mouse_event_to_message(event))

        if not event.inaxes:
            return

        xloc, yloc = self.get_bounded_xyloc(event)
        iplot = None
        for i, axes in enumerate(self.parent.axes):
            if axes == event.inaxes:
                iplot = i

        if iplot is not None:
            self.parent.on_motion(xloc, yloc, iplot)

            if self._crosshairs and self.vertOn:
                for line in self.vlines:
                    line.set_xdata((xloc, xloc))
                    line.set_visible(True)
            if self._crosshairs and self.horizOn:
                for line in self.hlines:
                    line.set_ydata((yloc, yloc))
                    line.set_visible(True)
            self.canvas.draw_idle()





    #-----------------------------------------------------------------------------
    # bjs original methods

    # def on_motion(self, event):
    #     # The following limit when motion events are triggered
    #
    #     if not event.inaxes and self.mode == '':
    #         return
    #     if not event.inaxes and not self._button_pressed:
    #         # When we are in pan or zoom or level and the mouse strays outside
    #         # the canvas, we still want to have events even though the xyloc
    #         # can not be properly calculated. We are reporting other things
    #         # that do not need xylocs for like width/level values.
    #         return
    #
    #     xloc, yloc = self.get_bounded_xyloc(event)
    #
    #     iplot = None
    #     if self._xypress:
    #         item = self._xypress[0]
    #         axis, iplot = item[0], item[1]
    #     else:
    #         axis = None
    #         for i, axes in enumerate(self.parent.axes):
    #             if axes == event.inaxes:
    #                 iplot = i
    #
    #     # print("mode ="+str(self.mode)+"  button_pressed = "+str(self._button_pressed))
    #
    #     if self.mode == 'pan/zoom' and (self._button_pressed == 1 or self._button_pressed == 3):
    #         if iplot is not None:
    #             self.parent.on_panzoom_motion(xloc, yloc, iplot)
    #     elif self.mode == 'zoom rect' and (self._button_pressed == 1 or self._button_pressed == 3):
    #         if iplot is None:
    #             pass
    #     elif self.mode == 'width/level' and self._button_pressed == 3:
    #         if iplot is not None:
    #             self.parent.on_level_motion(xloc, yloc, iplot)
    #     elif self.mode == '':
    #         if iplot is not None:
    #             # no toggle buttons on
    #             self.parent.on_motion(xloc, yloc, iplot)
    #
    #             if self._cursors and self.vertOn:
    #                 for line in self.vlines:
    #                     line.set_xdata((xloc, xloc))
    #                     line.set_visible(True)
    #             if self._cursors and self.horizOn:
    #                 for line in self.hlines:
    #                     line.set_ydata((yloc, yloc))
    #                     line.set_visible(True)
    #             self.canvas.draw_idle()
    #             # self.dynamic_update()
    #     else:
    #         if iplot is not None:
    #             # catch all
    #             self.parent.on_motion(xloc, yloc, iplot)

    # def drag_pan(self, event):
    #     NavigationToolbar2.drag_pan(self, event)
    #     self.mouse_move(event)
        
        
    # def level(self, *args):
    #     """Activate the width/level tool. change values with right button up/down left/right"""
    #
    #     for item in ['Zoom', 'Pan']:
    #         if item in list(self.wx_ids.keys()): self.ToggleTool(self.wx_ids[item], False)
    #
    #     self.local_setup_before_event()
    #
    #     if not self.canvas.widgetlock.available(self):
    #         self.set_message("level unavailable")
    #         return
    #
    #     if self.mode == _Mode.LEVEL:
    #         self.mode = _Mode.NONE
    #         self.canvas.widgetlock.release(self)
    #     else:
    #         self.mode = _Mode.LEVEL
    #         if self._idPress is not None:
    #             self._idPress = self.canvas.mpl_disconnect(self._idPress)
    #         if self._idRelease is not None:
    #             self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
    #         self._idPress   = self.canvas.mpl_connect( 'button_press_event',   self.press_level)
    #         self._idRelease = self.canvas.mpl_connect( 'button_release_event', self.release_level)
    #         self.canvas.widgetlock(self)
    #
    #     for a in self.canvas.figure.get_axes():
    #         a.set_navigate_mode(self.mode._navigate_mode)
    #
    #     self.set_message(self.mode)
    #
    #     self.local_setup_after_event()  # bjs - may not need this here, not part of super class

 
    # def press_level(self, event):
    #     """the press mouse button in width/level mode callback"""
    #
    #     if event.button == 3:
    #         self._button_pressed = 3
    #     else:
    #         self._button_pressed = None
    #         return
    #
    #     x, y = event.x, event.y
    #
    #     # push the current view to define home if stack is empty
    #     if self._nav_stack() is None:
    #         self.push_current()
    #
    #     self._xypress = []
    #     for i, a in enumerate(self.canvas.figure.get_axes()):
    #         if (x is not None and y is not None and a.in_axes(event) and a.get_navigate() and a.can_pan()):
    #             self._xypress.append([a, i, event.x, event.y])
    #             self.canvas.mpl_disconnect(self._idDrag)
    #             self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.drag_level)
    #
    #     self.press_local(event)
 
 
    # def drag_level(self, event):
    #     """the drag callback in width/level mode"""
    #
    #     for a, indx, xprev, yprev in self._xypress:
    #
    #         xdelt = int((event.x-xprev))
    #         ydelt = int((event.y-yprev))
    #
    #         if abs(ydelt) >= abs(xdelt):
    #             self.parent.level[indx] += ydelt
    #         else:
    #             self.parent.width[indx] += xdelt
    #
    #         vmax0 = self.parent.vmax_orig[indx]
    #         vmin0 = self.parent.vmin_orig[indx]
    #         wid   = max(WIDMIN, min(WIDMAX, self.parent.width[indx]))
    #         lev   = max(LEVMIN, min(LEVMAX, self.parent.level[indx]))
    #         vtot  = vmax0 - vmin0
    #         vmid  = vmin0 + vtot * (lev/WIDMAX)
    #         vwid  = vtot * (wid/WIDMAX)
    #         vmin  = vmid - (vwid/2.0)
    #         vmax  = vmid + (vwid/2.0)
    #
    #         self.parent.vmax[indx]  = vmax
    #         self.parent.vmin[indx]  = vmin
    #         self.parent.width[indx] = wid   # need this in case values were
    #         self.parent.level[indx] = lev   # clipped by MIN MAX bounds
    #
    #         self.parent.update_images(index=indx)
    #
    #         # prep new 'last' location for next event call
    #         self._xypress[0][2] = event.x
    #         self._xypress[0][3] = event.y
    #
    #     self.mouse_move(event)
    #
    #     self.canvas.draw_idle()
    #     #self.dynamic_update()

 
    # def release_level(self, event):
    #     """the release mouse button callback in width/level mode"""
    #
    #     if self._button_pressed is None:
    #         return
    #     self.canvas.mpl_disconnect(self._idDrag)
    #     self._idDrag = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)
    #     for a, ind, xlast, ylast in self._xypress:
    #         pass
    #     if not self._xypress:
    #         return
    #
    #     self._xypress = []
    #     self._button_pressed = None
    #     self.push_current()
    #     self.release_local(event)
    #     self.canvas.draw()





    # def set_cursor(self, cursor):
    #     cursor = wx.Cursor(cursord[cursor])
    #     self.canvas.SetCursor( cursor )








    # def on_motion(self, event):
    #     # The following limit when motion events are triggered
    #
    #     if not event.inaxes and self.mode == '':
    #         return
    #     if not event.inaxes and not self._button_pressed:
    #         # When we are in pan or zoom or level and the mouse strays outside
    #         # the canvas, we still want to have events even though the xyloc
    #         # can not be properly calculated. We are reporting other things
    #         # that do not need xylocs for like width/level values.
    #         return
    #
    #     xloc, yloc = self.get_bounded_xyloc(event)
    #
    #     iplot = None
    #     if self._xypress:
    #         item = self._xypress[0]
    #         axis, iplot = item[0], item[1]
    #     else:
    #         axis = None
    #         for i,axes in enumerate(self.parent.axes):
    #             if axes == event.inaxes:
    #                 iplot = i
    #
    #     # print("mode ="+str(self.mode)+"  button_pressed = "+str(self._button_pressed))
    #
    #     if self.mode == 'pan/zoom' and (self._button_pressed == 1 or self._button_pressed == 3):
    #         if iplot is not None:
    #             self.parent.on_panzoom_motion(xloc, yloc, iplot)
    #     elif self.mode == 'zoom rect' and (self._button_pressed == 1 or self._button_pressed == 3):
    #         if iplot is None:
    #             pass
    #     elif self.mode == 'width/level' and self._button_pressed == 3:
    #         if iplot is not None:
    #             self.parent.on_level_motion(xloc, yloc, iplot)
    #     elif self.mode == '':
    #         if iplot is not None:
    #             # no toggle buttons on
    #             self.parent.on_motion(xloc, yloc, iplot)
    #
    #             if self._cursors and self.vertOn:
    #                 for line in self.vlines:
    #                     line.set_xdata((xloc, xloc))
    #                     line.set_visible(True)
    #             if self._cursors and self.horizOn:
    #                 for line in self.hlines:
    #                     line.set_ydata((yloc, yloc))
    #                     line.set_visible(True)
    #             self.canvas.draw_idle()
    #             #self.dynamic_update()
    #     else:
    #         if iplot is not None:
    #             # catch all
    #             self.parent.on_motion(xloc, yloc, iplot)
            
  
    # def mouse_move(self, event):
    #     # call base event
    #     NavigationToolbar2.mouse_move(self, event)
    #
    #     if event.inaxes and self.parent.axes[0].get_navigate_mode():
    #
    #         try:
    #             # for MPL >=3.4 ?? bjs 3.6 for sure
    #             if (self.parent.axes[0].get_navigate_mode() == 'LEVEL' and self._last_cursor != 4):
    #                 self.set_cursor(4)
    #                 self._last_cursor = 4
    #         except:
    #             # for MPS <= 3.3 for sure, bjs
    #             if (self.parent.axes[0].get_navigate_mode() == 'LEVEL' and self._lastCursor != 4):
    #                 self.set_cursor(4)
    #                 self._lastCursor = 4
    #
    #     # call additional event
    #     self.on_motion(event)


    def get_bounded_xyloc(self, event):
        if not event.inaxes:
            return 0,0

        xloc, yloc = event.xdata, event.ydata
        
        # bound these values to be inside the size of the image.
        # - a pan event could yield negative locations.
        x0, y0, x1, y1 = event.inaxes.dataLim.bounds
        xmin,xmax = x0+0.5, x0+0.5+x1-1
        ymin,ymax = y0+0.5, y0+0.5+y1-1     # position swap due to 0,0 location 'upper'
        xloc = max(0, min(xmax, xloc))
        yloc = max(0, min(ymax, yloc))

        return xloc,yloc
    
    

    #-------------------------------------------------------


    def set_status_bar(self, statusbar):
        self.statusbar = statusbar


    def set_message(self, s):
        if self.statusbar is not None:
            pass
        # # from backend_wx.py
        # if self._coordinates:
        #     self._label_text.SetLabel(s)


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
            _log.debug('%s - Save file path: %s', type(self), path)
            fmt = exts[dialog.GetFilterIndex()]
            ext = path.suffix[1:]
            if ext in self.canvas.get_supported_filetypes() and fmt != ext:
                # looks like they forgot to set the image type drop
                # down, going with the extension.
                _log.warning('extension %s did not match the selected '
                             'image type %s; going with %s',
                             ext, fmt, ext)
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


    # def configure_subplots(self, evt):
    #     frame = wx.Frame(None, -1, "Configure subplots")
    #
    #     toolfig = Figure((6, 3))
    #     canvas = self.get_canvas(frame, toolfig)
    #
    #     # Create a figure manager to manage things
    #     figmgr = FigureManager(canvas, 1, frame)
    #
    #     # Now put all into a sizer
    #     sizer = wx.BoxSizer(wx.VERTICAL)
    #     # This way of adding to sizer allows resizing
    #     sizer.Add(canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
    #     frame.SetSizer(sizer)
    #     frame.Fit()
    #     tool = SubplotTool(self.canvas.figure, toolfig)
    #     frame.Show()

    # def save_figure(self, *args):
    #     # Fetch the required filename and file type.
    #     filetypes, exts, filter_index = self.canvas._get_imagesave_wildcards()
    #     default_file = self.canvas.get_default_filename()
    #     dlg = wx.FileDialog(self.parent, "Save to file", "", default_file,
    #                         filetypes,
    #                         wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
    #     dlg.SetFilterIndex(filter_index)
    #     if dlg.ShowModal() == wx.ID_OK:
    #         dirname = dlg.GetDirectory()
    #         filename = dlg.GetFilename()
    #         format = exts[dlg.GetFilterIndex()]
    #         basename, ext = os.path.splitext(filename)
    #         if ext.startswith('.'):
    #             ext = ext[1:]
    #         if ext in ('svg', 'pdf', 'ps', 'eps', 'png') and format != ext:
    #             # looks like they forgot to set the image type drop
    #             # down, going with the extension.
    #             warnings.warn('extension %s did not match the selected image type %s; going with %s' % (ext, format, ext),
    #                           stacklevel=0)
    #             format = ext
    #         try:
    #             self.canvas.print_figure(
    #                 os.path.join(dirname, filename), format=format)
    #         except Exception as e:
    #             error_msg_wx(str(e))



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
        
        
class DemoImagePanel(ImagePanelToolbar2):
    """Plots several lines in distinct colors."""

    # Activate event messages
    _EVENT_DEBUG = True
    
    def __init__( self, parent, tab, statusbar, **kwargs ):
        # statusbar has to be here for NavigationToolbar3Wx to discover on init()
        self.statusbar = statusbar
        # initiate plotter
        sizer = ImagePanelToolbar2.__init__( self, 
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

    def on_motion(self, xloc, yloc, iplot):
        value = self.data[iplot][0]['data'][int(round(xloc))][int(round(yloc))]
        self.top.statusbar.SetStatusText( " Value = %s" % (str(value), ), 0)
        self.top.statusbar.SetStatusText( " X,Y = %i,%i" % (int(round(xloc)),int(round(yloc))) , 1)
        self.top.statusbar.SetStatusText( " " , 2)
        self.top.statusbar.SetStatusText( " " , 3)

    def on_panzoom_motion(self, xloc, yloc, iplot):
        axes = self.axes[iplot]
        xmin,xmax = axes.get_xlim()
        ymax,ymin = axes.get_ylim()         # max/min flipped here because of y orient top/bottom
        xdelt, ydelt = xmax-xmin, ymax-ymin
        
        self.top.statusbar.SetStatusText(( " X-range = %.1f to %.1f" % (xmin, xmax)), 0)
        self.top.statusbar.SetStatusText(( " Y-range = %.1f to %.1f" % (ymin, ymax)), 1)
        self.top.statusbar.SetStatusText(( " delta X,Y = %.1f,%.1f " % (xdelt,ydelt )), 2)
        self.top.statusbar.SetStatusText( " " , 3)

    def on_level_motion(self, xloc, yloc, iplot):
        self.top.statusbar.SetStatusText( " " , 0)
        self.top.statusbar.SetStatusText(( " Width = %i " % (self.width[iplot],)), 1)
        self.top.statusbar.SetStatusText(( " Level = %i " % (self.level[iplot],)), 2)
        self.top.statusbar.SetStatusText( " " , 3)



class MyFrame(wx.Frame):
    def __init__(self, title="New Title Please", size=(350,200)):
 
        wx.Frame.__init__(self, None, title=title, pos=(150,150), size=size)
        self.Bind(wx.EVT_CLOSE, self.on_close)
 
        util_CreateMenuBar(self)

        self.statusbar = self.CreateStatusBar(4, 0)
 
        self.size_small  = 64
        self.size_medium = 128
        self.size_large  = 256
 
        data1 = { 'data'  : self.dist(self.size_medium),
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
    frame = MyFrame( title='WxPython and Matplotlib', size=(600,600) )
    frame.Show()
    app.MainLoop()
