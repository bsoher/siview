# -*- coding: UTF-8 -*-
#
# generated by wxGlade 1.0.0 on Fri Jan 22 23:00:14 2021
#

import wx

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class MyDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyDialog.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetTitle("Dataset Browser")

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(sizer_2, 1, wx.ALL | wx.EXPAND, 10)

        self.Listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=0)
        sizer_2.Add(self.Listbox, 1, wx.EXPAND, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(sizer_3, 0, wx.EXPAND | wx.TOP, 10)

        self.LabelOkCancelPlaceholder = wx.StaticText(self, wx.ID_ANY, "LabelOkCancelPlaceholder")
        sizer_3.Add(self.LabelOkCancelPlaceholder, 0, 0, 0)

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_LISTBOX, self.on_list_selection, self.Listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_list_double_click, self.Listbox)
        # end wxGlade

    def on_list_selection(self, event):  # wxGlade: MyDialog.<event_handler>
        print("Event handler 'on_list_selection' not implemented!")
        event.Skip()

    def on_list_double_click(self, event):  # wxGlade: MyDialog.<event_handler>
        print("Event handler 'on_list_double_click' not implemented!")
        event.Skip()

# end of class MyDialog
