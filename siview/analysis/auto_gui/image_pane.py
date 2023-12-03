# -*- coding: UTF-8 -*-
#
# generated by wxGlade 1.0.5 on Sun Dec  3 18:38:14 2023
#

import wx

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class ImagePaneUI(wx.Panel):
    def __init__(self, *args, **kwds):
        # begin wxGlade: ImagePaneUI.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        sizer_6 = wx.BoxSizer(wx.VERTICAL)

        self.PanelImagePane = wx.Panel(self, wx.ID_ANY)
        sizer_6.Add(self.PanelImagePane, 1, wx.EXPAND, 0)

        sizer_11 = wx.BoxSizer(wx.VERTICAL)

        self.ImageSplitterWindow = wx.SplitterWindow(self.PanelImagePane, wx.ID_ANY)
        self.ImageSplitterWindow.SetMinimumPaneSize(20)
        sizer_11.Add(self.ImageSplitterWindow, 1, wx.EXPAND, 0)

        self.window_1_pane_1 = wx.Panel(self.ImageSplitterWindow, wx.ID_ANY)

        sizer_4 = wx.BoxSizer(wx.VERTICAL)

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_4.Add(sizer_2, 1, wx.ALL | wx.EXPAND, 1)

        sizer_12 = wx.StaticBoxSizer(wx.StaticBox(self.window_1_pane_1, wx.ID_ANY, "Source Selection"), wx.HORIZONTAL)
        sizer_2.Add(sizer_12, 0, wx.ALL | wx.EXPAND, 2)

        label_5 = wx.StaticText(self.window_1_pane_1, wx.ID_ANY, "Stack 1:")
        sizer_12.Add(label_5, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        self.ComboSourceStack1 = wx.ComboBox(self.window_1_pane_1, wx.ID_ANY, choices=["None"], style=wx.CB_DROPDOWN)
        self.ComboSourceStack1.SetSelection(0)
        sizer_12.Add(self.ComboSourceStack1, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        label_6 = wx.StaticText(self.window_1_pane_1, wx.ID_ANY, "Stack 2:")
        sizer_12.Add(label_6, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 14)

        self.ComboSourceStack2 = wx.ComboBox(self.window_1_pane_1, wx.ID_ANY, choices=["None"], style=wx.CB_DROPDOWN)
        self.ComboSourceStack2.SetSelection(0)
        sizer_12.Add(self.ComboSourceStack2, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        SizerImagePlot = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(SizerImagePlot, 1, wx.EXPAND, 0)

        self.PanelImagePlot = wx.Panel(self.window_1_pane_1, wx.ID_ANY)
        SizerImagePlot.Add(self.PanelImagePlot, 1, wx.EXPAND, 0)

        self.window_1_pane_2 = wx.Panel(self.ImageSplitterWindow, wx.ID_ANY)

        sizer_3 = wx.StaticBoxSizer(wx.StaticBox(self.window_1_pane_2, wx.ID_ANY, ""), wx.VERTICAL)

        sizer_13 = wx.StaticBoxSizer(wx.StaticBox(self.window_1_pane_2, wx.ID_ANY, "Image Controls"), wx.VERTICAL)
        sizer_3.Add(sizer_13, 0, wx.ALL | wx.EXPAND, 1)

        grid_sizer_3 = wx.FlexGridSizer(1, 7, 2, 2)
        sizer_13.Add(grid_sizer_3, 0, 0, 0)

        self.LabelStackSlicew1 = wx.StaticText(self.window_1_pane_2, wx.ID_ANY, "Stack1 - Slice:")
        grid_sizer_3.Add(self.LabelStackSlicew1, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 2)

        self.SpinSliceIndex1 = wx.SpinCtrl(self.window_1_pane_2, wx.ID_ANY, "0", min=0, max=100, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        grid_sizer_3.Add(self.SpinSliceIndex1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.label_20 = wx.StaticText(self.window_1_pane_2, wx.ID_ANY, "Floor1:")
        grid_sizer_3.Add(self.label_20, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        self.FloatStackFloor1 = wx.SpinCtrlDouble(self.window_1_pane_2, wx.ID_ANY, initial=0.0, min=-1000.0, max=1000.0, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        self.FloatStackFloor1.SetDigits(2)
        grid_sizer_3.Add(self.FloatStackFloor1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_21 = wx.StaticText(self.window_1_pane_2, wx.ID_ANY, "Ceil1:")
        grid_sizer_3.Add(label_21, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        self.FloatStackCeil1 = wx.SpinCtrlDouble(self.window_1_pane_2, wx.ID_ANY, initial=0.0, min=-1000.0, max=1000.0, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        self.FloatStackCeil1.SetDigits(2)
        grid_sizer_3.Add(self.FloatStackCeil1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.ButtonStackReset1 = wx.Button(self.window_1_pane_2, wx.ID_ANY, "Reset", style=wx.BU_EXACTFIT)
        grid_sizer_3.Add(self.ButtonStackReset1, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 2)

        grid_sizer_4 = wx.FlexGridSizer(1, 7, 2, 2)
        sizer_13.Add(grid_sizer_4, 0, 0, 0)

        self.LabelStackSlice2 = wx.StaticText(self.window_1_pane_2, wx.ID_ANY, "Stack2 - Slice:")
        grid_sizer_4.Add(self.LabelStackSlice2, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 2)

        self.SpinSliceIndex2 = wx.SpinCtrl(self.window_1_pane_2, wx.ID_ANY, "0", min=0, max=100, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        grid_sizer_4.Add(self.SpinSliceIndex2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.label_22 = wx.StaticText(self.window_1_pane_2, wx.ID_ANY, "Floor2:")
        grid_sizer_4.Add(self.label_22, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        self.FloatStackFloor2 = wx.SpinCtrlDouble(self.window_1_pane_2, wx.ID_ANY, initial=0.0, min=-1000.0, max=1000.0, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        self.FloatStackFloor2.SetDigits(2)
        grid_sizer_4.Add(self.FloatStackFloor2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_23 = wx.StaticText(self.window_1_pane_2, wx.ID_ANY, "Ceil2:")
        grid_sizer_4.Add(label_23, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        self.FloatStackCeil2 = wx.SpinCtrlDouble(self.window_1_pane_2, wx.ID_ANY, initial=0.0, min=-1000.0, max=1000.0, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        self.FloatStackCeil2.SetDigits(2)
        grid_sizer_4.Add(self.FloatStackCeil2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.ButtonStackReset2 = wx.Button(self.window_1_pane_2, wx.ID_ANY, "Reset", style=wx.BU_EXACTFIT)
        grid_sizer_4.Add(self.ButtonStackReset2, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 2)

        grid_sizer_4.AddGrowableCol(1)

        grid_sizer_3.AddGrowableCol(1)

        self.window_1_pane_2.SetSizer(sizer_3)

        self.window_1_pane_1.SetSizer(sizer_4)

        self.ImageSplitterWindow.SplitHorizontally(self.window_1_pane_1, self.window_1_pane_2)

        self.PanelImagePane.SetSizer(sizer_11)

        self.SetSizer(sizer_6)

        self.Layout()

        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.on_splitter, self.ImageSplitterWindow)
        self.Bind(wx.EVT_COMBOBOX, self.on_source_stack1, self.ComboSourceStack1)
        self.Bind(wx.EVT_COMBOBOX, self.on_source_stack2, self.ComboSourceStack2)
        self.Bind(wx.EVT_SPINCTRL, self.on_slice_index1, self.SpinSliceIndex1)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_slice_index1, self.SpinSliceIndex1)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_stack_range1, self.FloatStackFloor1)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_stack_range1, self.FloatStackFloor1)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_stack_range1, self.FloatStackCeil1)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_stack_range1, self.FloatStackCeil1)
        self.Bind(wx.EVT_BUTTON, self.on_stack_reset1, self.ButtonStackReset1)
        self.Bind(wx.EVT_SPINCTRL, self.on_slice_index2, self.SpinSliceIndex2)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_slice_index2, self.SpinSliceIndex2)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_stack_range2, self.FloatStackFloor2)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_stack_range2, self.FloatStackFloor2)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_stack_range2, self.FloatStackCeil2)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_stack_range2, self.FloatStackCeil2)
        self.Bind(wx.EVT_BUTTON, self.on_stack_reset2, self.ButtonStackReset2)
        # end wxGlade

    def on_splitter(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_splitter' not implemented!")
        event.Skip()

    def on_source_stack1(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_source_stack1' not implemented!")
        event.Skip()

    def on_source_stack2(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_source_stack2' not implemented!")
        event.Skip()

    def on_slice_index1(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_slice_index1' not implemented!")
        event.Skip()

    def on_stack_range1(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_stack_range1' not implemented!")
        event.Skip()

    def on_stack_reset1(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_stack_reset1' not implemented!")
        event.Skip()

    def on_slice_index2(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_slice_index2' not implemented!")
        event.Skip()

    def on_stack_range2(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_stack_range2' not implemented!")
        event.Skip()

    def on_stack_reset2(self, event):  # wxGlade: ImagePaneUI.<event_handler>
        print("Event handler 'on_stack_reset2' not implemented!")
        event.Skip()

# end of class ImagePaneUI

class MyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((684, 956))
        self.SetTitle("frame_1")

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        self.ImagePaneUI = ImagePaneUI(self, wx.ID_ANY)
        sizer_1.Add(self.ImagePaneUI, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_1)

        self.Layout()
        # end wxGlade

# end of class MyFrame
