#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.

# Python modules
from __future__ import division
import argparse
import os
import sys
import platform

# 3rd party modules
try:
    import pydicom
except ImportError:
    import dicom as pydicom
import siview.common.dcmstack.dcmstack as dcmstack

# Our modules
import siview.common.export as export


DESC =  \
"""Command line interface to process lung wash-in/out 19F data. 
 Data directories, Mask file names and Output file name values 
 are all required for this command to function properly. 
 Note. You may have to enclose data/mask/output strings in double 
 quotation marks for them to process properly if they have  
 spaces or other special characters embedded in them.
"""

def siview_cli(datadirs=None, maskfiles=None, verbose=False):
    
    # Test if input arguments exist
    msg = ''
    for item in datadirs:
        if not os.path.exists(item):
            msg = """DATADIR path does not exist "%s".""" % item 
            print(msg, file=sys.stderr)
            sys.exit(-1)

    for item in maskfiles:
        if not os.path.isfile(item):
            msg = """MASKFILE does not exist "%s".""" % item 
            print(msg, file=sys.stderr)
            sys.exit(-1)
    
    # Load DICOM data into a DicomStack object
    if verbose: print( "Load DICOM data into a DicomStack object"    )
    try:
        all_filenames = []
        for path in datadirs:
            # - Enumerate the directory contents
            # - Turn the filenames into fully-qualified filenames
            # - Filter out non-files

            filenames = os.listdir(path)
            filenames = [os.path.join(path, filename) for filename in filenames]
            filenames = [filename for filename in filenames if os.path.isfile(filename)]
            all_filenames += filenames

        src_dcm  = pydicom.read_file(all_filenames[0])
        patid    = src_dcm.PatientID
        serdesc  = src_dcm.SeriesDescription
        studyuid = src_dcm.StudyInstanceUID
        
        my_stack = dcmstack.DicomStack(time_order='AcquisitionTime')
        for item in all_filenames:
            src_dcm = pydicom.read_file(item)
            my_stack.add_dcm(src_dcm)

    except:
        msg = """Unknown exception reading DICOM file "%s".""" % filename 
        print(msg, file=sys.stderr)
        sys.exit(-1)
    
    # Test DicomStack dimensions
    msg  = ""
    dims = my_stack.get_data().shape
    if len(dims) != 4:
        msg = """DicomStack data is not 4D, dim = "%s".""" % str(dims)
    elif dims[0] < 6:
        msg = """Time series dimension too small to fit, dim = "%s".""" % str(dims)
    
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(-1)

    path, _ = os.path.split(all_filenames[0])
    path_up, _ = os.path.split(path)
    
    # Convert DicomStack to timeseries
    timeseries = mri_timeseries.Timeseries()
    timeseries.import_from_dcmstack(my_stack, all_filenames, False, patid, serdesc, studyuid, path_up)
    if verbose: print( "    - DicomStack loaded")
        
    # Load masks in if available
    if verbose: print( "Load masks if available" )
    
    if maskfiles is not None:
    
        masks = []
        opts  = []
        try:
            for filename in maskfiles:
                data, options = nrrd.read(filename)
                masks.append(data)
                opts.append(options)
                
        except IOError:
            msg = """I can't read the Mask file "%s".""" % filename
        except:
            msg = """Unknown exception reading Mask NRRD file "%s".""" % filename 

        if msg:
            print(msg, file=sys.stderr)
            sys.exit(-1)
        
        # test if all masks have same dimensions
        for mask in masks:
            if mask.shape != masks[0].shape:
                msg = "Masks are not all the same shape."
                print(msg, file=sys.stderr)
                sys.exit(-1)
        
        # concatenate to one mask and save in results dictionary
        mask = masks[0]
        if len(masks) > 1:
            for item in masks[1:]:
                mask += item
                
        mask = mask.swapaxes(0,1)    
        dims = timeseries.result_maps['Mask'].shape
    
        if mask.shape != dims:
            msg = 'New mask is different shape than Image1 spatial dims.'
            print(msg, file=sys.stderr)
            sys.exit(-1)
    
        timeseries.result_maps['Mask'] = mask
        if verbose: print( "    - masks loaded")
    
    else:
        if verbose: print( "    - no masks to load")
        
    # Process time series data fitting
    if verbose: print( "Process time series data fitting")
    voxel = timeseries.get_all_voxels()  # list of tuples, with mask != 0
    p = timeseries.chain.run(voxel, entry='all')
    if verbose: print( "    - processing done")
            
    patid = timeseries.patient_id
    sdesc = timeseries.series_description
    path  = timeseries.output_path
    default_fbase = os.path.join(path_up, patid+'_'+sdesc)
        
    filename_left  = default_fbase+'_Left_Masked_XYZV.csv'
    filename_right = default_fbase+'_Right_Masked_XYZV.csv'
    filename_xml   = default_fbase+'.xml'
    
    # Output values from the fitting results array into a CSV based text
    # file. 
    #  
    # This method organizes the output serially by voxel value. We loop
    # through x,y,z value (x changing fastest) and write a result to the 
    # text array if the mask value is non-zero. All fitting values are
    # written to the same voxel line as are the mask and image value.
    
    #-------------------------------------------------------------------------- 
    # Write results to XML output file
    if verbose: print( "Writing results to XML output file")
    export.export(filename_xml, [timeseries], None, None, False)
    if verbose: print( "    - results (xml) write successful to, "+filename_xml)

    #-------------------------------------------------------------------------- 
    # Write results out to text files by slice    
    lines_left, lines_right = timeseries.get_output_text_by_slice()
    
    lines_left = "\n".join(lines_left)
    lines_left = lines_left.encode("utf-8")
    if (platform.system() == "Windows"):
        lines_left = lines_left.replace(b"\n", b"\r\n")
    open(filename_left, "wb").write(lines_left)
    if verbose: print( "    - results (left) write successful to, "+filename_left)
    
    lines_right = "\n".join(lines_right)
    lines_right = lines_right.encode("utf-8")
    if (platform.system() == "Windows"):
        lines_right = lines_right.replace(b"\n", b"\r\n")
    open(filename_right, "wb").write(lines_right)
    if verbose: print( "    - results (right) write successful to, "+filename_right)

    #-------------------------------------------------------------------------- 
    # Write results to DICOM format
    try:
        timeseries.do_results_output_dicom()
        if verbose: print( "    - write results to DICOM format successful.")
    except:
        #msg = "Error DICOM Output, exiting." 
        e = sys.exc_info()[0]
        print(e, file=sys.stderr)
        sys.exit(-1)
        
    
    
    
    
def create_parser():

    parser = argparse.ArgumentParser(prog='siview_cli', 
                                     usage='%(prog)s [options]',
                                     description=DESC)
    
    parser.add_argument('-d', '--datadirs', nargs='+', dest='datadirs',
                                required=True, metavar='Dir',
                                help='list of directories containing only DICOM files')
    parser.add_argument('-m', '--maskfiles', nargs='+', dest='maskfiles',
                                required=True, metavar='File',
                                help='list of NRRD files containing mask values')
    parser.add_argument('-v', '--verbose',  dest='verbose', 
                                action="store_true", 
                                help='increase output verbosity')
    return parser    


def main():

    parser = create_parser()
    args = parser.parse_args()
    siview_cli(args.datadirs, args.maskfiles, args.verbose)

#     # generalize the call to the local testdata directory, wherever it is
#     fpath = os.path.dirname(os.path.realpath(__file__))
#
#     DPATH = fpath+r'/testdata/Mk0003V3/B17_Upgrade_Evolve_Camrd397Merck'
#     MPATH = fpath+r'/testdata/Mk0003V3'
#      
#     DATADIRS = [r'gre3_vibe_130_HZPERPIX_2_NEX_04',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_05',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_06',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_07',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_08',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_09',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_10',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_11',
#                 r'gre3_vibe_130_HZPERPIX_2_NEX_12',
#                 ]
#      
#     MASKFILES = [r'MK0003V2toV3LeftLung.nrrd',
#                  r'MK0003V2toV3RightLung.nrrd',
#                  ] 
#      
#     datadirs = []
#     for item in DATADIRS:
#         datadirs.append(DPATH+'/'+item)
#  
#     maskfiles = []
#     for item in MASKFILES:
#         maskfiles.append(MPATH+'/'+item)
#  
#     siview_cli(datadirs, maskfiles, verbose=True)
        

        
if __name__ == '__main__':
    main()        
        