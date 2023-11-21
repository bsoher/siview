#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# Our modules 
import siview.common.constants as constants

"""
When we need to create an app's INI file, this is the content it
uses. 

This module contains just three objects:
1) the name of the application
2) the name of the configuration file to use
3) a dict called DEFAULT_INI_FILE_CONTENT. The dict has a key 
   for the INI file ("siview", etc.) and associated with 
   that key is the default content for that INI file. 
"""

APP_NAME = "SIView"
INI_NAME = "siview.ini"

# The dict contents are mostly strings 

DEFAULT_INI_FILE_CONTENT = {

###############################      SIView

    "siview" : """
# The SIView config file.

[general]
last_export_path=
# If cpu_limit is set to a positive integer, SIView will use no more than that
# many CPUs simultaneously. When cpu_limit is set to 0 or left blank, SIView
# will use as many CPUs as it thinks are available.
cpu_limit=

""",


###############################      Analysis

    "analysis" : """
# The SIView-Analysis config file.

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
maximized = False

[basic_prefs]
bgcolor = "#ffffff"
line_color_imaginary = red
line_color_individual = green
line_color_magnitude = purple
line_color_real = black
line_color_summed = black
line_width = 1.0
sash_position = 550
xaxis_hertz = False
xaxis_ppm = True
xaxis_show = True
zero_line_bottom = True
zero_line_color = darkgoldenrod
zero_line_middle = False
zero_line_show = False
zero_line_style = solid
zero_line_top = False
csv_qa_metab_labels = False

[grid]
bgcolor = "#ffffff"
cmap_autumn = True
cmap_blues = False
cmap_jet = False
cmap_rdbu = False
cmap_gray = False
cmap_rdylbu = False
line_color_imaginary = red
line_color_individual = green
line_color_magnitude = purple
line_color_real = black
line_color_summed = black
line_width = 1.0
sash_position = 550
xaxis_hertz = False
xaxis_ppm = True
xaxis_show = True
zero_line_bottom = True
zero_line_color = darkgoldenrod
zero_line_middle = False
zero_line_show = False
zero_line_style = solid
zero_line_top = False
csv_qa_metab_labels = False

[spatial]
bgcolor = "#ffffff"
cmap_autumn = True
cmap_blues = False
cmap_jet = False
cmap_rdbu = False
cmap_gray = False
cmap_rdylbu = False
line_color_imaginary = red
line_color_individual = green
line_color_magnitude = purple
line_color_real = black
line_color_summed = black
line_width = 1.0
sash_position = 550
xaxis_hertz = False
xaxis_ppm = True
xaxis_show = True
zero_line_bottom = True
zero_line_color = darkgoldenrod
zero_line_middle = False
zero_line_show = False
zero_line_style = solid
zero_line_top = False
csv_qa_metab_labels = False

[prep_generic]
area_calc_plot_a = False
area_calc_plot_b = True
bgcolor = "#ffffff"
data_type_imaginary = False
data_type_magnitude = False
data_type_real = True
line_color_imaginary = red
line_color_magnitude = purple
line_color_real = black
line_width = 1.0
sash_position = 522
xaxis_hertz = False
xaxis_ppm = True
xaxis_show = False
zero_line_bottom = True
zero_line_color = darkgoldenrod
zero_line_middle = False
zero_line_show = False
zero_line_style = solid
zero_line_top = False
zero_line_plot_bottom = False
zero_line_plot_color = yellow
zero_line_plot_middle = False
zero_line_plot_show = True
zero_line_plot_style = solid
zero_line_plot_top = True

[spectral_prefs]
area_calc_plot_a = True
area_calc_plot_b = False
area_calc_plot_c = False
bgcolor = "#ffffff"
cmap_autumn = True
cmap_blues = False
cmap_jet = False
cmap_rdbu = False
cmap_gray = False
cmap_rdylbu = False
data_type_imaginary = False
data_type_magnitude = False
data_type_real = True
line_color_baseline = blue
line_color_imaginary = red
line_color_magnitude = purple
line_color_real = black
line_color_svd = green
line_width = 1.0
plot_c_function_a_minus_b = True
plot_c_function_a_plus_b = False
plot_c_function_b_minus_a = False
plot_c_function_none = False
plot_view_all = True
plot_view_final = False
sash_position_main = 400
sash_position_svd = 487
xaxis_hertz = False
xaxis_ppm = True
xaxis_show = False
zero_line_bottom = True
zero_line_color = darkgoldenrod
zero_line_middle = False
zero_line_show = False
zero_line_style = solid
zero_line_top = False

[voigt_prefs]
area_calc_plot_a = True
area_calc_plot_b = False
area_calc_plot_c = False
area_calc_plot_d = False
bgcolor = "#ffffff"
cmap_autumn = True
cmap_blues = False
cmap_jet = False
cmap_rdbu = False
cmap_gray = False
cmap_rdylbu = False
csv_qa_metab_labels = False
line_color_base = purple
line_color_fit = green
line_color_imaginary = red
line_color_init = green
line_color_magnitude = purple
line_color_real = black
line_color_raw = black
line_color_weight = darkgoldenrod
line_width = 1.0
n_plots_1 = False
n_plots_2 = False
n_plots_3 = False
n_plots_4 = True
sash_position = 550
xaxis_hertz = False
xaxis_ppm = True
xaxis_show = False
zero_line_bottom = True
zero_line_color = darkgoldenrod
zero_line_middle = False
zero_line_show = False
zero_line_style = solid
zero_line_top = False

[voigt_plot_a]
baseline = False
bgcolor = black
combo_fit_and_base = False
combo_fit_plus_base = False
combo_raw_and_base = False
combo_raw_and_fit = False
combo_raw_and_fit_plus_base = False
combo_raw_and_init_model = True
combo_raw_and_wt_arr = False
combo_raw_minus_base = False
combo_raw_minus_base_and_fit = False
combo_raw_minus_fit = False
combo_raw_minus_fit_minus_base = False
data_type_imaginary = False
data_type_magnitude = False
data_type_real = True
fitted_data = False
raw_data = False

[voigt_plot_b]
baseline = False
bgcolor = black
combo_fit_and_base = False
combo_fit_plus_base = False
combo_raw_and_base = True
combo_raw_and_fit = False
combo_raw_and_fit_plus_base = False
combo_raw_and_init_model = False
combo_raw_and_wt_arr = False
combo_raw_minus_base = False
combo_raw_minus_base_and_fit = False
combo_raw_minus_fit = False
combo_raw_minus_fit_minus_base = False
data_type_imaginary = False
data_type_magnitude = False
data_type_real = True
fitted_data = False
raw_data = False

[voigt_plot_c]
baseline = False
bgcolor = black
combo_fit_and_base = False
combo_fit_plus_base = False
combo_raw_and_base = False
combo_raw_and_fit = False
combo_raw_and_fit_plus_base = True
combo_raw_and_init_model = False
combo_raw_and_wt_arr = False
combo_raw_minus_base = False
combo_raw_minus_base_and_fit = False
combo_raw_minus_fit = False
combo_raw_minus_fit_minus_base = False
data_type_imaginary = False
data_type_magnitude = False
data_type_real = True
fitted_data = False
raw_data = False

[voigt_plot_d]
baseline = False
bgcolor = black
combo_fit_and_base = False
combo_fit_plus_base = False
combo_raw_and_base = False
combo_raw_and_fit = False
combo_raw_and_fit_plus_base = False
combo_raw_and_init_model = False
combo_raw_and_wt_arr = False
combo_raw_minus_base = False
combo_raw_minus_base_and_fit = False
combo_raw_minus_fit = False
combo_raw_minus_fit_minus_base = True
data_type_imaginary = False
data_type_magnitude = False
data_type_real = True
fitted_data = False
raw_data = False

[watref_prefs]
csv_qa_metab_labels = False
sash_position_main = 400

""",



}

