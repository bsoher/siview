#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# Our modules 


"""
When we need to create an app's INI file, this is the content it
uses. 

This module contains just three objects:
1) the name of the application
2) the name of the configuration file to use
3) a dict called DEFAULT_INI_FILE_CONTENT. The dict has a key 
   for the INI file ("timeseries", etc.) and associated with 
   that key is the default content for that INI file. 
"""

APP_NAME = "WashSim"
INI_NAME = "washsim.ini"

# The dict contents are mostly strings 

DEFAULT_INI_FILE_CONTENT = {

###############################      Washsim

    "washsim" : """
# The Washsim config file.

# Colors are described in matplotlib's terms. Matplotlib understands standard
# color names like "red", "black", "blue", etc.
# One can also specify the color using an HTML hex string like #eeefff.
# If you use a string like that, you must put it in quotes, otherwise the
# hash mark will get interpreted as a comment marker. For example, to set
# a background to pale yellow:
#    bgcolor = "#f3f3bb"


[main]
left = 40
top = 40
width = 1200
height = 800

[main_prefs]
bgcolor = "#ffffff"

""" 

,}

