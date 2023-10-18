#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules


# Our modules
import siview.si_dataset as si_dataset

from siview.common.import_ import Importer



class SiDatasetImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        for element in self.root.getiterator("si_dataset"):
            self.found_count += 1

            dataset = si_dataset.Dataset(element)
            
            self.imported.append(si_dataset)

        self.post_import()
        
        return self.imported
    
    
