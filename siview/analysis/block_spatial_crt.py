# Python modules

# 3rd party modules
from xml.etree.cElementTree import Element

# Our modules
import siview.siview.block_spatial_identity as block_spatial_identity
import siview.siview.block as block
from siview.siview.chain_spatial_crt import ChainSpatialCrt
from siview.common.constants import Deflate



class _Settings(object):
    """
    Settings object contains the parameter inputs used for processing in the 
    Chain object in this Block. Having a separate object helps to delineate 
    inputs/outputs and to simplify load/save of preset values.

    This object can also save/recall these values to/from an XML node.

    Version 1.0.0 - similar settings to initial CRT script

    """
    XML_VERSION = "1.0.0"

    def __init__(self, attributes=None):
        """
        Most of these values appear in a GUI when the app first starts.

        """
        #------------------------------------------------------------
        # Spatial Processing Variables
        #------------------------------------------------------------

        # General Parameters
        pass


    def deflate(self, flavor=Deflate.ETREE):
        if flavor == Deflate.ETREE:
            e = Element("settings", {"version" : self.XML_VERSION})
            return e
            
        elif flavor == Deflate.DICTIONARY:
            return self.__dict__.copy()


    def inflate(self, source):
        if hasattr(source, "makeelement"):
            # Quacks like an ElementTree.Element
            pass

        elif hasattr(source, "keys"):
            # Quacks like a dict
            for key in list(source.keys()):
                if hasattr(self, key):
                    setattr(self, key, source[key])



class BlockSpatialCrt(block_grid_identity.BlockSpatialIdentity):
    """
    This Block is based on initial CRT processing script and performs the
    following actions:
    
    Coil Combination
    Eddy Current Correction
    Frequency Correction
    
    All of these are performed separately on each 'rep' whether an averaging
    rep or metabolite cycling rep. So data is still in the full 7 dimension
    state here (echo, rep, mcycle, nz, ny, nx, nt).
    
    This block allows us to pick the various algorithms, and turn each one on
    or off to better view results in the plot window.

    """
    XML_VERSION = "1.0.0"

    def __init__(self, attributes=None):

        super().__init__(attributes)
        self.set = _Settings(attributes)
        self.data = None

        if attributes is not None:
            self.inflate(attributes)

    ##### Standard Methods and Properties #####################################

    def __str__(self):
        lines = []
        lines.append("------- {0} Object -------".format(self.__class__.__name__))
        lines.append("Nothing here")
        return '\n'.join(lines)


    def create_chain(self, dataset):
        self.chain = ChainSpatialCrt(dataset, self)


    def get_associated_datasets(self, is_main_dataset=True):
        """
        Returns a list of datasets associated with this object

        'is_main_dataset' signals that this is the top level dataset gathering 
        associated datasets, and is used to stop circular references

        """
        datasets = super().get_associated_datasets(self, is_main_dataset)

        return datasets


    def set_associated_datasets(self, datasets):
        """
        When we open a VIFF format file, main._import_file() calls this method
        to parse/store any datasets associated with this one as described below.
        
        """
        for dataset in datasets:
            pass
                
                

    def deflate(self, flavor=Deflate.ETREE):
        if flavor == Deflate.ETREE:
            e = Element("block_spatial_crt", { "id":self.id,
                                            "version":self.XML_VERSION})
            e.append(self.set.deflate())
            return e

        elif flavor == Deflate.DICTIONARY:
            raise NotImplementedError


    def inflate(self, source):
        if hasattr(source, "makeelement"):
            # Quacks like an ElementTree.Element
            self.set = _Settings(source.find("settings"))

        elif hasattr(source, "keys"):
            # Quacks like a dict
            for key in list(source.keys()):
                if key == "set":
                    setattr(self, key, source[key])


######################    Private methods

    def _reset_dimensional_data(self, dataset):
        """Resets (to zero) and resizes dimensionally-dependent data"""

        dims = dataset.spectral_dims
        pass




#--------------------------------------------------------------------
# test code

def _test():

    import siview.common.util.time_ as util_time

    test = BlockSpatialCrt()
    test.data = np.zeros([1,1,1,1,1,1,512], dtype=np.complex64)

    class_name = test.__class__.__name__
    filename = "_test_output_"+class_name+".xml"
    element = test.deflate()
    root = ElementTree.Element("_test_"+class_name, { "version" : "1.0.0" })
    util_xml.TextSubElement(root, "timestamp", util_time.now().isoformat())
    root.append(element)
    tree = ElementTree.ElementTree(root)
    tree.write(filename, "utf-8")

    tom = 10


if __name__ == '__main__':
    _test()