#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.

# Dependencies
#
# numpy
# scipy
# nibabel
# wxpython
# matplotlib
# - pyparsing (for Matplotlib)
# - python-dateutil (for Matplotlib)
# pydicom 


# Python modules

import os
import sys
import webbrowser
import struct

# 3rd party modules
import wx
import wx.adv as wx_adv
import wx.lib.agw.aui as aui        # NB. wx.aui version throws odd wxWidgets exception on Close/Exit
try:
    import pydicom
except ImportError:
    import dicom as pydicom
import numpy as np

#import wx.lib.agw.multidirdialog as MDD
import siview.common.multidirdialog as MDD
import siview.common.dcmstack.dcmstack as dcmstack

# Our modules
import siview.util_menu as util_menu
import siview.util_import as util_import
import siview.dialog_export as dialog_export
import siview.mri_timeseries as mri_timeseries
import siview.default_content as default_content
import siview.notebook_siview as notebook_siview
import siview.util_siview_config as util_siview_config

import siview.common.misc as misc
import siview.common.export as export
import siview.common.wx_util as wx_util
import siview.common.local_nrrd as nrrd
import siview.common.common_dialogs as common_dialogs

from wx.lib.embeddedimage import PyEmbeddedImage

IS_WX2X = False

Mondrian = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAHFJ"
    "REFUWIXt1jsKgDAQRdF7xY25cpcWC60kioI6Fm/ahHBCMh+BRmGMnAgEWnvPpzK8dvrFCCCA"
    "coD8og4c5Lr6WB3Q3l1TBwLYPuF3YS1gn1HphgEEEABcKERrGy0E3B0HFJg7C1N/f/kTBBBA"
    "+Vi+AMkgFEvBPD17AAAAAElFTkSuQmCC")


    

class Main(wx.Frame):    
    def __init__(self, position, size):
        # Create a frame using values from our INI file.
        self._left,  self._top    = position
        self._width, self._height = size
    
        style = wx.CAPTION | wx.CLOSE_BOX | wx.MINIMIZE_BOX | \
                wx.MAXIMIZE_BOX | wx.SYSTEM_MENU | wx.RESIZE_BORDER | \
                wx.CLIP_CHILDREN

        wx.Frame.__init__(self, None, wx.ID_ANY, default_content.APP_NAME,
                          (self._left, self._top),
                          (self._width, self._height), style)

        # GUI Creation ----------------------------------------------

        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.SetIcon(Mondrian.GetIcon())

        self.statusbar = self.CreateStatusBar(4, 0)
        self.statusbar.SetStatusText("Ready")

        bar = util_menu.SiviewMenuBar(self)
        self.SetMenuBar(bar)
        util_menu.bar = bar

        self.build_panes()
        self.bind_events()

        
    def build_panes(self):
        
        self.notebook_siview = notebook_siview.NotebookSiview(self)

        # create center pane
        self._mgr.AddPane(self.notebook_siview, 
                          aui.AuiPaneInfo().
                          Name("notebook_siview").
                          CenterPane().
                          PaneBorder(False))
                          
        # "commit" all changes made to AuiManager
        self._mgr.Update()                          
                        

    def bind_events(self):
        self.Bind(wx.EVT_CLOSE, self.on_self_close)
        self.Bind(wx.EVT_SIZE, self.on_self_coordinate_change)
        self.Bind(wx.EVT_MOVE, self.on_self_coordinate_change)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)


    def on_erase_background(self, event):
        event.Skip()


    ##############                                    ############
    ##############       Menu handlers are below      ############
    ##############       in the order they appear     ############
    ##############             on the menu            ############
    ##############                                    ############

    ############    SIView menu

    def on_import_dicom(self, event):

        ini_name = "import_timeseries_dicom"
        default_path = util_siview_config.get_path(ini_name)

        title="Choose directory(s) with DICOM time series:"

        dlg = MDD.MultiDirDialog(self, title=title,
                                 defaultPath=default_path,
                                 agwStyle=MDD.DD_MULTIPLE|MDD.DD_DIR_MUST_EXIST)
        
        if dlg.ShowModal() == wx.ID_OK:
            
            msg = ""
            try:
                src_paths = dlg.GetPaths()
                paths     = src_paths
                
                if len(paths) < 6:
                    # could be Washin only, set flag
                    flag_washin_only = True
                else:
                    flag_washin_only = False
                
                all_filenames = []
                for path in paths:
                    # Enumerate the directory contents
                    filenames = os.listdir(path)
            
                    # Turn the filenames into fully-qualified filenames.
                    filenames = [os.path.join(path, filename) for filename in filenames]
            
                    # Filter out non-files
                    filenames = [filename for filename in filenames if os.path.isfile(filename)]
                    
                    all_filenames += filenames
                
                src_dcm  = pydicom.read_file(all_filenames[0])
                patid    = src_dcm.PatientID
                serdesc  = src_dcm.SeriesDescription
                studyuid = src_dcm.StudyInstanceUID
                
                set_study_uid = set()
                set_series_uid = set()
                
                my_stack = dcmstack.DicomStack(time_order='AcquisitionTime')
                for item in all_filenames:
                    src_dcm = pydicom.read_file(item)
                    set_study_uid.add(src_dcm.StudyInstanceUID)
                    set_series_uid.add(src_dcm.SeriesInstanceUID)
                    my_stack.add_dcm(src_dcm)
                    
                # collect data from one series to use as template for DICOM output
                #
                # 1. grab first directory
                # 2. fully qualify file names
                # 3. filter out non-file
                source_path = paths[0]
                fnames = os.listdir(source_path)
                fnames = [os.path.join(source_path, fname) for fname in fnames]
                fnames = [fname for fname in fnames if os.path.isfile(fname)]

                dicoms = []
                for item in fnames:
                    tmp = pydicom.read_file(item)
                    dicoms.append(tmp)
                    
                source_path, _ = os.path.split(source_path)
                
                out_dcm = { 'study_uid'   : list(set_study_uid),
                            'series_uid'  : list(set_series_uid),
                            'source_path' : source_path,
                            'dicom_files' : dicoms
                          }
            except Exception as e:
                msg = """Exception reading DICOM file: \n"%s".""" % str(e)
                #msg = """Unknown exception reading DICOM file "%s".""" % filename 

            if msg:
                common_dialogs.message(msg, default_content.APP_NAME+" - Import DICOM", common_dialogs.E_OK)
            else:
                # test if right dimensions
                msg  = ""
                dims = my_stack.get_data().shape
                if len(dims) != 4:
                    msg = """Data is not 4D, dim = "%s".""" % str(dims)
                elif dims[0] < 3:
                    msg = """Time series dimension too small, dim = "%s".""" % str(dims)
                
                if msg:
                    common_dialogs.message(msg, default_content.APP_NAME+" - Import DICOM", common_dialogs.E_OK)
                else:
                    path, _ = os.path.split(all_filenames[0])
                    path_up, _ = os.path.split(path)
                    # convert to timeseries
                    timeseries = mri_timeseries.Timeseries()
                    if flag_washin_only:
                        timeseries.time_course_model = 'Exponential Washin Only'
                    timeseries.import_from_dcmstack(my_stack, all_filenames, False, patid, serdesc, studyuid, path_up)

                    # call standard new tab create
                    self._import_file(timeseries, out_dicom=out_dcm)
                    
                    util_siview_config.set_path(ini_name, src_paths[0])
        
        dlg.Destroy()

        
    def _import_file(self, timeseries, out_dicom=None):

        if timeseries:
            wx.BeginBusyCursor()
            self.notebook_siview.Freeze()
            self.notebook_siview.add_siview_tab(timeseries=timeseries, out_dicom=out_dicom)
            self.notebook_siview.Thaw()
            self.notebook_siview.Layout()
            wx.EndBusyCursor()
            self.update_title()

   
    def on_import_mask_files(self, event):
        
        # New default dir is due to my mistake is sometimes opening the NRRD 
        # files under the last dicom dir by mistake ... no perfect answer here. 
        # ini_name = "import_mask_files"
        ini_name = "import_timeseries_dicom"
        default_path = util_siview_config.get_path(ini_name)

        filetype_filter="Masks NRRD format only (*.nrrd)|*.nrrd"
        filenames = common_dialogs.pickfile(filetype_filter=filetype_filter,
                                            multiple=True,
                                            default_path=default_path)
        if filenames:
            msg = ""
            masks = []
            opts  = []
            try:
                for filename in filenames:
                    data, options = nrrd.read(filename)
                    data = data[:,:,::-1]   # empirically determined
                    masks.append(data)
                    opts.append(options)
                    
            except IOError:
                msg = """I can't read the file "%s".""" % filename
            except:
                msg = """Unknown exception reading Mask NRRD file "%s".""" % filename 
    
            if msg:
                common_dialogs.message(msg, default_content.APP_NAME+" - Import Mask", common_dialogs.E_OK)
            else:
                # test if all masks have same dimensions
                for mask in masks:
                    if mask.shape != masks[0].shape:
                        msg = "Masks are not all the same shape."
                        break
                
                if msg:
                    common_dialogs.message(msg, default_content.APP_NAME+" - Import Mask", common_dialogs.E_OK)
                else:
                    # concatenate to one mask
                    mask = masks[0]
                    if len(masks) > 1:
                        for item in masks[1:]:
                            mask += item
                            
                    mask = mask.swapaxes(0,1)
                            
                    self.notebook_siview.set_mask(mask)

                    path, _ = os.path.split(filename)
                    util_siview_config.set_path(ini_name, path)
        
        
    
    def on_open(self, event):
        wx.BeginBusyCursor()

        ini_name = "save_viff"
        default_path = util_siview_config.get_path(ini_name)

        filetype_filter=default_content.APP_NAME+" (*.xml,*.xml.gz,*.viff,*.vif)|*.xml;*.xml.gz;*.viff;*.vif"
        filename = common_dialogs.pickfile(filetype_filter=filetype_filter,
                                            multiple=False,
                                            default_path=default_path)
        if filename:
            msg = ""
            try:
                importer = util_import.TimeseriesImporter(filename)
            except IOError:
                msg = """I can't read the file "%s".""" % filename
            except SyntaxError:
                msg = """The file "%s" isn't valid Vespa Interchange File Format.""" % filename

            if msg:
                common_dialogs.message(msg, "MRI_Timeseries - Open File", 
                                       common_dialogs.E_OK)
            else:
                # Time to rock and roll!
                wx.BeginBusyCursor()
                siview = importer.go()
                wx.EndBusyCursor()    

                if siview:
                    timeseries = siview[0]
    
                    self.notebook_siview.Freeze()
                    self.notebook_siview.add_siview_tab(timeseries=timeseries)
                    self.notebook_siview.Thaw()
                    self.notebook_siview.Layout()
                    self.update_title()
                    
                    path, _ = os.path.split(filename)
                    util_siview_config.set_path(ini_name, path)
                else:
                    msg = """The file "%s" didn't contain any MRI_Timeseries.""" % filename
                    common_dialogs.message(msg)
                
        wx.EndBusyCursor()                


    def on_save_siview(self, event, save_as=False):
        # This event is also called programmatically by on_save_as_viff().
        timeseries = self.notebook_siview.active_tab.timeseries

        filename = timeseries.timeseries_filename
        if filename and (not save_as):
            # This dataset already has a filename which means it's already
            # associated with a VIFF file. We don't bug the user for a 
            # filename, we just save it.
            pass
        else:
            if not filename:
                filename = timeseries.data_sources[0]
            path, filename = os.path.split(filename)
            # The default filename is the current filename with the extension
            # changed to ".xml".
            filename = os.path.splitext(filename)[0] + ".xml"

            filename = common_dialogs.save_as("Save As XML/VIFF (Vespa Interchange Format File)",
                                              "VIFF/XML files (*.xml)|*.xml",
                                              path, filename)

        if filename:
            timeseries.timeseries_filename = filename
        
            self._save_viff(timeseries)
        
        
    def on_save_as_siview(self, event):
        self.on_save_siview(event, True)        
        
        
    def on_close_siview(self, event):
        self.notebook_siview.close_siview()


    


    ############    View  menu
    
    # View options affect only the dataset and so it's up to the
    # experiment notebook to react to them.

    def on_menu_view_option(self, event):
        self.notebook_siview.on_menu_view_option(event)
        
    def on_menu_view_output(self, event):
        self.notebook_siview.on_menu_view_output(event)
        
    def on_menu_output_by_slice(self, event):
        self.notebook_siview.on_menu_output_by_slice(event)

    def on_menu_output_by_voxel(self, event):
        self.notebook_siview.on_menu_output_by_voxel(event)

    def on_menu_output_to_dicom(self, event):
        self.notebook_siview.on_menu_output_to_dicom(event)


    ############    Help menu

    def on_user_manual(self, event):
        pass
#        path = misc.get_install_directory()
#        path = os.path.join(path, "docs", "siview_user_manual.pdf")
#        wx_util.display_file(path)


    def on_help_online(self, event):
        pass 


    def on_about(self, event):

        version = misc.get_application_version()
        
        bit = str(8 * struct.calcsize('P')) + '-bit Python'
        info = wx_adv.AboutDialogInfo()
        info.SetVersion(version)  
        info.SetCopyright("Copyright 2014, Brian J. Soher. All rights reserved.")
        info.SetDescription(default_content.APP_NAME+" - analyzes ventilation time series data. \nRunning on "+bit)
        wx_adv.AboutBox(info)


    def on_show_inspection_tool(self, event):
        wx_util.show_wx_inspector(self)



    ############    Global Events
    
    def on_self_close(self, event):
        # I trap this so I can save my coordinates
        config = util_siview_config.Config()

        config.set_window_coordinates("main", self._left, self._top, 
                                      self._width, self._height)

        config.write()
        self.Destroy()


    def on_self_coordinate_change(self, event):
        # This is invoked for move & size events
        if self.IsMaximized() or self.IsIconized():
            # Bah, forget about this. Recording coordinates doesn't make sense
            # when the window is maximized or minimized. This is only a
            # concern on Windows; GTK and OS X don't produce move or size
            # events when a window is minimized or maximized.
            pass
        else:
            if event.GetEventType() == wx.wxEVT_MOVE:
                self._left, self._top = self.GetPosition()
            else:
                # This is a size event
                self._width, self._height = self.GetSize()


    
    ##############
    ##############   Public  functions  alphabetized  below
    ##############

    def update_title(self):
        """Updates the main window title to reflect the current dataset."""
        name = ""
        
        # Create an appropriate name for whatever is selected.
        tab = self.notebook_siview.active_tab
        if tab:
            filename = tab.timeseries.timeseries_filename
            fname = " - " + os.path.split(filename)[1] 

        self.SetTitle(default_content.APP_NAME + fname)
        
        
    ##############
    ##############   Private  functions  alphabetized  below
    ##############

    def _save_viff(self, timeseries):    
        msg = ""
        filename = timeseries.timeseries_filename
        comment  = "Processed in SIView version "+misc.get_application_version()
        try:
            export.export(filename, [timeseries], db=None, comment=comment, compress=False)
            path, _ = os.path.split(filename)
            util_siview_config.set_path("save_viff", path)
        except IOError:
            msg = """I can't write the file "%s".""" % filename

        if msg:
            common_dialogs.message(msg, style=common_dialogs.E_OK)
        else:
            # dataset.filename is an attribute set only at run-time to maintain
            # the name of the VIFF file that was read in rather than deriving 
            # a filename from the raw data filenames with *.xml appended. We 
            # set it here to indicate the current name that the dataset has 
            # been saved to VIFF file as.
            timeseries.timeseries_filename = filename
                    
        self.update_title()



#------------------------------------------------------------------------------

def main():

    # This function is for profiling with cProfile

    app = wx.App(0)
    
    # The app name must be set before the call to GetUserDataDir() below.
    app.SetAppName(default_content.APP_NAME)
    
    # Create the data directory if necessary - this version creates it in 
    # the Windows 'AppData/Local' location as opposed to the call to
    # wx.StandardPaths.Get().GetUserDataDir() which returns '/Roaming'
     
    data_dir = misc.get_data_dir()
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    
    # My settings are in the INI filename defined in 'default_content.py'
    config = util_siview_config.Config()
    position, size = config.get_window_coordinates("main")

    frame = Main(position, size)
    app.SetTopWindow(frame)
    frame.Show()
    app.MainLoop()    



if __name__ == "__main__":

    main()    
    
