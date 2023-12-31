#!/usr/bin/env python
# -*- coding: utf-8 -*-
# generated by wxGlade HG on Mon Jan 24 17:37:17 2011

import wx

# begin wxGlade: extracode
# end wxGlade



class PulseProjectBrowser(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: PulseProjectBrowser.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetSize((652, 414))
        self.SetTitle("Pulse Project Browser")

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_5, 1, wx.EXPAND, 0)

        sizer_7 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Pulse Projects"), wx.VERTICAL)
        sizer_5.Add(sizer_7, 1, wx.EXPAND, 0)

        self.ListPulseProjects = wx.ListBox(self, wx.ID_ANY, choices=[], style=0)
        sizer_7.Add(self.ListPulseProjects, 5, wx.EXPAND, 0)

        grid_sizer_1 = wx.FlexGridSizer(2, 2, 10, 5)
        sizer_7.Add(grid_sizer_1, 1, wx.BOTTOM | wx.EXPAND | wx.TOP, 10)

        grid_sizer_1.Add((0, 0), 0, 0, 0)

        grid_sizer_1.Add((0, 0), 0, 0, 0)

        grid_sizer_1.Add((0, 0), 0, 0, 0)

        grid_sizer_1.Add((0, 0), 0, 0, 0)

        sizer_10 = wx.BoxSizer(wx.VERTICAL)
        sizer_5.Add(sizer_10, 1, wx.EXPAND, 0)

        sizer_13 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_13, 1, wx.EXPAND, 0)

        self.LabelHtml = wx.StaticText(self, wx.ID_ANY, "At runtime this label is replaced by an HTML control")
        sizer_13.Add(self.LabelHtml, 0, 0, 0)

        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10.Add(sizer_11, 0, wx.EXPAND, 0)

        self.LabelOpenCancelPlaceholder = wx.StaticText(self, wx.ID_ANY, "The Open and Cancel buttons are \nadded in the dialog init, not here.")
        sizer_11.Add(self.LabelOpenCancelPlaceholder, 0, 0, 0)

        grid_sizer_1.AddGrowableCol(1)

        self.SetSizer(sizer_1)

        self.Layout()

        self.Bind(wx.EVT_LISTBOX, self.on_list_click, self.ListPulseProjects)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_double_click, self.ListPulseProjects)
        # end wxGlade

    def on_list_double_click(self, event): # wxGlade: PulseProjectBrowser.<event_handler>
        print("Event handler `on_list_double_click' not implemented!")
        event.Skip()

    def on_list_click(self, event): # wxGlade: PulseProjectBrowser.<event_handler>
        print("Event handler `on_list_click' not implemented!")
        event.Skip()

# end of class PulseProjectBrowser


if __name__ == "__main__":
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    dialog_1 = PulseProjectBrowser(None, -1, "")
    app.SetTopWindow(dialog_1)
    dialog_1.Show()
    app.MainLoop()
