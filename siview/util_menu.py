#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules
import wx

# Our modules
import siview.util_siview_config as util_siview_config
import siview.common.menu as common_menu


########################################################################
# This is a collection of menu-related constants, functions and utilities. 
# The function that builds the menu bar lives here, as does the menu 
# definition.
########################################################################


class ViewIds(common_menu.IdContainer):
    """A container for the ids of all of the menu items to which we need 
    explicit references.
    """
    ZERO_LINE_PLOT_SHOW = "replace me"
    ZERO_LINE_PLOT_TOP = "replace me"
    ZERO_LINE_PLOT_MIDDLE = "replace me"
    ZERO_LINE_PLOT_BOTTOM = "replace me"

    XAXIS_SHOW = "replace me"

    CMAP_AUTUMN = "replace me"
    CMAP_BLUES  = "replace me"
    CMAP_JET    = "replace me"
    CMAP_RDBU   = "replace me"
    CMAP_GRAY   = "replace me"
    CMAP_RDYLBU = "replace me"

    # MASK_TO_MOSAIC = "replace me"
    # FITS_TO_MOSAIC = "replace me"
    # MASK_TO_STRIP = "replace me"
    # FITS_TO_STRIP = "replace me"
    # MRI_TO_VSTRIP = "replace me"
    # MRI_TO_HSTRIP = "replace me"
    #
    # VIEW_TO_PNG = "replace me"
    # VIEW_TO_SVG = "replace me"
    # VIEW_TO_PDF = "replace me"
    # VIEW_TO_EPS = "replace me"
    #
    # VIEW_TO_CSV1 = "replace me"
    # VIEW_TO_CSV2 = "replace me"
    # VIEW_TO_DICOM = "replace me"


# When main creates an instance of PriorsetMenuBar(), it sets the variable
# below to that instance. It's a convenience. It's the same as 
# wx.GetApp().GetTopWindow().GetMenuBar(), but much easier to type.
bar = None


class SiviewMenuBar(common_menu.TemplateMenuBar):
    """
    A subclass of wx.MenuBar that adds some app-specific functions
    and constants.
    
    There should be only one instance of this class per invocation of the 
    app. It's a singleton class.
    """
    
    def __init__(self, main):
        common_menu.TemplateMenuBar.__init__(self, main)
        
        ViewIds.init_ids()

        # _get_menu_data() is called just once, right here. 
        siview, view, help = _get_menu_data(main)

        # Build the top-level menus that are always present. 
        siview   = common_menu.create_menu(main, "Timeseries", siview)
        view     = common_menu.create_menu(main, "&View", view)
        help     = common_menu.create_menu(main, "&Help", help)

        for menu in (siview, view, help):
            self.Append(menu, menu.label)

        ViewIds.enumerate_booleans(self.view_menu)


# ================    Module Internal Use Only    =======================


def _get_menu_data(main):
    # Note that wx treats the ids wx.ID_EXIT and wx.ID_ABOUT specially by 
    # moving them to their proper location on the Mac. wx will also change
    # the text of the ID_EXIT item to "Quit" as is standard under OS X. 
    # Quit is also the standard under Gnome but unfortunately wx doesn't seem
    # to change Exit --> Quit there, so our menu looks a little funny under
    # Gnome.

    study = (
                ("O&pen Siview...\tCTRL+O",   main.on_open),
                common_menu.SEPARATOR,
                ("S&ave\tCTRL+S",       main.on_save_siview),
                ("S&ave As...",         main.on_save_as_siview),
                common_menu.SEPARATOR,
                ("Close\tCTRL+W",       main.on_close_siview),
                common_menu.SEPARATOR,
                ("Import Processed CRT Data", main.on_import_data_crt),
                common_menu.SEPARATOR,
                ("&Exit",               main.on_self_close))

    view = (    
                ("Zero Line", (
                    ("Show",   main.on_menu_view_option, wx.ITEM_CHECK, ViewIds.ZERO_LINE_PLOT_SHOW),
                    common_menu.SEPARATOR,
                    ("Top",    main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.ZERO_LINE_PLOT_TOP),
                    ("Middle", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.ZERO_LINE_PLOT_MIDDLE),
                    ("Bottom", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.ZERO_LINE_PLOT_BOTTOM))),
                ("X-Axis", (
                    ("Show",   main.on_menu_view_option, wx.ITEM_CHECK, ViewIds.XAXIS_SHOW),
                    ("Show",   main.on_menu_view_option, wx.ITEM_CHECK, ViewIds.XAXIS_SHOW))),
                common_menu.SEPARATOR,
                ("Colormap - Results", (
                    ("autumn", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.CMAP_AUTUMN),
                    ("Blues",  main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.CMAP_BLUES),
                    ("jet",    main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.CMAP_JET),
                    ("RdBu",   main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.CMAP_RDBU),
                    ("gray",   main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.CMAP_GRAY),
                    ("RdYlBu", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.CMAP_RDYLBU))),
                common_menu.SEPARATOR)

                # ("Output Images", (   # BJS - NB. End parentheses are messed up by my hack and slash here.
                #     ("Mask to Mosaic", main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.MASK_TO_MOSAIC),
                #     ("Fits to Mosaic", main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.FITS_TO_MOSAIC),
                #     ("Mask to Strip",  main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.MASK_TO_STRIP),
                #     ("Fits to Strip",  main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.FITS_TO_STRIP),
                #     ("MRI to Strip Vert",  main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.MRI_TO_VSTRIP),
                #     ("MRI to Strip Horiz", main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.MRI_TO_HSTRIP))),
                # ("Output Plots", (
                #     ("Plot to PNG", main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.VIEW_TO_PNG),
                #     ("Plot to SVG", main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.VIEW_TO_SVG),
                #     ("Plot to EPS", main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.VIEW_TO_EPS),
                #     ("Plot to PDF", main.on_menu_view_output, wx.ITEM_NORMAL, ViewIds.VIEW_TO_PDF))),

    help = (
                ("&User Manual",          main.on_user_manual),
                ("&About", main.on_about, wx.ITEM_NORMAL, wx.ID_ABOUT),
           )

    if util_siview_config.Config().show_wx_inspector:
        help = list(help)
        help.append(common_menu.SEPARATOR)
        help.append( ("Show Inspection Tool", main.on_show_inspection_tool) )
    
    return (study, view, help)          

