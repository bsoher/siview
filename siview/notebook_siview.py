#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import os
import sys

# 3rd party modules 
import wx
import wx.html
#import wx.aui as aui
import wx.lib.agw.aui as aui        # NB. wx.aui version throws odd wxWidgets exception on Close/Exit


# Our modules
import siview.default_content as default_content
import siview.tab_siview as tab_siview
import siview.common.wx_util as wx_util
import siview.common.notebook_base as notebook_base



class NotebookSiview(notebook_base.BaseAuiNotebook):
    
    # Need to check if we are in a PyInstaller bundle here
    if getattr(sys, 'frozen', False):
        _path = sys._MEIPASS
    else:
        # Don't want app install directory here in case we are running this as an
        # executable script, in which case we get the python27/Scripts directory.
        _path = os.path.dirname(tab_siview.__file__)
    
    _path = os.path.join(_path, "siviewscreen.png")
    
    WELCOME_TAB_TEXT = """
    <html><body>
    <h1>Welcome to "%s"</h1>
    <img src="%s" alt="Time Series Plots" />
    <p><b>Currently there are no Timeseries loaded.</b></p>
    <p>You can use the Timeseries menu to browse for data.</p>
    </body></html>
    """ % (default_content.APP_NAME, _path)
    # I tidy up my namespace by deleting this temporary variable.
    del _path
    
    
    def __init__(self, top):

        notebook_base.BaseAuiNotebook.__init__(self, top)

        self.top    = top
        self.count  = 0
        
        self.show_welcome_tab()

        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_tab_close)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_tab_closed)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
        

    #=======================================================
    #
    #           Global and Menu Event Handlers 
    #
    #=======================================================

    def on_menu_view_option(self, event):
        if self.active_tab:
            self.active_tab.on_menu_view_option(event)

    # def on_menu_view_output(self, event):
    #     if self.active_tab:
    #         self.active_tab.on_menu_view_output(event)
    #
    # def on_menu_output_by_slice(self, event):
    #     self.active_tab.on_menu_output_by_slice(event)
    #
    # def on_menu_output_by_voxel(self, event):
    #     self.active_tab.on_menu_output_by_voxel(event)
    #
    # def on_menu_output_to_dicom(self, event):
    #     self.active_tab.on_menu_output_to_dicom(event)


    def on_tab_changed(self, event):

        self._set_title()
            
        if self.active_tab:
            self.active_tab.on_activation()
            
            
    def on_tab_close(self, event):
        """
        This is a two step event. Here we give the user a chance to cancel 
        the Close action. If user selects to continue, then the on_tab_closed()
        event will also fire.  
        
        """
        msg = "Are you sure you want to close this SIView?"
        if wx.MessageBox(msg, "Close SIView", wx.YES_NO, self) != wx.YES:
            event.Veto()


    def on_tab_closed(self, event):        
        """
        At this point the tab is already closed and the dataset removed from
        memory.        
        """
        if not self.tabs:
            self.show_welcome_tab()

        self._set_title()


    #=======================================================
    #
    #           Public methods shown below
    #             in alphabetical order 
    #
    #=======================================================

    def add_siview_tab(self, dataset=None, out_dicom=None):

        # If the welcome tab is open, close it.
        if self.is_welcome_tab_open:
            self.remove_tab(index=0)

        self.count += 1
        name = "SIView%d" % self.count

        # create new notebook tab with process controls 
        tab = tab_siview.TabSiview(self, self.top, dataset, out_dicom=out_dicom)
        self.AddPage(tab, name, True)


    def close_siview(self):
        if self.active_tab:
            wx_util.send_close_to_active_tab(self)


    # def set_mask(self, mask):
    #     if self.active_tab:
    #         self.active_tab.set_mask(mask)

    #=======================================================
    #
    #           Internal methods shown below
    #             in alphabetical order 
    #
    #=======================================================

    def _set_title(self):
        title = default_content.APP_NAME

        if self.active_tab:
            tab = self.active_tab

            if tab.dataset:
                title += " - " + tab.dataset.dataset_filename

        wx.GetApp().GetTopWindow().SetTitle(title)


    def global_poll_phase(self, poll_labels, delta, voxel, do_zero=True):
        """
        Phase 0 and phase 1 are parameters that can affect one or more
        view panels in tabs within a dataset tab. They can be changed using
        either widgets or mouse canvas events. For a given dataset, these
        events only change one phase 0 or phase 1 variable located in the
        block_spectral object.

        These values can also be changed "between dataset tabs" due to the
        PlotB, option on the Spectral tab when combined with the Sync check
        box. So, I've located these methods at the notebook level so that one
        tab does not ever talk directly to another tab, but just to a parent
        (or grandparent).

        The "poll_labels" list whether one or more datasets are involved
        from the calling event. This is typically only more than one label
        when the event is from the Spectral tab.

        """
        # determine which dataset tabs are affected by this event
        poll_labels, view_labels = self._get_poll_and_view_labels(poll_labels)
        # update values in dataset tabs
        for label in poll_labels:
            tab = self.get_tab_by_label(label)
            if do_zero:
                tab.set_phase_0(delta, voxel)
            else:
                tab.set_phase_1(delta, voxel)

        # refresh views in tabs where values have changed
        for label in view_labels:
            tab = self.get_tab_by_label(label)
            if do_zero:
                tab.set_phase_0_view(voxel)
            else:
                tab.set_phase_1_view(voxel)


    def _get_poll_and_view_labels(self, poll_labels):
        """
        This is a helper function used by the global_poll_xxx() methods.

        We poll all dataset tabs to determine which are affected by the event
        triggered by the calling dataset(s) listed in the poll_labels list as
        it is sent into the method.

        If a dataset is in the list, and it has a PlotB selected, the PlotB
        dataset is added to the list.

        If a dataset is synched to a PlotB that is in the list, then that
        dataset is added to the list.

        We also poll tab labels for ANY dataset that is involved in this event
        whether in PlotA or PlotB, because we need to refresh those views.

        Unique values for both the poll_list and view_list are returned.

        """
        view_labels = list(poll_labels)
        for label in list(self.top.datasets.keys()):
            tab_dataset  = self.get_tab_by_label(label)
            tab_spectral = tab_dataset.get_tab("spectral")
            if label in poll_labels:
                poll_labels.append(tab_dataset.indexAB[0])
                if tab_spectral.do_sync:
                    poll_labels.append(tab_dataset.indexAB[1])
                    view_labels.append(tab_dataset.indexAB[1])
                view_labels.append(tab_dataset.indexAB[0])
            if tab_dataset.indexAB[1] in poll_labels:
                poll_labels.append(tab_dataset.indexAB[1])
                if tab_spectral.do_sync:
                    poll_labels.append(tab_dataset.indexAB[0])
                view_labels.append(tab_dataset.indexAB[0])
                view_labels.append(tab_dataset.indexAB[1])
        poll_labels = list(set(poll_labels))
        view_labels = list(set(view_labels))
        return poll_labels, view_labels