#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules


# Our modules
from siview.common.util.import_ import Importer
import siview.analysis.mrs_dataset as mrs_dataset
import siview.analysis.mrs_metinfo as mrs_metinfo
import siview.common.mrs_prior as mrs_prior
import siview.common.mrs_data_raw as mrs_data_raw



class DatasetImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        for element in self.root.getiterator("dataset"):
            self.found_count += 1

            dataset = mrs_dataset.Dataset(element)
            
            self.imported.append(dataset)

        self.post_import()
        
        return self.imported


class DatasetCliImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        for element in self.root.getiterator("dataset"):
            self.found_count += 1

            dataset = mrs_dataset.Dataset(element)
            
            self.imported.append(dataset)

        self.post_import()
        
        return self.imported, self.timestamp
    

class DataRawImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        for element in self.root.getiterator("data_raw"):
            self.found_count += 1

            data = mrs_data_raw.DataRaw(element)
            
            self.imported.append(data)

        self.post_import()
        
        return self.imported
    

class PriorImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)


    def go(self, add_history_comment=False):
        for element in self.root.getiterator("prior"):
            self.found_count += 1

            prior = mrs_prior.Prior(element)

            self.imported.append(prior)

        self.post_import()
        
        return self.imported


class MetinfoImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        for element in self.root.getiterator("metinfo"):
            self.found_count += 1

            metinfo = mrs_metinfo.MetInfo(element)

            self.imported.append(metinfo)

        self.post_import()

        return self.imported
