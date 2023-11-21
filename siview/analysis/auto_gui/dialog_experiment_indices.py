# -*- coding: UTF-8 -*-
#
# generated by wxGlade 1.0.0 on Fri Jan 22 23:00:30 2021
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
        self.SetTitle("Select Experiment Dimension")

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_3, 0, wx.ALL | wx.EXPAND, 10)

        self.LabelInstructions = wx.StaticText(self, wx.ID_ANY, "Select the experiment dimension (loop indices) you want to use.")
        sizer_3.Add(self.LabelInstructions, 0, wx.EXPAND, 0)

        grid_sizer_1 = wx.FlexGridSizer(2, 3, 5, 15)
        sizer_1.Add(grid_sizer_1, 1, wx.ALL | wx.EXPAND, 10)

        self.LabelLoop1 = wx.StaticText(self, wx.ID_ANY, "LabelLoop1")
        grid_sizer_1.Add(self.LabelLoop1, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.LabelLoop2 = wx.StaticText(self, wx.ID_ANY, "LabelLoop2")
        grid_sizer_1.Add(self.LabelLoop2, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.LabelLoop3 = wx.StaticText(self, wx.ID_ANY, "LabelLoop3")
        grid_sizer_1.Add(self.LabelLoop3, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.ListLoop1 = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT | wx.LC_SINGLE_SEL)
        grid_sizer_1.Add(self.ListLoop1, 0, wx.EXPAND, 0)

        self.ListLoop2 = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT | wx.LC_SINGLE_SEL)
        grid_sizer_1.Add(self.ListLoop2, 0, wx.EXPAND, 0)

        self.ListLoop3 = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT | wx.LC_SINGLE_SEL)
        grid_sizer_1.Add(self.ListLoop3, 0, wx.EXPAND, 0)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_2, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.LabelOKCancelPlaceholder = wx.StaticText(self, wx.ID_ANY, "LabelOKCancelPlaceholder")
        sizer_2.Add(self.LabelOKCancelPlaceholder, 0, wx.ALIGN_BOTTOM, 0)

        grid_sizer_1.AddGrowableRow(1)
        grid_sizer_1.AddGrowableCol(0)
        grid_sizer_1.AddGrowableCol(1)
        grid_sizer_1.AddGrowableCol(2)

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)

        self.Layout()

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list_select, self.ListLoop1)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list_select, self.ListLoop2)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list_select, self.ListLoop3)
        # end wxGlade

    def on_list_select(self, event):  # wxGlade: MyDialog.<event_handler>
        print("Event handler 'on_list_select' not implemented!")
        event.Skip()

# end of class MyDialog
