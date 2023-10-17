#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import math

# Our modules


DEGREES_TO_RADIANS = math.pi / 180
RADIANS_TO_DEGREES = 180 / math.pi
MINUTES_TO_SECONDS = 60

######################     Object Start Values     ########################

PEAK_MIN     =  10
PEAK_START   =  20
PEAK_MAX     = 500

RATE1_MIN    =   5
RATE1_START  =  25
RATE1_MAX    = 320

RATE2_MIN    =   5
RATE2_START  =  25
RATE2_MAX    = 330

DELAY1_MIN   = -45  
DELAY1_START = -40 
DELAY1_MAX   =   5

DELAY2_MIN   = 150
DELAY2_START = 200 
DELAY2_MAX   = 346

BASE_MIN     =   1
BASE_START   =  10
BASE_MAX     =  20


######################     GUI Range Constants     ########################

GUI_PEAK_MIN     = (1,500)
GUI_PEAK_MAX     = (1,500)
GUI_PEAK_START   = (1,500)

GUI_RATE1_MIN    = (0,600)
GUI_RATE1_MAX    = (0,600)
GUI_RATE1_START  = (0,600)
 
GUI_RATE2_MIN    = (0,600)
GUI_RATE2_MAX    = (0,600)
GUI_RATE2_START  = (0,600)

GUI_DELAY1_MIN   = (-100,1000)
GUI_DELAY1_MAX   = (-100,1000)
GUI_DELAY1_START = (-100,1000)

GUI_DELAY2_MIN   = (0,1000)
GUI_DELAY2_MAX   = (0,1000)
GUI_DELAY2_START = (0,1000)

GUI_BASE_MIN     = (0,100)
GUI_BASE_MAX     = (0,100)
GUI_BASE_START   = (0,100)
