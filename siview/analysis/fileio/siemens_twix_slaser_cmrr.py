"""
Routine for reading a Siemens Twix meas.dat format file created by CMRR sLASER.
Data is returned in a DataRawCmrrSlaser object

"""


# Python modules

# 3rd party modules
import numpy as np

# Our modules
from siview.common.mrs_data_raw import DataRawCmrrSlaser
from siview.analysis.fileio.siemens_twix import RawReaderSiemensTwix



# RAWDATA_SCALE is based on ICE_RAWDATA_SCALE in SpecRoFtFunctor.cpp
RAWDATA_SCALE = 131072.0 * 256.0



class RawReaderSiemensTwixSlaserCmrrVe(RawReaderSiemensTwix):

    def read_raw(self, filename, ignore_data=False, open_dataset=None):
        """
        Given the name of a twix file, returns a DataRawCmrrSlaser object.
        - ignore_data option is not implemented for this reader.
        - open_dataset attribute is not used in this reader.
        
        """
        twix, version_flag = self.get_twix(filename)

        d = self._get_parameters(twix.current)
        d["data_source"] = filename

        data = d['data']
        prep = d['prep']
        nref = d["ref_nscans"]
        navg = d["lAverages"]

        # Note. Scaling is done below to match Versin 0.10.0

        if d["remove_os"]:
            data = self._remove_oversampling_basic(data)
            if prep is not None:
                prep = self._remove_oversampling_basic(prep)
            d["sw"] = d["sw"] / 2.0

        data = np.conjugate(data)
        if prep is not None:
            prep = np.conjugate(prep)

        raws = []

        # dataset1 - scan 0, water unsuppressed for coil combine
        
        d["data"] = prep * RAWDATA_SCALE / 1.0               # this matches version 0.10.0

        d["data_source"] = filename+'.combine'
        raws.append(DataRawCmrrSlaser(d))

        # dataset2 - scan 1-2, water unsuppressed for ECC
        
        d["data"] = data[:,:,0:nref,:].copy() * RAWDATA_SCALE / float(nref) # this matches version 0.10.0
        d["data_source"] = filename+'.ecc1'
        raws.append(DataRawCmrrSlaser(d))

        # dataset3 - scans 3-4, water unsuppressed for water scale
        
        d["data"] = data[:,:,nref:nref*2,:].copy() * RAWDATA_SCALE / float(nref)    # this matches version 0.10.0
        d["data_source"] = filename+'.water1'
        raws.append(DataRawCmrrSlaser(d))

        # dataset5 - scans 69-70 (2 total), water unsuppressed for ecc

        d["data"] = data[:,:,nref*2+navg:nref*2+navg+nref,:].copy() * RAWDATA_SCALE / float(nref)
        d["data_source"] = filename+'.ecc2'
        raws.append(DataRawCmrrSlaser(d))

        # dataset6 - scans 71-72 (2 total), water unsuppressed for water scale

        d["data"] = data[:,:,nref*2+navg+nref:nref*2+navg+nref*2,:].copy() * RAWDATA_SCALE / float(nref)
        d["data_source"] = filename+'.water2'
        raws.append(DataRawCmrrSlaser(d))

        # dataset4 - scans 5-68 (64 total), metabolite data with WS

        d["data"] = data[:,:,nref*2:nref*2+navg,:].copy() * RAWDATA_SCALE / float(navg)
        d["data_source"] = filename+'.metab64'
        raws.append(DataRawCmrrSlaser(d))

        return raws



class RawReaderSiemensTwixSlaserCmrrVb(RawReaderSiemensTwixSlaserCmrrVe):

    def read_raw(self, filename, ignore_data=False, open_dataset=None):
        """
        Given the name of a twix file, returns a DataRawCmrrSlaser object.
        - ignore_data option is not implemented for this reader.
        - open_dataset attribute is not used in this reader.

        """
        return super().read_raw(filename, ignore_data=False, open_dataset=None)



class RawReaderSiemensTwixSlaserCmrrVbGulinLong(RawReaderSiemensTwixSlaserCmrrVe):

    def read_raw(self, filename, ignore_data=False, open_dataset=None):
        """
        Given filename, returns a DataRawCmrrSlaser object.
        - The ignore_data option is not implemented for this reader.
        - The open_dataset attribute is not used in this reader.

        """
        twix, version_flag = self.get_twix(filename)

        d = self._get_parameters(twix.current)
        d["data_source"] = filename

        data = d['data']
        prep = d['prep']

        _, _, navg, npts = data.shape

        if d["remove_os"]:
            data = self._remove_oversampling_basic(data)
            if prep is not None:
                prep = self._remove_oversampling_basic(prep)
            d["sw"] = d["sw"] / 2.0

        data = np.conjugate(data)
        if prep is not None:
            prep = np.conjugate(prep)

        raws = []

        # dataset1 - scan 0, water unsuppressed for coil combine and (maybe) ECC

        d["data"] = prep[:,:,0:1,:].copy() * RAWDATA_SCALE / float(1.0)
        d["data_source"] = filename + '.combine'
        raws.append(DataRawCmrrSlaser(d))

        # dataset2 - scan 1-2, water unsuppressed for water scale

        d["data"] = prep[:,:,1:2,:].copy() * RAWDATA_SCALE / float(1.0)
        d["data_source"] = filename + '.water1'
        raws.append(DataRawCmrrSlaser(d))

        # dataset3 - scans 5-68 (64 total), metabolite data with WS

        d["data"] = data.copy() * RAWDATA_SCALE / float(navg)
        d["data_source"] = filename + '.metab64'
        raws.append(DataRawCmrrSlaser(d))

        return raws


class RawReaderSiemensTwixSlaserCmrrVbGulinLongWater(RawReaderSiemensTwixSlaserCmrrVe):

    def read_raw(self, filename, ignore_data=False, open_dataset=None):
        """
        Given filename, returns a DataRawCmrrSlaser object.
        - The ignore_data option is not implemented for this reader.
        - The open_dataset attribute is not used in this reader.

        """
        twix, version_flag = self.get_twix(filename)

        # 'scan' returns data in [ncha, navg, npts] order - easy to convert to mrs_data_raw dims
        d = self._get_parameters(twix.current, index='scan')
        d["data_source"] = filename

        data = d['data']
        prep = d['prep']
        nrep, _, navg, npts = data.shape

        if d["remove_os"]:
            data = self._remove_oversampling_basic(data)
            if prep is not None:
                prep = self._remove_oversampling_basic(prep)
            d["sw"] = d["sw"] / 2.0

        data = np.conjugate(data)
        if prep is not None:
            prep = np.conjugate(prep)

        raws = []

        # dataset1 - scan 0, water unsuppressed for coil combine and (maybe) ECC

        # tmp = prep[:,:,0,:].copy()
        # tmp.shape = (tmp.shape[0], tmp.shape[1], 1, tmp.shape[2])
        d["data"] = prep[:,:,0:1,:].copy() * RAWDATA_SCALE / float(1.0)
        d["data_source"] = filename + '.combine'
        raws.append(DataRawCmrrSlaser(d))

        # dataset2 - scan 1-2, water unsuppressed for water scale

        if prep.shape[2] > 1:
            d["data"] = prep[:,:,1:2,:].copy() * RAWDATA_SCALE / float(1.0)
        else:
            d["data"] = prep[:,:,0:1,:].copy() * RAWDATA_SCALE / float(1.0)
        d["data_source"] = filename + '.water1'
        raws.append(DataRawCmrrSlaser(d))

        # dataset3 - scans 5-68 (64 total), metabolite data with WS

        d["data"] = data.copy() * RAWDATA_SCALE / float(navg)
        d["data_source"] = filename + '.metab64'
        raws.append(DataRawCmrrSlaser(d))

        return raws

