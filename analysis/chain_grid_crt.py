# Python modules

# 3rd party modules

# Our modules
from siview.chain_base import Chain


class ChainGridCrt(Chain):
    """
    Building block object used to create a processing chain for MRSI data.

    Processes: kspace weighting, kspace grid locations, NUFFT call including
    (maybe) some multiprocessing speedups, and usually an iFFT for the spectral
    dimension to move it back into the time domain.

    Base class sets convenience references to:  self._block and self._dataset
    
    self.data is always initialized as []

    """
    def __init__(self, dataset, block):
        """ Prepare the base class. """
        super().__init__(dataset, block)

        self.raw_dims             = self._dataset.raw_dims
        self.raw_dim0             = self._dataset.raw_dims[0]
        self.raw_hpp              = self._dataset.raw_hpp
        
        # processing functor - provides entry points for chain
        self.functor_all = funct_spectral_all.do_processing_all

        self.reset_results_arrays()


    def reset_results_arrays(self):
        """
        A separate method so it can be called outside __init__. Should
        create/set enough results to keep View happy if run() fails.

        """
        pass
            
        
    def run(self, voxels, entry='all'):
        """
        Run in this block is called manually by the user after all settings
        have been applied. 

        This object maintains previous run() results values until next run().
        This allows the View to update without having to re-run the pipeline.

        The 'entry' keyword adds flexibility to Block-Chain-View relationship.

        """

        # Get 'global' parameters, that DO NOT change with voxel, from Dataset
        #  - these processing/data parameters have to be updated at run time 

        self.raw_dims = self._dataset.spectral_dims
        self.nrings   = self._dataset.nrings
        # etc ...
        
        self.data = self._dataset.get_source_data('raw')

        # select the chain processing functor based on the entry point
        if entry == 'all':
            self.functor_all(self)
        else:
            print('oooops!')

        # save data and parameter results into the Block results arrays
        self._block.data = self.freq

        # Return values specific to calling Tab that contains this Block.Chain
        # Used to update its self.view (plot_panel_spectrum object).

        plot_results = { 'freq'                   : self.freq.copy()   }
                        
        return plot_results