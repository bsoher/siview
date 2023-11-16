#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import os

# 3rd party modules

# Our modules
import common.util.config as config
import common.default_content as default_content
import common.util.misc as misc



def get_window_coordinates(window_name):
    """A shortcut for the Config object method of the same name."""
    config = Config()
    return config.get_window_coordinates(window_name)

def get_path(type_):
    """A shortcut for the Config object method of the same name."""
    config = Config()
    return config.get_path(type_)

def set_path(type_, path):
    """A shortcut for the Config object method of the same name."""
    config = Config()
    config.set_path(type_, path)
    config.write()
    
def get_last_export_path():
    """A shortcut for the Config object method of the same name."""
    config = Config()
    return config.get_last_export_path()

def set_last_export_path(path):
    """A shortcut for the Config object method of the same name."""
    config = Config()
    config.set_last_export_path(path)
    config.write()
    
def get_last_import_path():
    """A shortcut for the Config object method of the same name."""
    config = Config()
    return config.get_last_import_path()

def set_last_import_path(path):
    """A shortcut for the Config object method of the same name."""
    config = Config()
    config.set_last_import_path(path)
    config.write()

   

class Config(config.BaseConfig):

    def __init__(self, filename=default_content.INI_NAME):
        config.BaseConfig.__init__(self, filename)

    @property
    def show_wx_inspector(self):
        return ("debug" in self) and                        \
               ("show_wx_inspector" in self["debug"]) and   \
               self["debug"].as_bool("show_wx_inspector")


    def get_last_export_path(self):
        """
        Returns the last path from which the user exported a file via this
        application. The path is always fully-qualified and is never blank.
        """
        path = ""
        
        if "general" in self:
            path = self["general"].get("last_export_path", "")

        if not os.path.exists(path):
            path = misc.get_documents_dir()

        return path


    def set_last_export_path(self, path):
        """
        Sets the last path to which the user exported a file via this
        application.
        """
        path = os.path.abspath(path)
        if "general" not in self:
            self["general"] = { }
        self["general"]["last_export_path"] = path


    def get_last_import_path(self):
        """
        Returns the last path from which the user imported a file via this
        application. The path is always fully-qualified and is never blank.
        """
        path = ""
        
        if "general" in self:
            path = self["general"].get("last_import_path", "")

        if not os.path.exists(path):
            path = misc.get_documents_dir()

        return path


    def set_last_import_path(self, path):
        """
        Sets the last path from which the user imported a file via this
        application.
        """
        path = os.path.abspath(path)
        if "general" not in self:
            self["general"] = { }
        self["general"]["last_import_path"] = path
        
        
    def get_path(self, type_):
        """
        Given a file type (as a string), returns the most recent path from 
        which the user imported that type of file. If we can't find a path 
        in the INI file, we make one up.
        
        The type param is freeform and typically something like 
        "import_vasf" or "open_viff".
        
        This function always returns a path, and that path is always 
        fully-qualified and guaranteed to exist.
        """
        path = ""
        
        if "paths" in self:
            path = self["paths"].get(type_, "")

        if not os.path.exists(path):
            path = misc.get_documents_dir()

        return path


    def set_path(self, type_, path):
        """
        Given a file type (as a string) and a path, writes the path to the
        INI file under that file type.

        The type param is freeform and typically something like 
        "import_vasf" or "open_viff".
        """
        path = os.path.abspath(path)
        if "paths" not in self:
            self["paths"] = { }

        self["paths"][type_] = path
        
        