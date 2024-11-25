"""
Expansion of matplotlib embed in wx example
see http://matplotlib.org/examples/user_interfaces/embedding_in_wx4.html

This version, is an expansion that allows users to display one or more
images in vertical arrangement of axes. A toolbar with custom icons is
attached to the bottom that allow the user to pan, zoom, save figures, and
undo/home the images in the axes. Note that standard settings are for
multiple axes to be linked for pan/zoom operations.

Orig version, image_panel_toolbar.py, was not working well for pymriseg,
so I did a refactor and renamed the Image Navigation bar to ImageNav class.
It combines the original NavigationToolbar2 with NavigationToolbar3Wx so
that all the methods are on the same level and I can try to suss out how
to weave them better.

Right now, October 2024, it is working as needed, but still a swirl of Modes
PAN vs LEVEL vs ZOOM (not set right now) etc.

Copyright Brian J. Soher, Duke University, 2024


"""
# Python modules
import os
import time
import warnings
from contextlib import contextmanager
from collections import namedtuple
from weakref import WeakKeyDictionary

# third party modules
import wx
import numpy as np
import matplotlib as mpl
import matplotlib.cm as cm
from enum import Enum, IntEnum

mpl.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases          import cursors
from matplotlib.figure    import Figure
from matplotlib import (backend_tools as tools, cbook, widgets)
from wx.lib.embeddedimage import PyEmbeddedImage


LEVMAX =  383
LEVMIN = -127
WIDMAX =  255
WIDMIN =    0
LEVSTR =  128

# ***************** Shortcuts to wxPython standard cursors************

cursord = { cursors.MOVE          : wx.CURSOR_HAND,
            cursors.HAND          : wx.CURSOR_HAND,
            cursors.POINTER       : wx.CURSOR_ARROW,
            cursors.SELECT_REGION : wx.CURSOR_CROSS,
            4                     : wx.CURSOR_BULLSEYE,
          }

class MouseButton(IntEnum):
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    BACK = 8
    FORWARD = 9

class _Mode(str, Enum):
    NONE = ""
    PAN = "pan/zoom"
    ZOOM = "zoom rect"
    LEVEL = "level"

    def __str__(self):
        return self.value

    @property
    def _navigate_mode(self):
        return self.name if self is not _Mode.NONE else None

class Stack:
    """
    Stack of elements with a movable cursor.
    Mimics home/back/forward in a web browser.
    Orig from mpl.cbook.Stack, but that is deprecated, so local copy

    """
    def __init__(self, default=None):
        self.clear()
        self._default = default

    def __call__(self):
        """Return the current element, or None."""
        if not self._elements:
            return self._default
        else:
            return self._elements[self._pos]

    def __len__(self):
        return len(self._elements)

    def __getitem__(self, ind):
        return self._elements[ind]

    def forward(self):
        """Move the position forward and return the current element."""
        self._pos = min(self._pos + 1, len(self._elements) - 1)
        return self()

    def back(self):
        """Move the position back and return the current element."""
        if self._pos > 0:
            self._pos -= 1
        return self()

    def push(self, o):
        """
        Push *o* to the stack at current position.  Discard all later elements.
        *o* is returned.

        """
        self._elements = self._elements[:self._pos + 1] + [o]
        self._pos = len(self._elements) - 1
        return self()

    def home(self):
        """
        Push the first element onto the top of the stack.
        The first element is returned.

        """
        if not self._elements:
            return
        self.push(self._elements[0])
        return self()

    def empty(self):
        """Return whether the stack is empty."""
        return len(self._elements) == 0

    def clear(self):
        """Empty the stack."""
        self._pos = -1
        self._elements = []

    def bubble(self, o):
        """
        Raise all references of *o* to the top of the stack, and return it.
        Raises
        ------
        ValueError
            If *o* is not in the stack.

        """
        if o not in self._elements:
            raise ValueError('Given element not contained in the stack')
        old_elements = self._elements.copy()
        self.clear()
        top_elements = []
        for elem in old_elements:
            if elem == o:
                top_elements.append(elem)
            else:
                self.push(elem)
        for _ in top_elements:
            self.push(o)
        return o

    def remove(self, o):
        """
        Remove *o* from the stack.
        Raises
        ------
        ValueError
            If *o* is not in the stack.

        """
        if o not in self._elements:
            raise ValueError('Given element not contained in the stack')
        old_elements = self._elements.copy()
        self.clear()
        for elem in old_elements:
            if elem != o:
                self.push(elem)

#------------------------------------------------------------------------------
# ImageNav
#
# This toolbar is specific to use in canvases that display images.
#
#------------------------------------------------------------------------------

class ImageNav(wx.ToolBar):
    """
    Base class for the navigation cursor toolbar.

    Based on backend_bases.py NavigationToolbar2 and NavigationToolbar2Wx in backend_wx.py
    - started new because inheritance got complicated
    - too many interleaving things

    Backends must implement a canvas that handles connections for
    'button_press_event' and 'button_release_event'.  See
    :meth:`FigureCanvasBase.mpl_connect` for more information.

    They must also define

    :meth:`save_figure`
        Save the current figure.

    :meth:`draw_rubberband` (optional)
        Draw the zoom to rect "rubberband" rectangle.

    :meth:`set_message` (optional)
        Display message.

    :meth:`set_history_buttons` (optional)
        You can change the history back / forward buttons to indicate disabled / enabled
        state.

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
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis', 'zoom_to_rect', 'zoom'),
        ('Level', 'Set width/level with right mouse', 'contrast', 'level'),
        ('Cursors', 'Track mouse movement with crossed cursors', 'crosshair', 'cursors'),
        (None, None, None, None),
        ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
      )

    def __init__(self, canvas, parent, vertOn=False, horizOn=False, lcolor='gold', lw=0.5, coordinates=True):

        self.canvas = canvas
        self.parent = parent

        wx.ToolBar.__init__(self, canvas.GetParent(), -1)
        if 'wxMac' in wx.PlatformInfo:
            self.SetToolBitmapSize((24, 24))

        self.wx_ids = {}
        for text, tooltip_text, image_file, callback in self.toolitems:

            if text is None:
                self.AddSeparator()
                continue

            bmp = z_catalog[image_file].GetBitmap()

            self.wx_ids[text] = wx.NewIdRef()
            if text in ['Pan', 'Level', 'Cursors','Subplots']:
                self.AddCheckTool(self.wx_ids[text], ' ', bmp, shortHelp=text, longHelp=tooltip_text)
            elif text in ['Zoom', ]:
                pass  # don't want this in my toolbar
            else:
                self.AddTool(self.wx_ids[text], ' ', bmp, text)

            self.Bind(wx.EVT_TOOL, getattr(self, callback), id=self.wx_ids[text])

        self._coordinates = coordinates
        if self._coordinates:
            self.AddStretchableSpace()
            self._label_text = wx.StaticText(self)
            self.AddControl(self._label_text)

        self.Realize()

        # orig __init__
        canvas.toolbar = self
        self._nav_stack = Stack()
        # This cursor will be set after the initial draw.
        self._last_cursor = tools.Cursors.POINTER

        self._id_press = self.canvas.mpl_connect( 'button_press_event', self._zoom_pan_handler)
        self._id_release = self.canvas.mpl_connect( 'button_release_event', self._zoom_pan_handler)
        self._id_drag = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)
        self._pan_info = None
        self._zoom_info = None

        self.mode = _Mode.NONE  # a mode string for the status bar
        self.set_history_buttons()

        # end orig __init__

        self._idle = True
        self.statbar = self.parent.statusbar
        self._button_pressed = None
        self._xypress = None

        # turn off crosshair cursors when mouse outside canvas
        self._idAxLeave = self.canvas.mpl_connect('axes_leave_event', self.leave)
        self._idFigLeave = self.canvas.mpl_connect('figure_leave_event', self.leave)
        self._idRelease = self.canvas.mpl_connect('button_release_event', self.release)
        self._idPress = None
        self._idDrag = self.canvas.mpl_connect( 'motion_notify_event', self.mouse_move)

        # set up control params for cursor crosshair functionality
        self._cursors = False
        self.vertOn = vertOn
        self.horizOn = horizOn
        self.vlines = []
        self.hlines = []
        if vertOn:  self.vlines = [ax.axvline(0, visible=False, color=lcolor, lw=lw) for ax in self.parent.axes]
        if horizOn: self.hlines = [ax.axhline(0, visible=False, color=lcolor, lw=lw) for ax in self.parent.axes]
        self._lastCursor = -1

    def remove_rubberband(self):
        """Remove the rubberband."""

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
        self._draw_time, last_draw_time = (time.time(), getattr(self, "_draw_time", -np.inf))
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

    def mouse_move(self, event):
        self._update_cursor(event)
        self.set_message(self._mouse_event_to_message(event))

        # bjs-start
        if event.inaxes and self.parent.axes[0].get_navigate_mode():
            if (self.parent.axes[0].get_navigate_mode() == 'LEVEL' and self._lastCursor != 4):
                self.set_cursor(4)
                self._lastCursor = 4

        # call additional event
        self.on_motion(event)
        # bjs-end

    def _zoom_pan_handler(self, event):
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

    def _start_event_axes_interaction(self, event, *, method):

        def _ax_filter(ax):
            return (ax.in_axes(event) and
                    ax.get_navigate() and
                    getattr(ax, f"can_{method}")()
                    )

        def _capture_events(ax):
            f = ax.get_forward_navigation_events()
            if f == "auto":  # (capture = patch visibility)
                f = not ax.patch.get_visible()
            return not f

        # get all relevant axes for the event
        axes = list(filter(_ax_filter, self.canvas.figure.get_axes()))

        if len(axes) == 0:
            return []

        if self._nav_stack() is None:
            self.push_current()   # Set the home button to this view.

        # group axes by zorder (reverse to trigger later axes first)
        grps = dict()
        for ax in reversed(axes):
            grps.setdefault(ax.get_zorder(), []).append(ax)

        axes_to_trigger = []
        # go through zorders in reverse until we hit a capturing axes
        for zorder in sorted(grps, reverse=True):
            for ax in grps[zorder]:
                axes_to_trigger.append(ax)
                # NOTE: shared axes are automatically triggered, but twin-axes not!
                axes_to_trigger.extend(ax._twinned_axes.get_siblings(ax))

                if _capture_events(ax):
                    break  # break if we hit a capturing axes
            else:
                # If the inner loop finished without an explicit break,
                # (e.g. no capturing axes was found) continue the
                # outer loop to the next zorder.
                continue

            # If the inner loop was terminated with an explicit break,
            # terminate the outer loop as well.
            break

        # avoid duplicated triggers (but keep order of list)
        axes_to_trigger = list(dict.fromkeys(axes_to_trigger))

        return axes_to_trigger

    def pan(self, *args):
        """
        Toggle the pan/zoom tool.

        Pan with left button, zoom with right.
        """

        # bjs-start
        for item in ['Zoom', 'Level']:
            if item in list(self.wx_ids.keys()): self.ToggleTool(self.wx_ids[item], False)
        if self.parent.axes[0].get_navigate_mode() is None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
        # bjs-end

        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)

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

        # bjs-start
        if self.parent.axes[0].get_navigate_mode() is None:
            self._idRelease = self.canvas.mpl_connect('button_release_event', self.release)
        # bjs-end

    _PanInfo = namedtuple("_PanInfo", "button axes cid")

    def press_pan(self, event):
        """Callback for mouse button press in pan/zoom mode."""
        if (event.button not in [MouseButton.LEFT, MouseButton.RIGHT]
                or event.x is None or event.y is None):
            return

        axes = self._start_event_axes_interaction(event, method="pan")
        if not axes:
            return

        # call "ax.start_pan(..)" on all relevant axes of an event
        for ax in axes:
            ax.start_pan(event.x, event.y, event.button)

        self.canvas.mpl_disconnect(self._id_drag)
        id_drag = self.canvas.mpl_connect("motion_notify_event", self.drag_pan)

        self._pan_info = self._PanInfo(button=event.button, axes=axes, cid=id_drag)

    def drag_pan(self, event):
        """Callback for dragging in pan/zoom mode."""
        for ax in self._pan_info.axes:
            # Using the recorded button at the press is safer than the current
            # button, as multiple buttons can get pressed during motion.
            ax.drag_pan(self._pan_info.button, event.key, event.x, event.y)
        self.canvas.draw_idle()

        # bjs-start
        self.mouse_move(event)
        # bjs-end

    def release_pan(self, event):
        """Callback for mouse button release in pan/zoom mode."""
        if self._pan_info is None:
            return
        self.canvas.mpl_disconnect(self._pan_info.cid)
        self._id_drag = self.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        for ax in self._pan_info.axes:
            ax.end_pan()
        self.canvas.draw_idle()
        self._pan_info = None
        self.push_current()

    def zoom(self, *args):

        # bjs-start
        for item in ['Pan', 'Level']:
            if item in list(self.wx_ids.keys()): self.ToggleTool(self.wx_ids[item], False)
        if self.parent.axes[0].get_navigate_mode() is None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
        # bjs-end

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

        # bjs-start
        if self.parent.axes[0].get_navigate_mode() is None:
            self._idRelease = self.canvas.mpl_connect('button_release_event', self.release)
        # bjs-end

    _ZoomInfo = namedtuple("_ZoomInfo", "direction start_xy axes cid cbar")

    def press_zoom(self, event):
        """Callback for mouse button press in zoom to rect mode."""
        if (event.button not in [MouseButton.LEFT, MouseButton.RIGHT]
                or event.x is None or event.y is None):
            return

        axes = self._start_event_axes_interaction(event, method="zoom")
        if not axes:
            return

        id_zoom = self.canvas.mpl_connect("motion_notify_event", self.drag_zoom)

        # A colorbar is one-dimensional, so we extend the zoom rectangle out
        # to the edge of the Axes bbox in the other dimension. To do that we
        # store the orientation of the colorbar for later.
        parent_ax = axes[0]
        if hasattr(parent_ax, "_colorbar"):
            cbar = parent_ax._colorbar.orientation
        else:
            cbar = None

        self._zoom_info = self._ZoomInfo(
            direction="in" if event.button == 1 else "out",
            start_xy=(event.x, event.y), axes=axes, cid=id_zoom, cbar=cbar)

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

        self.canvas.draw_idle()
        self._zoom_info = None
        self.push_current()

    def level(self, *args):
        """
        Toggle the width/level tool.

        Change values with right button
        """

        # set the pointer icon and button press funcs to the
        # appropriate callbacks

        # bjs-start
        for item in ['Pan', 'Zoom']:
            if item in list(self.wx_ids.keys()): self.ToggleTool(self.wx_ids[item], False)
        if self.parent.axes[0].get_navigate_mode() is None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
        # bjs-end

        if self.parent.axes[0].get_navigate_mode() == _Mode.LEVEL._navigate_mode:
            self.parent.axes[0].set_navigate_mode(None)
        else:
            self.parent.axes[0].set_navigate_mode(_Mode.LEVEL)

        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)

        if self.parent.axes[0].get_navigate_mode() == _Mode.LEVEL:
            self._idPress = self.canvas.mpl_connect('button_press_event', self.press_level)
            self._idRelease = self.canvas.mpl_connect('button_release_event', self.release_level)
            self.mode = _Mode.LEVEL
            self.canvas.widgetlock(self)
        else:
            self.mode = _Mode.NONE
            self.canvas.widgetlock.release(self)

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self.mode._navigate_mode)

        if self.parent.axes[0].get_navigate_mode() is None:
            self._idRelease = self.canvas.mpl_connect('button_release_event', self.release)

        self.set_message(self.mode)


    def press_level(self, event):
        """the press mouse button in width/level mode callback"""

        if event.button == 3:
            self._button_pressed = 3
        else:
            self._button_pressed = None
            return

        x, y = event.x, event.y

        # push the current view to define home if stack is empty
        if self._nav_stack.empty():
            self.push_current()

        self._xypress = []
        for i, a in enumerate(self.canvas.figure.get_axes()):
            if (x is not None and y is not None and a.in_axes(event) and a.get_navigate() and a.can_pan()):
                self._xypress.append([a, i, event.x, event.y])
                self.canvas.mpl_disconnect(self._idDrag)
                self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.drag_level)

        self.press(event)

    def drag_level(self, event):
        """the drag callback in width/level mode"""

        for a, indx, xprev, yprev in self._xypress:

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
            self._xypress[0][2] = event.x
            self._xypress[0][3] = event.y

        self.mouse_move(event)

        self.dynamic_update()

    def release_level(self, event):
        """the release mouse button callback in width/level mode"""

        if self._button_pressed is None:
            return
        self.canvas.mpl_disconnect(self._idDrag)
        self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.mouse_move)
        for a, ind, xlast, ylast in self._xypress:
            pass
        if not self._xypress:
            return
        self._xypress = []
        self._button_pressed = None
        self.push_current()
        self.release(event)
        self.canvas.draw()

    def cursors(self, *args):
        """
        Toggle the crosshair cursors tool to show vertical and
        horizontal lines that track the mouse motion, or not.

        """
        if self._cursors:
            self._cursors = False
            if 'Cursors' in list(self.wx_ids.keys()):
                self.ToggleTool(self.wx_ids['Cursors'], False)
        else:
            self._cursors = True
            if 'Cursors' in list(self.wx_ids.keys()):
                self.ToggleTool(self.wx_ids['Cursors'], True)

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

    def save_figure(self, *args):
        # Fetch the required filename and file type.
        filetypes, exts, filter_index = self.canvas._get_imagesave_wildcards()
        default_file = self.canvas.get_default_filename()
        dlg = wx.FileDialog(self.parent, "Save to file", "", default_file,
                            filetypes,
                            wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        dlg.SetFilterIndex(filter_index)
        if dlg.ShowModal() == wx.ID_OK:
            dirname  = dlg.GetDirectory()
            filename = dlg.GetFilename()
            format = exts[dlg.GetFilterIndex()]
            basename, ext = os.path.splitext(filename)
            if ext.startswith('.'):
                ext = ext[1:]
            if ext in ('svg', 'pdf', 'ps', 'eps', 'png') and format!=ext:
                #looks like they forgot to set the image type drop
                #down, going with the extension.
                warnings.warn('extension %s did not match the selected image type %s; going with %s'%(ext, format, ext), stacklevel=0)
                format = ext
            try:
                self.canvas.print_figure(os.path.join(dirname, filename), format=format)
            except Exception as e:
                raise ValueError(str(e))

    def set_cursor(self, cursor):
        cursor = wx.Cursor(cursord[cursor])
        self.canvas.SetCursor( cursor )

    def update(self):
        """Reset the Axes stack - BJS not currently used? """
        self._nav_stack.clear()
        self.set_history_buttons()

    def set_history_buttons(self):
        can_backward = (self._nav_stack._pos > 0)
        can_forward = (self._nav_stack._pos < len(self._nav_stack._elements) - 1)
        self.EnableTool(self.wx_ids['Back'], can_backward)
        self.EnableTool(self.wx_ids['Forward'], can_forward)

    def press(self, event):

        xloc, yloc = self.get_bounded_xyloc(event)
        item = self._xypress[0]
        axes, iplot = item[0], item[1]
        if self.mode == 'pan/zoom':
            for line in self.vlines + self.hlines:
                line.set_visible(False)
            self.dynamic_update()
            pass
        elif self.mode == 'zoom rect':
            for line in self.vlines + self.hlines:
                line.set_visible(False)
            self.dynamic_update()
            pass
        elif self.mode == 'width/level':
            for line in self.vlines + self.hlines:
                line.set_visible(False)
            self.dynamic_update()
            self.parent.on_level_press(xloc, yloc, iplot)
        elif self.mode == '':
            # no toggle buttons on
            # but, maybe we want to show crosshair cursors
            if self._cursors:
                for line in self.vlines + self.hlines:
                    line.set_visible(True)
            self.dynamic_update()
            pass
        else:
            # catch all
            pass

    def release(self, event):
        # legacy code from NavigationToolbar2Wx
        try:
            del self.lastrect
        except AttributeError:
            pass

        # find out what plot we released in
        iplot = None
        for i, axes in enumerate(self.parent.axes):
            if axes == event.inaxes:
                iplot = i

        # get bounded location and call user event
        xloc, yloc = self.get_bounded_xyloc(event)
        if self.mode == 'pan/zoom':
            self.parent.on_panzoom_release(xloc, yloc)
        elif self.mode == 'zoom rect':
            pass
        elif self.mode == 'width/level':
            self.parent.on_level_release(xloc, yloc)
        elif self.mode == '':
            # no toggle buttons on
            self.parent.on_select(xloc, yloc, iplot)
        else:
            # catch all
            self.parent.on_select(xloc, yloc, iplot)

    def leave(self, event):
        """ Turn off the cursors as we move mouse outside axes or figure """

        for line in self.vlines + self.hlines: line.set_visible(False)
        self.dynamic_update()

    def on_motion(self, event):

        # The following limit when motion events are triggered

        if not event.inaxes and self.mode == '':
            return
        if not event.inaxes and not self._button_pressed:
            # When we are in pan or zoom or level and the mouse strays outside
            # the canvas, we still want to have events even though the xyloc
            # can not be properly calculated. We are reporting other things
            # that do not need xylocs for like width/level values.
            return

        xloc, yloc = self.get_bounded_xyloc(event)

        iplot = None
        if self._xypress:
            item = self._xypress[0]
            axis, iplot = item[0], item[1]
        else:
            axis = None
            for i, axes in enumerate(self.parent.axes):
                if axes == event.inaxes:
                    iplot = i

        if self.mode == 'pan/zoom' and (self._button_pressed == 1 or self._button_pressed == 3):
            if iplot is not None:
                self.parent.on_panzoom_motion(xloc, yloc, iplot)
        elif self.mode == 'zoom rect' and (self._button_pressed == 1 or self._button_pressed == 3):
            if iplot is None:
                pass
        elif self.mode == 'width/level' and self._button_pressed == 3:
            if iplot is not None:
                self.parent.on_level_motion(xloc, yloc, iplot)
        elif self.mode == '':
            if iplot is not None:
                # no toggle buttons on
                self.parent.on_motion(xloc, yloc, iplot)

                if self._cursors and self.vertOn:
                    for line in self.vlines:
                        line.set_xdata((xloc, xloc))
                        line.set_visible(True)
                if self._cursors and self.horizOn:
                    for line in self.hlines:
                        line.set_ydata((yloc, yloc))
                        line.set_visible(True)
                self.dynamic_update()
        else:
            if iplot is not None:
                # catch all
                self.parent.on_motion(xloc, yloc, iplot)

    def get_bounded_xyloc(self, event):
        if not event.inaxes:
            return 0, 0

        xloc, yloc = event.xdata, event.ydata

        # bound these values to be inside the size of the image.
        # - a pan event could yield negative locations.
        x0, y0, x1, y1 = event.inaxes.dataLim.bounds
        xmin, xmax = x0 + 0.5, x0 + 0.5 + x1 - 1
        ymin, ymax = y0 + 0.5, y0 + 0.5 + y1 - 1  # position swap due to 0,0 location 'upper'
        xloc = max(0, min(xmax, xloc))
        yloc = max(0, min(ymax, yloc))

        return xloc, yloc

    def dynamic_update(self):
        d = self._idle
        self._idle = False
        if d:
            self.canvas.draw()
            self._idle = True

    def draw_rubberband(self, event, x0, y0, x1, y1):
        """
        Draw a rectangle rubberband to indicate zoom limits.
        Note that it is not guaranteed that ``x0 <= x1`` and ``y0 <= y1``.
        'adapted from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/189744'

        """
        canvas = self.canvas
        dc = wx.ClientDC(canvas)

        # Set logical function to XOR for rubberbanding
        dc.SetLogicalFunction(wx.XOR)

        # Set dc brush and pen
        # Here I set brush and pen to white and grey respectively
        # You can set it to your own choices

        # The brush setting is not really needed since we
        # dont do any filling of the dc. It is set just for
        # the sake of completion.

        wbrush = wx.Brush(wx.Colour(255, 255, 255), wx.TRANSPARENT)
        wpen = wx.Pen(wx.Colour(200, 200, 200), 1, wx.SOLID)
        dc.SetBrush(wbrush)
        dc.SetPen(wpen)

        dc.ResetBoundingBox()
        dc.BeginDrawing()
        height = self.canvas.figure.bbox.height
        y1 = height - y1
        y0 = height - y0

        if y1 < y0: y0, y1 = y1, y0
        if x1 < y0: x0, x1 = x1, x0

        w = x1 - x0
        h = y1 - y0

        rect = int(x0), int(y0), int(w), int(h)
        try:
            lastrect = self.lastrect
        except AttributeError:
            pass
        else:
            dc.DrawRectangle(*lastrect)  # erase last
        self.lastrect = rect
        dc.DrawRectangle(*rect)
        dc.EndDrawing()

    def set_status_bar(self, statbar):
        self.statbar = statbar

    def set_message(self, s):
        if self.statbar is not None:
            pass
            # self.statbar.SetStatusText(s,0)



# ***************** Embed Icon Catalog Starts Here *******************

z_catalog = {}

#----------------------------------------------------------------------
z_crosshair = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAAIBJREFUWEftlVEKgCAQBfcgXau/TtB9OkF/XbJ8sBsimlToFryB"
    "+RJxQGXl70yqG5vqBgMYwAAGrGpXhuBYEGvNwUF7Qaw1xwJSXgVgotmDuhL3XQtYgum+nHPw"
    "xD3gDrWA5lhAzi4B7t8wBvcN3bAH5QYDGMAABmCiPZ5qH0DkAEnpVB1zVLSlAAAAAElFTkSu"
    "QmCC")
z_catalog['crosshair'] = z_crosshair

#----------------------------------------------------------------------
z_back = PyEmbeddedImage(
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
z_catalog['back'] = z_back

#----------------------------------------------------------------------
z_contrast = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAASFJREFUSEvNlUEOgjAQRYG1J2GnNzDs4AZuPYbn4TBwCYgegZ3B"
    "6jzTEpHSgrHGl/yElOlMOzNto38gEe1ER9FJi2/G+PcxGxHOLqL7jM4ibLBdxV5kddz3vWqa"
    "RpVlqfI8v8VxzDi2zFnEQXQVTZyjd6qqUmmaKvnHHOY6YRWzzpGNrutUlmUmyOxOyKMr30/N"
    "QRC9E3xYa0KxrE5f5aKua5UkCXb4GkG7eVePfBRFwS7orlEL09NWh+/yQXdp261ogIMzcWaT"
    "j7ZtTQB8DizKP/LBOdG2ozp8M4CxHQUInqLgRQ7eprCoDi5cBw2CXxUQ9LIzrL2ub2uuawOr"
    "sKbrGw+OgTxSLDpiEkjr4yfzFdqNnubg4AzxzdikFX9MFD0Aw8HVrGb5SeoAAAAASUVORK5C"
    "YII=")
z_catalog['contrast'] = z_contrast

#----------------------------------------------------------------------
z_filesave = PyEmbeddedImage(
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
z_catalog['filesave'] = z_filesave

#----------------------------------------------------------------------
z_forward = PyEmbeddedImage(
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
z_catalog['forward'] = z_forward

#----------------------------------------------------------------------
z_home = PyEmbeddedImage(
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
z_catalog['home'] = z_home

#----------------------------------------------------------------------
z_move = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAadEVYdFNvZnR3YXJlAFBhaW50Lk5F"
    "VCB2My41LjEwMPRyoQAAAQlJREFUSEu1kzEOwjAUQ3swDgATOzssSAyIAQYWRiZWNgaOwP2C"
    "HMnVj3FoI7XDq1In307y2y6lNCtWrLHcnhNQ/R9WdMD4+HhnWkKsqND89vpkWkKsGFHz1hAr"
    "ktP9mRabQ2a1u/TmGFPHGq2LWNEBMwZgrPM1rOh2NRRQO8mPgHt1Buv9tb8WjHUeuutJ8cKG"
    "uoAhUOMa3w9ork10uyXxVPwINCQ/ormCYi5WMOdqYkheOHsAiCGTXxFhCAqiPgbUqDkoFgEs"
    "cAFxt+5U0NUcFC9k1h+txlBADSsS7ApmgE0E8SOo7ZxYMcLG05y4hjqsqGjIWHNgRQdDWsyB"
    "FWvAuMUcWHE6UvcF5OFXiwd3+VIAAAAASUVORK5CYII=")
z_catalog['move'] = z_move

#----------------------------------------------------------------------
z_subplots = PyEmbeddedImage(
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
z_catalog['subplots'] = z_subplots

#----------------------------------------------------------------------
z_zoom_to_rect = PyEmbeddedImage(
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
z_catalog['zoom_to_rect'] = z_zoom_to_rect

        


# Test Code ------------------------------------------------------------------

class ImageNavPanel(wx.Panel):
    """
    The ImageNavPanel has a Figure and a Canvas and 'n' Axes. The user defines
    the number of axes on Init and this number cannot be changed thereafter.
    However, the user can change the number of axes displayed in the Figure.

    Axes are specified on Init because the zoom and widlev actions
    need an axes to attach to initialize properly.

    on_size events simply set a flag, and the actual resizing of the figure is
    triggered by an Idle event.

    """

    # Set _EVENT_DEBUG to True to activate printing of messages to stdout
    # during events.
    _EVENT_DEBUG = False

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
        wx.Panel.__init__(self, parent, **kwargs)

        self.figure = Figure(figsize=(4, 4), dpi=100)

        self.cmap = [cm.gray for i in range(naxes)]
        self.imageid = [None for i in range(naxes)]
        self.width = [WIDMAX for i in range(naxes)]
        self.level = [LEVSTR for i in range(naxes)]
        self.vmax = [WIDMAX for i in range(naxes)]
        self.vmin = [LEVSTR for i in range(naxes)]
        self.vmax_orig = [WIDMAX for i in range(naxes)]
        self.vmin_orig = [LEVSTR for i in range(naxes)]

        # here we create the required naxes, add them to the figure, but we
        # also keep a permanent reference to each axes so they can be added
        # or removed from the figure as the user requests 1-N axes be displayed
        self.naxes = naxes
        self.axes = []

        if naxes > 1:
            iaxes = np.arange(naxes - 1, dtype=np.uint16) + 1
            for i in iaxes:
                if layout == 'vertical':
                    self.axes.append(self.figure.add_subplot(naxes, 1, 1))
                    self.axes.append(self.figure.add_subplot(naxes, 1, i + 1, sharex=self.axes[0], sharey=self.axes[0]))
                else:
                    self.axes.append(self.figure.add_subplot(1, naxes, 1))
                    self.axes.append(self.figure.add_subplot(1, naxes, i + 1, sharex=self.axes[0], sharey=self.axes[0]))
        self.all_axes = list(self.axes)

        self.canvas = FigureCanvas(self, -1, self.figure)
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

        if not data or len(data) != naxes:
            data = self._default_data()
        self.set_data(data)
        self.update(no_draw=True)  # we don't have a canvas yet

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        if layout == 'vertical':
            self.sizer_canvas = wx.BoxSizer(wx.VERTICAL)
            self.sizer_canvas.Add(self.canvas, 1, wx.EXPAND, 10)
        else:
            self.sizer_canvas = wx.BoxSizer(wx.HORIZONTAL)
            self.sizer_canvas.Add(self.canvas, 1, wx.EXPAND, 10)

        self.sizer.Add(self.sizer_canvas, 1, wx.TOP | wx.LEFT | wx.EXPAND)

        # Capture the paint message
        self.Bind(wx.EVT_PAINT, self.on_paint)

        self.toolbar = ImageNav(self.canvas, self,
                                vertOn=vertOn,
                                horizOn=horizOn,
                                lcolor=lcolor,
                                lw=lw)

        self.toolbar.Realize()
        if wx.Platform == '__WXMAC__':
            # Mac platform (OSX 10.3, MacPython) does not seem to cope with
            # having a toolbar in a sizer. This work-around gets the buttons
            # back, but at the expense of having the toolbar at the top
            self.SetToolBar(self.toolbar)
        else:
            # On Windows platform, default window size is incorrect, so set
            # toolbar width to figure width.
            #            tw, th = self.toolbar.GetSize()
            #            fw, fh = self.canvas.GetSize()
            # By adding toolbar in sizer, we are able to put it at the bottom
            # of the frame - so appearance is closer to GTK version.
            # As noted above, doesn't work for Mac.
            #            self.toolbar.SetSize(wx.Size(fw, th))
            # self.sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
            # self.sizer.Add(self.toolbar, 0, wx.ALIGN_CENTER | wx.EXPAND)
            self.sizer.Add(self.toolbar, 0, wx.EXPAND)

        # update the axes menu on the toolbar
        self.toolbar.update()

        self.SetSizer(self.sizer)
        self.Fit()

        # Always link scroll events, but only handle them if on_scroll()
        # is overloaded by the user.
        self.scroll_id = self.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.keypress_id = self.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.keyrelease_id = self.canvas.mpl_connect('key_release_event', self.on_key_release)
        self.shift_is_held = False

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
        for i, axes in enumerate(self.axes):
            if axes == event.inaxes:
                iplot = i
        self.on_scroll(event.button, event.step, iplot)

    def _default_data(self):
        data = []
        for i in range(self.naxes):
            data.append([self._dist(128), ])
        return data

    def _dist(self, n, m=None):
        """
        Return a rectangular array in which each pixel = euclidian
        distance from the origin.

        """
        n1 = n
        m1 = n if not m else m
        x = np.arange(n1)
        x = np.array([val ** 2 if val < (n1 - val) else (n1 - val) ** 2 for val in x])

        a = np.ndarray((n1, m1), float)  # Make array

        for i in range(int((m1 / 2) + 1)):  # Row loop
            y = np.sqrt(x + i ** 2.0)  # Euclidian distance
            a[i, :] = y  # Insert the row
            if i != 0:
                a[m1 - i, :] = y  # Symmetrical

        return a

    def on_paint(self, event):
        # this is necessary or the embedded MPL canvas does not show
        self.canvas.draw()
        event.Skip()

    # =======================================================
    #
    #           Default Event Handlers
    #
    # =======================================================

    def on_scroll(self, button, step, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_scroll,     button=' + str(button) + '  step=' + str(step) + '  Index = ' + str(iplot))

    def on_motion(self, xloc, yloc, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_motion,          xloc=' + str(xloc) + '  yloc=' + str(yloc) + '  Index = ' + str(iplot))

    def on_select(self, xloc, yloc, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_select,          xloc=' + str(xloc) + '  yloc=' + str(yloc) + '  Index = ' + str(iplot))

    def on_panzoom_release(self, xloc, yloc):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_panzoom_release, xloc=' + str(xloc) + '  yloc=' + str(yloc))

    def on_panzoom_motion(self, xloc, yloc, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_panzoom_motion,  xloc=' + str(xloc) + '  yloc=' + str(yloc) + '  Index = ' + str(iplot))

    def on_level_press(self, xloc, yloc, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_level_press,     xloc=' + str(xloc) + '  yloc=' + str(yloc) + '  Index = ' + str(iplot))

    def on_level_release(self, xloc, yloc):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_level_release,   xloc=' + str(xloc) + '  yloc=' + str(yloc))

    def on_level_motion(self, xloc, yloc, iplot):
        """ placeholder, overload for user defined event handling """
        self._dprint('debug::on_level_motion,    xloc=' + str(xloc) + '  yloc=' + str(yloc) + '  Index = ' + str(iplot))

    # =======================================================
    #
    #           User Accessible Data Functions
    #
    # =======================================================

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
                        raise ValueError("must have a data array in the dict sent to set_data()")
                    if 'alpha' not in list(dat.keys()):
                        dat['alpha'] = 1.0
                    if 'cmap' not in list(dat.keys()):
                        dat['cmap'] = self.cmap[i]
                    if 'vmax' not in list(dat.keys()):
                        dat['vmax'] = dat['data'].max()
                    if 'vmin' not in list(dat.keys()):
                        dat['vmin'] = dat['data'].min()
                    if 'keep_norm' not in list(dat.keys()):
                        dat['keep_norm'] = keep_norm
                    if 'patches' not in list(dat.keys()):
                        dat['patches'] = None
                    if 'lines' not in dat.keys():
                        dat['lines'] = None
                else:
                    # Only data in this item, so add all default values
                    dat = {'data': dat,
                           'alpha': 1.0,
                           'cmap': self.cmap[i],
                           'vmax': dat.max(),
                           'vmin': dat.min(),
                           'keep_norm': keep_norm,
                           'patches': None,
                           'lines': None
                           }

                item[j] = dat

        if index:
            if index < 0 or index >= self.naxes:
                raise ValueError("index must be within that number of axes in the plot_panel")

            if data[0][0]['data'].shape != self.data[0][0]['data'].shape:
                raise ValueError("new data must be a same number of spectral points as existing data")

            # even though we are inserting into an index, I want to force users
            # to submit a dict in a list of lists format so it is consistent
            # with submitting a whole new set of data (below). We just take the
            # first list of dicts from the submitted data and put it in the
            # index position
            self.data[index] = data[0]

        else:
            if len(data) != self.naxes:
                raise ValueError("data must be a list with naxes number of ndarrays")
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

                    if d.shape != data[0][0]['data'].shape:
                        raise ValueError("all ndarrays must have same dimensions")

            self.data = data

        for i, data in enumerate(self.data):
            if not data[0]['keep_norm']:
                self.vmax_orig[i] = data[0]['vmax']
                self.vmin_orig[i] = data[0]['vmin']
                self.vmax[i] = data[0]['vmax']
                self.vmin[i] = data[0]['vmin']

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
                yold, xold = -1, -1

            # axes.images.clear()
            for item in list(axes.images):
                item.remove()

            ddict = self.data[i][0]
            data = ddict['data'].copy()
            alpha = ddict['alpha']
            cmap = ddict['cmap']
            vmax = self.vmax[i]
            vmin = self.vmin[i]
            patches = ddict['patches']
            lines = ddict['lines']

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
                # self.imageid[i].axes.patches.clear()
                for item in list(self.imageid[i].axes.patches):
                    item.remove()

            if len(self.imageid[i].axes.lines) > 2:
                # should be two lines in here for cursor tracking
                self.imageid[i].axes.lines = self.imageid[i].axes.lines[0:2]
            if lines is not None:
                for line in lines:
                    self.imageid[i].axes.add_line(line)

            if xold != xwid or yold != ywid or force_bounds:
                xmin -= 0.5  # this centers the image range to voxel centers
                ymin -= 0.5
                # Set new bounds for dataLims to x,y extent of data in the
                # new image. On reset zoom this is how far we reset the limits.
                axes.ignore_existing_data_limits = True
                axes.update_datalim([[xmin, ymin], [xmin + xwid, ymin + ywid]])

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
                        raise ValueError("index in list outside naxes range")
                else:
                    raise ValueError("too many index entries")
            else:
                if index < self.naxes:
                    indices = [index]
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
        
        
class DemoImagePanel(ImageNavPanel):
    """Plots several lines in distinct colors."""

    # Activate event messages
    _EVENT_DEBUG = True
    
    def __init__( self, parent, tab, statusbar, **kwargs ):
        # statusbar has to be here for NavigationToolbar3Wx to discover on init()
        self.statusbar = statusbar
        # initiate plotter
        sizer = ImageNavPanel.__init__(self, parent,
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
         
        self.nb = wx.Notebook(self, -1, style=wx.BK_BOTTOM)
         
        panel1 = wx.Panel(self.nb, -1)
         
        self.view = DemoImagePanel(panel1, self, self.statusbar, naxes=2, data=data)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.view, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        panel1.SetSizer(sizer)
        self.view.Fit()    
     
        self.nb.AddPage(panel1, "One")

    def menuData(self):
        return [("&File", (
                    ("&Quit",    "Quit the program",  self.on_close),)),
                 ("Tests", (
                     ("Placeholder",    "non-event",  self.on_placeholder),))]

    def on_close(self, event):
        dlg = wx.MessageDialog(self, 
            "Do you really want to close this application?",
            "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            self.Destroy()

    def on_placeholder(self, event):
        print("Event handler for on_placeholder - not implemented")

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




if __name__ == '__main__':

    app   = wx.App( False )
    frame = MyFrame( title='WxPython and Matplotlib', size=(600,600) )
    frame.Show()
    app.MainLoop()
