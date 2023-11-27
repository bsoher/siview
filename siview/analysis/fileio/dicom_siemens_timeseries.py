# Python modules

# 3rd party modules

# Our modules
from siview.analysis.fileio.dicom_siemens import RawReaderDicomSiemens
from siview.common.mrs_data_raw_timeseries import DataRawTimeseries
from siview.common.constants import Deflate



class RawReaderDicomSiemensTimeseries(RawReaderDicomSiemens):

    def __init__(self):
        """ Read multiple Siemens DICOM files into DataRawTimeseries object """
        RawReaderDicomSiemens.__init__(self)


    def read_raw(self, filename, ignore_data=False, *args, **kwargs):

        raw = super().read_raw(filename, ignore_data, kwargs['open_dataset'])[0]
        raw = DataRawTimeseries(raw.deflate(Deflate.DICTIONARY))

        return [raw,]



