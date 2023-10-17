#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules


# Our modules
import siview.mri_timeseries as mri_timeseries
import siview.mri_siview as mri_siview

from siview.common.import_ import Importer



class TimeseriesImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        for element in self.root.getiterator("timeseries"):
            self.found_count += 1

            timeseries = mri_timeseries.Timeseries(element)
            
            self.imported.append(timeseries)

        self.post_import()
        
        return self.imported
    
    
class WashsimImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        
        for element in self.root.getiterator("timeseries"):
            self.found_count += 1

            timeseries = mri_timeseries.Timeseries(element)
            
            self.imported.append(timeseries)

        for element in self.root.getiterator("washsim"):
            self.found_count += 1

            washsim = mri_washsim.Washsim(element)
            
            self.imported.append(washsim)

        self.post_import()
        
        return self.imported
