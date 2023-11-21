"""
# -----------------------------------------------------------------------------
# MrsiDataRaw object - Discussion on Data Dimensions
# -----------------------------------------------------------------------------

Data are stored in numpy arrays. There are 7 dimensions, one spectral, three
'spatial' and two 'other' (typically for edits or reps). This base class is 
subclassed to indicate to SIView what the other dimensions contain, as shown 
below:

3D/4D spatial data subclasses:
    DataRaw : shape = [nedit, nrep, mcyc,  1, ny, nx, npts]
    DataRaw : shape = [nedit, nrep, mcyc, nz, ny, nx, npts]

nb. 'mcyc' is metabolite cycling for combined water and metab acquisitions

"""

# Python modules
import uuid

# 3rd party modules
import numpy as np
import xml.etree.cElementTree as ElementTree

# Our modules
import siview.common.util.xml_ as util_xml
import siview.common.constants as common_constants
from siview.common.constants import Deflate
from siview.common.base_transform import BaseTransform, transformation_matrix, rotation_matrix, requires_transform





class MrsiDataRaw(BaseTransform):
    """ 
    A container for 'raw' magnetic resonance spectroscopy k-space data.
    - Can be subclassed to create specific raw MRS containers.
    - Contains functionality to save/recall object data to/from XML.
    - Has attributes for provenance and/or for sorting the data (te, tr, etc.).
    
    """
    XML_VERSION = "1.0.0"

    def __init__(self, attributes=None, transform=None):
        """
        Parameters:
            attributes (dict): default None, optional, if passed in will be
                used to set attribute values in object.

            transform (numpy array, 4x4 float): default None, optional, if
                passed in will be used to set transform attribute. If not
                given a default transform will be set.

        Attributes:
            id (string), unique identifying string for this object.

            source_id (list):  unique identifier used to find where this items
                lives. Typically the filename this object is saved under.

            data_sources (list of strings): where the data came from. Typically
                filenames. Should be 0, 1, or N entries (where N == dims[1]).

            sw (float): default 2000.0 [Hz], raw data sweep width, aka 'acquisition
                sweep width'

            frequency (float): default 127.9 [MHz], MR scanner field strength

            resppm (float): default 4.7 [ppm], acquisition on-resonance value

            echopeak (float): default 0.0, range [0.0-1.0], spectral echo peak
                in % of acquisition dim0 length

            nucleus (string): default '1H', nucleus name, e.g. 1H, 31P, 13C etc.

            seqte (float): default 30.0 [ms], sequence echo time (TE)

            seqtr (float): default 1500.0 [ms], sequence repetition time (TR)

            voxel_dimensions (list, floats): default [20.0, 20.0, 20.0], in [mm]

            fov (list, floats): default [240.0, 240.0, 180.0], in [mm]

            headers (list of string(s)): default [], header (metadata) from
                the data_sources file(s)

            data (numpy array): default [1,1,1,2048] complex128, zeros A
                4-dimensional numpy array with raw mr spectroscopy data

        """
        super().__init__(transform=transform)

        self.id                = str(uuid.uuid4())
        self.source_id         = ''
        self.behave_as_preset  = False
        self.block_prep_flavor = ''
        
        self.data_sources      = []
        self.sw                = 1250.0                 # [Hz]
        self.frequency         = 123.8                  # [MHz]
        self.resppm            = 4.7                    # [ppm]
        self.echopeak          = 0.0                    # percentage (0.0-1.0)
        self.nucleus           = '1H'
        self.seqte             = 110.0                  # [ms]
        self.seqtr             = 2000.0                 # [ms]
        self.voxel_dimensions  = [100.0, 100.0, 20.0]   # [mm] for x, y z dims
        self.fov               = [240.0, 240.0, 180.0]  # [mm] for x, y z dims
        self.headers           = []

        self.data = np.zeros([1, 1, 1, 1, 1, 1, 512], dtype=np.complex64)

        if attributes is not None:
            self.inflate(attributes)

        if self.transform is None:
            self.transform = self.default_transform()

    ##### Standard Methods and Properties #####################################

    @property
    def data_source(self):
        """Returns first entry in the list of data sources """
        return (self.data_sources[0] if self.data_sources else "[No information available]")
    
    @property
    def data_type(self):
        """Return numpy dtype value of data array """
        return str(self.data.dtype)

    @property
    def data_shape(self):
        """Return numpy shape value of data array """
        return list(self.data.shape)

    @property
    def dims(self):
        """Return shape of numpy data array. Dims must be a list."""
        return list(self.data.shape[::-1])

    @property
    def hpp(self):
        """Current hertz per point. It's read only."""
        return (self.sw / self.dims[0]) if self.dims[0] else 0.0

    @property
    def dwell(self):
        """Current hertz per point. It's read only."""
        return 1.0/self.sw

    @property
    def is_fid(self): 
        """Bool, True if data is Free Induction Decay, inferred from echopeak """
        return not bool(self.echopeak)

    @property
    @requires_transform
    def center(self):
        # The BaseTransform class is for images, for spectroscopy volumes the
        # volume is encoded in the position of the volume
        return self.position

    def __str__(self):
        lines = [ ]
        # The header to this text contains the class name. Generating it 
        # dynamically here ensures that this reports the correct object type
        # even for subclass instances of this class.
        header = "----------- {0} Object ------------"
        lines.append(header.format(self.__class__.__name__))
        lines.append("Data sources                  : %s" % self.data_sources)
        lines.append("Block prep flavor             : %s" % self.block_prep_flavor)
        lines.append("Spectral sweep width [Hz]     : %f" % self.sw)
        lines.append("Spectrometer frequency [MHz]  : %f" % self.frequency)
        lines.append("Resonance PPM                 : %f" % self.resppm)
        lines.append("Echo peak                     : %f" % self.echopeak)
        lines.append("Nucleus                       : %s" % self.nucleus)
        lines.append("Sequence TE                   : %f" % self.seqte)
        lines.append("Sequence TR                   : %f" % self.seqtr)
        lines.append("Voxel dimensions              : "+str(self.voxel_dimensions))
        lines.append("FOV                           : "+str(self.fov))
        lines.append("Data shape                    : "+str(self.data.shape))
        lines.append("Data type                     : %s" % self.data_type)
        lines.append("Data length                   : %d" % self.data.size)
        lines.append("Transform                     : \n"+str(self.transform))

        return '\n'.join(lines)


    ##### Helper methods ######################################################

    def default_transform(self):
        vox_size     = np.array([100.0, 100.0, 20.0]) # in [mm]
        voi_position = np.array([ 0.0, 0.0, 0.0])   # scanner center in [mm]
        row_vector   = np.array([-1.0, 0.0, 0.0])   # transverse
        col_vector   = np.array([ 0.0, 1.0, 0.0])
        return transformation_matrix(row_vector, col_vector, voi_position, vox_size)


    def deflate(self, flavor=Deflate.ETREE, tag='', version=''):

        if flavor == Deflate.ETREE:
            tag = 'mrsi_data_raw' if tag == '' else tag
            version = self.XML_VERSION if version == '' else version

            e = ElementTree.Element(tag, {"version" : version})

            util_xml.TextSubElement(e, "behave_as_preset", self.behave_as_preset)
            util_xml.TextSubElement(e, "block_prep_flavor", self.block_prep_flavor)

            if not self.behave_as_preset:
            
                for data_source in self.data_sources:
                    util_xml.TextSubElement(e, "data_source", data_source)

                util_xml.TextSubElement(e, "sweep_width", self.sw)
                util_xml.TextSubElement(e, "frequency",   self.frequency)
                util_xml.TextSubElement(e, "resppm",      self.resppm)
                util_xml.TextSubElement(e, "echopeak",    self.echopeak)
                util_xml.TextSubElement(e, "nucleus",     self.nucleus)
                util_xml.TextSubElement(e, "seqte",       self.seqte)
                util_xml.TextSubElement(e, "seqtr",       self.seqtr)
                
                for dim in self.voxel_dimensions:
                    util_xml.TextSubElement(e, "voxel_dimensions", dim)

                for val in self.fov:
                    util_xml.TextSubElement(e, "fov", val)

                e.append(util_xml.numpy_array_to_element(self.transform, "transform"))
                e.append(util_xml.numpy_array_to_element(self.data, "data"))

                for header in self.headers:
                    util_xml.TextSubElement(e, "header", header)

            return e
            
        elif flavor == Deflate.DICTIONARY:
            return self.__dict__.copy()


    def inflate(self, source):

        if hasattr(source, "makeelement"):
            # Quacks like an ElementTree.Element  

            self.id = source.get("id")

            val = source.findtext("behave_as_preset")   # default is False
            if val is not None:
                self.behave_as_preset = util_xml.BOOLEANS[val]

            val = source.findtext("block_prep_flavor")   # suggestion for block_prep class to use to inflate to mrs_dataset
            if val is not None:
                self.block_prep_flavor = val

            if not self.behave_as_preset:
                self.data_sources = [item.text for item in source.findall("data_source") if item.text]

                if source.findtext("sweep_width") is not None:
                    self.sw = float(source.findtext("sweep_width"))
                if source.findtext("frequency") is not None:
                    self.frequency = float(source.findtext("frequency"))
                if source.findtext("resppm") is not None:
                    self.resppm = float(source.findtext("resppm"))
                if source.findtext("echopeak") is not None:
                    self.echopeak = float(source.findtext("echopeak"))
                if source.findtext("seqte") is not None:
                    self.seqte = float(source.findtext("seqte"))
                if source.findtext("seqtr") is not None:
                    self.seqtr = float(source.findtext("seqtr"))

                self.nucleus = source.findtext("nucleus")

                self.voxel_dimensions = [float(val.text) for val in source.getiterator("voxel_dimensions")]
                self.fov              = [float(val.text) for val in source.getiterator("fov")]

                if source.findtext("transform") is not None:
                    self.transform = util_xml.element_to_numpy_array(source.find("transform"))

                if source.findtext("data") is not None:
                    self.data = util_xml.element_to_numpy_array(source.find("data"))

                self.headers = [header.text for header in source.findall("header")]

        elif hasattr(source, "keys"):
            # Quacks like a dict
            for key in list(source.keys()):
                if key == "header":
                    # Item passed as a single string but is stored in a list.
                    self.headers.append(source["header"])
                elif key in ("data_source", "filename"):
                    # These are single items in the dict but a list on the raw
                    # object. NB, all keys map back to "data_sources".
                    self.data_sources.append(source[key])
                elif key in ("data_type", "dims"):
                    # We ignore these since they're implied by the data now.
                    pass
                else:
                    if hasattr(self, key):
                        setattr(self, key, source[key])

        if self.nucleus != "1H":
            self.resppm = common_constants.DEFAULT_XNUCLEI_CENTER_PPM

        self.normalize_dims()       # ensure data shaped correctly. Mostly CYA.


    def get_data_source(self, index):
        """
        Given a 0-based index into the list of data_sources, attempts to 
        return the data source at that index. 

        This function is 'safe' in that if the index goes off the end of the
        list it won't fail but will instead return an alternate data source. 
        The sources that this function attempts to return in order of 
        preference are:
           1. data_sources[index]
           2. data_sources[0]
           3. A placeholder string ("[No information available]")

        This function sacrifices guaranteed accuracy for guaranteed convenience.
        Callers who absolutely need to know which data source is at a given
        index will need to examine the list themselves.
        
        """
        # index is usually a voxel, we want the x-val from the tuple because we will
        # assume that we are only dealing with SVS data here for now
        index = index[0]
        nsources = len(self.data_sources)
        if nsources == 0:
            source = "[No information available]"
        else:
            if index > nsources-1:
                # Ooops, off the end of the list, return the first one
                index = 0
            source = self.data_sources[index]

        return source


    def normalize_dims(self):
        """ Like normalize_data_dims() above, adds 1's to data.shape til 6D """
        while len(self.data.shape) < 6:
            tmp = list(self.data.shape)
            tmp.insert(0,1)
            self.data.shape = tmp
        


