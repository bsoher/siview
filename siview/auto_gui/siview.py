# -*- coding: UTF-8 -*-
#
# generated by wxGlade 1.0.5 on Wed Oct 18 15:31:36 2023
#

import wx

# begin wxGlade: dependencies
from wx.lib.agw.floatspin import FloatSpin, EVT_FLOATSPIN, FS_LEFT, FS_RIGHT, FS_CENTRE, FS_READONLY
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class SiviewUI(wx.Panel):
    def __init__(self, *args, **kwds):
        # begin wxGlade: SiviewUI.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        sizer_2 = wx.BoxSizer(wx.VERTICAL)

        sizer_30 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(sizer_30, 0, wx.ALL | wx.EXPAND, 4)

        label_11 = wx.StaticText(self, wx.ID_ANY, "Source:")
        sizer_30.Add(label_11, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)

        self.TextSource = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.TextSource.SetMinSize((-1,-1))
        sizer_30.Add(self.TextSource, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, "Scale: ")
        sizer_30.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)

        self.FloatScale = FloatSpin(self, wx.ID_ANY, value=0.0, digits=3, min_val=0.0, max_val=100.0, increment=1.0, agwStyle=FS_LEFT, style=0)
        sizer_30.Add(self.FloatScale, 0, wx.EXPAND, 0)

        self.SplitterWindow = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_3D | wx.SP_BORDER)
        self.SplitterWindow.SetMinimumPaneSize(20)
        sizer_2.Add(self.SplitterWindow, 1, wx.EXPAND, 0)

        self.PaneLeft = wx.Panel(self.SplitterWindow, wx.ID_ANY)

        sizer_7 = wx.BoxSizer(wx.VERTICAL)

        self.notebook_1 = wx.Notebook(self.PaneLeft, wx.ID_ANY, style=0)
        sizer_7.Add(self.notebook_1, 1, wx.EXPAND, 0)

        self.TabImages = wx.Panel(self.notebook_1, wx.ID_ANY)
        self.notebook_1.AddPage(self.TabImages, "Images")

        sizer_7_copy = wx.BoxSizer(wx.VERTICAL)

        self.PanelImage = wx.Panel(self.TabImages, wx.ID_ANY)
        sizer_7_copy.Add(self.PanelImage, 1, wx.EXPAND, 0)

        sizer_4 = wx.StaticBoxSizer(wx.StaticBox(self.TabImages, wx.ID_ANY, "Image Controls"), wx.VERTICAL)
        sizer_7_copy.Add(sizer_4, 0, wx.EXPAND, 0)

        grid_sizer_1 = wx.FlexGridSizer(2, 2, 2, 2)
        sizer_4.Add(grid_sizer_1, 0, wx.EXPAND, 0)

        self.LabelTop = wx.StaticText(self.TabImages, wx.ID_ANY, "Time Index [sec]:")
        grid_sizer_1.Add(self.LabelTop, 0, 0, 0)

        self.SliderTop = wx.Slider(self.TabImages, wx.ID_ANY, 0, 0, 10)
        grid_sizer_1.Add(self.SliderTop, 1, wx.EXPAND, 0)

        self.LabelBottom = wx.StaticText(self.TabImages, wx.ID_ANY, "Fit Results Map:")
        grid_sizer_1.Add(self.LabelBottom, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, 0)

        self.ChoiceResults = wx.Choice(self.TabImages, wx.ID_ANY, choices=["Mask", "Peak", "R1", "R2", "Delay1", "Delay2", "Base", "Chis", "Badfit"])
        self.ChoiceResults.SetSelection(0)
        grid_sizer_1.Add(self.ChoiceResults, 0, wx.EXPAND, 0)

        grid_sizer_3 = wx.FlexGridSizer(2, 5, 4, 4)
        sizer_4.Add(grid_sizer_3, 1, wx.ALL | wx.EXPAND, 6)

        self.label_18 = wx.StaticText(self.TabImages, wx.ID_ANY, "Map - Floor: ")
        grid_sizer_3.Add(self.label_18, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, 0)

        self.SpinMapFloor = wx.SpinCtrl(self.TabImages, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_3.Add(self.SpinMapFloor, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_19 = wx.StaticText(self.TabImages, wx.ID_ANY, "    Ceil: ")
        grid_sizer_3.Add(label_19, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.SpinMapCeil = wx.SpinCtrl(self.TabImages, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_3.Add(self.SpinMapCeil, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.ButtonMapReset = wx.Button(self.TabImages, wx.ID_ANY, "Reset", style=wx.BU_EXACTFIT)
        grid_sizer_3.Add(self.ButtonMapReset, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.label_20 = wx.StaticText(self.TabImages, wx.ID_ANY, "MRI - Floor: ")
        grid_sizer_3.Add(self.label_20, 0, wx.ALIGN_RIGHT, 0)

        self.SpinTimeFloor = wx.SpinCtrl(self.TabImages, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_3.Add(self.SpinTimeFloor, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_19_copy = wx.StaticText(self.TabImages, wx.ID_ANY, "    Ceil: ")
        grid_sizer_3.Add(label_19_copy, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.SpinTimeCeil = wx.SpinCtrl(self.TabImages, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_3.Add(self.SpinTimeCeil, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.ButtonTimeReset = wx.Button(self.TabImages, wx.ID_ANY, "Reset", style=wx.BU_EXACTFIT)
        grid_sizer_3.Add(self.ButtonTimeReset, 0, 0, 0)

        self.TabSettings = wx.Panel(self.notebook_1, wx.ID_ANY)
        self.notebook_1.AddPage(self.TabSettings, "Settings")

        sizer_5 = wx.BoxSizer(wx.VERTICAL)

        self.panel_2 = wx.Panel(self.TabSettings, wx.ID_ANY)
        sizer_5.Add(self.panel_2, 1, wx.EXPAND, 0)

        sizer_8 = wx.BoxSizer(wx.VERTICAL)

        sizer_9 = wx.StaticBoxSizer(wx.StaticBox(self.panel_2, wx.ID_ANY, "Time Course Model"), wx.HORIZONTAL)
        sizer_8.Add(sizer_9, 0, wx.ALL | wx.EXPAND, 4)

        self.label_13 = wx.StaticText(self.panel_2, wx.ID_ANY, "Model : ")
        sizer_9.Add(self.label_13, 0, wx.ALIGN_CENTER_VERTICAL | wx.BOTTOM | wx.TOP, 2)

        self.ChoiceTimeCourseModel = wx.Choice(self.panel_2, wx.ID_ANY, choices=["Exponential Rate", "Power Rate"])
        self.ChoiceTimeCourseModel.SetSelection(0)
        sizer_9.Add(self.ChoiceTimeCourseModel, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_10 = wx.StaticBoxSizer(wx.StaticBox(self.panel_2, wx.ID_ANY, "Optimization Weight Function"), wx.HORIZONTAL)
        sizer_8.Add(sizer_10, 0, wx.ALL | wx.EXPAND, 4)

        label_14 = wx.StaticText(self.panel_2, wx.ID_ANY, "Function : ")
        sizer_10.Add(label_14, 0, wx.ALIGN_CENTER_VERTICAL | wx.BOTTOM | wx.TOP, 2)

        self.ChoiceWeightFunction = wx.Choice(self.panel_2, wx.ID_ANY, choices=["Even", "Symmetric Half-Sine", "Asymmetric Half-Sine"])
        self.ChoiceWeightFunction.SetSelection(0)
        sizer_10.Add(self.ChoiceWeightFunction, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_15 = wx.StaticText(self.panel_2, wx.ID_ANY, "Vertical Scale : ")
        sizer_10.Add(label_15, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        self.FloatWeightScale = FloatSpin(self.panel_2, wx.ID_ANY, value=0.0, digits=3, min_val=0.0, max_val=100.0, increment=1.0, agwStyle=FS_LEFT, style=0)
        sizer_10.Add(self.FloatWeightScale, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_12 = wx.StaticText(self.panel_2, wx.ID_ANY, "Fitting Parameter Values ")
        sizer_8.Add(label_12, 0, wx.ALL, 4)

        grid_sizer_2 = wx.FlexGridSizer(7, 4, 4, 4)
        sizer_8.Add(grid_sizer_2, 1, wx.EXPAND, 0)

        grid_sizer_2.Add((20, 20), 0, 0, 0)

        label_2 = wx.StaticText(self.panel_2, wx.ID_ANY, "Min Value")
        grid_sizer_2.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_3 = wx.StaticText(self.panel_2, wx.ID_ANY, "Start Value")
        grid_sizer_2.Add(label_3, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_4 = wx.StaticText(self.panel_2, wx.ID_ANY, "Max Value")
        grid_sizer_2.Add(label_4, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        label_5 = wx.StaticText(self.panel_2, wx.ID_ANY, "Peak [% max Val]")
        grid_sizer_2.Add(label_5, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)

        self.SpinPeakMin = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "10", min=1, max=100, style=0)
        grid_sizer_2.Add(self.SpinPeakMin, 0, 0, 0)

        self.SpinPeakStart = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "10", min=1, max=100, style=0)
        grid_sizer_2.Add(self.SpinPeakStart, 0, 0, 0)

        self.SpinPeakMax = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "10", min=1, max=100, style=0)
        grid_sizer_2.Add(self.SpinPeakMax, 0, 0, 0)

        label_6 = wx.StaticText(self.panel_2, wx.ID_ANY, "Delay 1 [sec]")
        grid_sizer_2.Add(label_6, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)

        self.SpinDelay1Min = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "10", min=1, max=100, style=0)
        grid_sizer_2.Add(self.SpinDelay1Min, 0, 0, 0)

        self.SpinDelay1Start = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "10", min=1, max=100, style=0)
        grid_sizer_2.Add(self.SpinDelay1Start, 0, 0, 0)

        self.SpinDelay1Max = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "10", min=1, max=100, style=0)
        grid_sizer_2.Add(self.SpinDelay1Max, 0, 0, 0)

        self.LabelDelay2 = wx.StaticText(self.panel_2, wx.ID_ANY, "Delay 2 [sec]")
        grid_sizer_2.Add(self.LabelDelay2, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)

        self.SpinDelay2Min = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinDelay2Min, 0, 0, 0)

        self.SpinDelay2Start = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinDelay2Start, 0, 0, 0)

        self.SpinDelay2Max = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinDelay2Max, 0, 0, 0)

        label_8 = wx.StaticText(self.panel_2, wx.ID_ANY, "Rate In [sec]")
        grid_sizer_2.Add(label_8, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)

        self.SpinRate1Min = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinRate1Min, 0, 0, 0)

        self.SpinRate1Start = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinRate1Start, 0, 0, 0)

        self.SpinRate1Max = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinRate1Max, 0, 0, 0)

        self.LabelRate2 = wx.StaticText(self.panel_2, wx.ID_ANY, "Rate Out [sec]")
        grid_sizer_2.Add(self.LabelRate2, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)

        self.SpinRate2Min = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinRate2Min, 0, 0, 0)

        self.SpinRate2Start = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinRate2Start, 0, 0, 0)

        self.SpinRate2Max = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinRate2Max, 0, 0, 0)

        label_10 = wx.StaticText(self.panel_2, wx.ID_ANY, "Base [% noise Val]")
        grid_sizer_2.Add(label_10, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)

        self.SpinBaseMin = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinBaseMin, 0, 0, 0)

        self.SpinBaseStart = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinBaseStart, 0, 0, 0)

        self.SpinBaseMax = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        grid_sizer_2.Add(self.SpinBaseMax, 0, 0, 0)

        sizer_11 = wx.StaticBoxSizer(wx.StaticBox(self.panel_2, wx.ID_ANY, "Strip Output - Chop Settings"), wx.VERTICAL)
        sizer_8.Add(sizer_11, 0, wx.ALL | wx.EXPAND, 8)

        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11.Add(sizer_12, 1, wx.EXPAND, 0)

        self.label_16 = wx.StaticText(self.panel_2, wx.ID_ANY, "Chop Horiz [vox]:")
        sizer_12.Add(self.label_16, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.SpinCanvasChopX = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        sizer_12.Add(self.SpinCanvasChopX, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.label_17 = wx.StaticText(self.panel_2, wx.ID_ANY, "      Chop Vert [vox]:")
        sizer_12.Add(self.label_17, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.SpinCanvasChopY = wx.SpinCtrl(self.panel_2, wx.ID_ANY, "", min=0, max=100, style=0)
        sizer_12.Add(self.SpinCanvasChopY, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7.Add(sizer_3, 0, wx.ALL | wx.EXPAND, 6)

        self.ButtonResetMask = wx.Button(self.PaneLeft, wx.ID_ANY, "Reset Mask")
        sizer_3.Add(self.ButtonResetMask, 0, wx.EXPAND, 0)

        self.ButtonFitAll = wx.Button(self.PaneLeft, wx.ID_ANY, "Fit All Voxels")
        sizer_3.Add(self.ButtonFitAll, 0, wx.EXPAND, 0)

        self.ButtonFitSlice = wx.Button(self.PaneLeft, wx.ID_ANY, "Fit This Slice")
        sizer_3.Add(self.ButtonFitSlice, 0, wx.EXPAND, 0)

        self.ButtonFitCurrent = wx.Button(self.PaneLeft, wx.ID_ANY, "Fit Current Voxel")
        sizer_3.Add(self.ButtonFitCurrent, 1, wx.EXPAND, 0)

        self.PaneRight = wx.Panel(self.SplitterWindow, wx.ID_ANY)

        sizer_6 = wx.BoxSizer(wx.VERTICAL)

        self.PanelPlot = wx.Panel(self.PaneRight, wx.ID_ANY)
        sizer_6.Add(self.PanelPlot, 1, wx.EXPAND, 0)

        self.PaneRight.SetSizer(sizer_6)

        self.panel_2.SetSizer(sizer_8)

        self.TabSettings.SetSizer(sizer_5)

        grid_sizer_1.AddGrowableCol(1)

        self.TabImages.SetSizer(sizer_7_copy)

        self.PaneLeft.SetSizer(sizer_7)

        self.SplitterWindow.SplitVertically(self.PaneLeft, self.PaneRight)

        self.SetSizer(sizer_2)

        self.Layout()

        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.on_splitter, self.SplitterWindow)
        self.Bind(wx.EVT_CHOICE, self.on_results, self.ChoiceResults)
        self.Bind(wx.EVT_SPINCTRL, self.on_map_range, self.SpinMapFloor)
        self.Bind(wx.EVT_SPINCTRL, self.on_map_range, self.SpinMapCeil)
        self.Bind(wx.EVT_BUTTON, self.on_map_reset, self.ButtonMapReset)
        self.Bind(wx.EVT_SPINCTRL, self.on_time_range, self.SpinTimeFloor)
        self.Bind(wx.EVT_SPINCTRL, self.on_time_range, self.SpinTimeCeil)
        self.Bind(wx.EVT_BUTTON, self.on_time_reset, self.ButtonTimeReset)
        self.Bind(wx.EVT_CHOICE, self.on_time_course_model, self.ChoiceTimeCourseModel)
        self.Bind(wx.EVT_CHOICE, self.on_weight_function, self.ChoiceWeightFunction)
        self.Bind(wx.EVT_SPINCTRL, self.on_peak_min, self.SpinPeakMin)
        self.Bind(wx.EVT_SPINCTRL, self.on_peak_start, self.SpinPeakStart)
        self.Bind(wx.EVT_SPINCTRL, self.on_peak_max, self.SpinPeakMax)
        self.Bind(wx.EVT_SPINCTRL, self.on_delay1_min, self.SpinDelay1Min)
        self.Bind(wx.EVT_SPINCTRL, self.on_delay1_start, self.SpinDelay1Start)
        self.Bind(wx.EVT_SPINCTRL, self.on_delay1_max, self.SpinDelay1Max)
        self.Bind(wx.EVT_SPINCTRL, self.on_delay2_min, self.SpinDelay2Min)
        self.Bind(wx.EVT_SPINCTRL, self.on_delay2_start, self.SpinDelay2Start)
        self.Bind(wx.EVT_SPINCTRL, self.on_delay2_max, self.SpinDelay2Max)
        self.Bind(wx.EVT_SPINCTRL, self.on_rate1_min, self.SpinRate1Min)
        self.Bind(wx.EVT_SPINCTRL, self.on_rate1_start, self.SpinRate1Start)
        self.Bind(wx.EVT_SPINCTRL, self.on_rate1_max, self.SpinRate1Max)
        self.Bind(wx.EVT_SPINCTRL, self.on_rate2_min, self.SpinRate2Min)
        self.Bind(wx.EVT_SPINCTRL, self.on_rate2_start, self.SpinRate2Start)
        self.Bind(wx.EVT_SPINCTRL, self.on_rate2_max, self.SpinRate2Max)
        self.Bind(wx.EVT_SPINCTRL, self.on_base_min, self.SpinBaseMin)
        self.Bind(wx.EVT_SPINCTRL, self.on_base_start, self.SpinBaseStart)
        self.Bind(wx.EVT_SPINCTRL, self.on_base_max, self.SpinBaseMax)
        self.Bind(wx.EVT_SPINCTRL, self.on_chop, self.SpinCanvasChopX)
        self.Bind(wx.EVT_SPINCTRL, self.on_chop, self.SpinCanvasChopY)
        self.Bind(wx.EVT_BUTTON, self.on_reset_mask, self.ButtonResetMask)
        self.Bind(wx.EVT_BUTTON, self.on_fit_all, self.ButtonFitAll)
        self.Bind(wx.EVT_BUTTON, self.on_fit_slice, self.ButtonFitSlice)
        self.Bind(wx.EVT_BUTTON, self.on_fit_current, self.ButtonFitCurrent)
        # end wxGlade

    def on_splitter(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_splitter' not implemented!")
        event.Skip()

    def on_results(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_results' not implemented!")
        event.Skip()

    def on_map_range(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_map_range' not implemented!")
        event.Skip()

    def on_map_reset(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_map_reset' not implemented!")
        event.Skip()

    def on_time_range(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_time_range' not implemented!")
        event.Skip()

    def on_time_reset(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_time_reset' not implemented!")
        event.Skip()

    def on_time_course_model(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_time_course_model' not implemented!")
        event.Skip()

    def on_weight_function(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_weight_function' not implemented!")
        event.Skip()

    def on_peak_min(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_peak_min' not implemented!")
        event.Skip()

    def on_peak_start(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_peak_start' not implemented!")
        event.Skip()

    def on_peak_max(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_peak_max' not implemented!")
        event.Skip()

    def on_delay1_min(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_delay1_min' not implemented!")
        event.Skip()

    def on_delay1_start(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_delay1_start' not implemented!")
        event.Skip()

    def on_delay1_max(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_delay1_max' not implemented!")
        event.Skip()

    def on_delay2_min(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_delay2_min' not implemented!")
        event.Skip()

    def on_delay2_start(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_delay2_start' not implemented!")
        event.Skip()

    def on_delay2_max(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_delay2_max' not implemented!")
        event.Skip()

    def on_rate1_min(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_rate1_min' not implemented!")
        event.Skip()

    def on_rate1_start(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_rate1_start' not implemented!")
        event.Skip()

    def on_rate1_max(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_rate1_max' not implemented!")
        event.Skip()

    def on_rate2_min(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_rate2_min' not implemented!")
        event.Skip()

    def on_rate2_start(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_rate2_start' not implemented!")
        event.Skip()

    def on_rate2_max(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_rate2_max' not implemented!")
        event.Skip()

    def on_base_min(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_base_min' not implemented!")
        event.Skip()

    def on_base_start(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_base_start' not implemented!")
        event.Skip()

    def on_base_max(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_base_max' not implemented!")
        event.Skip()

    def on_chop(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_chop' not implemented!")
        event.Skip()

    def on_reset_mask(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_reset_mask' not implemented!")
        event.Skip()

    def on_fit_all(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_fit_all' not implemented!")
        event.Skip()

    def on_fit_slice(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_fit_slice' not implemented!")
        event.Skip()

    def on_fit_current(self, event):  # wxGlade: SiviewUI.<event_handler>
        print("Event handler 'on_fit_current' not implemented!")
        event.Skip()

# end of class SiviewUI

class MyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((800, 1000))
        self.SetTitle("frame_1")

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        self.SiviewUI = SiviewUI(self, wx.ID_ANY)
        sizer_1.Add(self.SiviewUI, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_1)

        self.Layout()
        # end wxGlade

# end of class MyFrame
