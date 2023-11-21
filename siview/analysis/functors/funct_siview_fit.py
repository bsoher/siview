#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules



# 3rd party modules
import numpy as np
from scipy.optimize import minimize


# Our modules
import siview.analysis.functors.functor as functor
import siview.analysis.constrained_levenberg_marquardt as clm


class FunctSiviewFit(functor.Functor):
    """ 
    This is a building block object that can be used to create a  
    processing chain for time domain to frequency domain spectral MRS 
    data processing.
    
    """
    
    def __init__(self):
        functor.Functor.__init__(self)



    ##### Standard Methods and Properties #####################################

    def algorithm(self, chain):
        """
        constrained_levenberg_marquardt - Exit modes (badfit) are just 0/1
         - maybe I should spread this out a bit based on what returns ...
        
        SLSQP - Exit modes (badfit) are defined as follows
        
        -1 : Gradient evaluation required (g & a)
         0 : Optimization terminated successfully.
         1 : Function evaluation required (f & c)
         2 : More equality constraints than independent variables
         3 : More than 3*n iterations in LSQ subproblem
         4 : Inequality constraints incompatible
         5 : Singular matrix E in LSQ subproblem
         6 : Singular matrix C in LSQ subproblem
         7 : Rank-deficient equality constraint subproblem HFTI
         8 : Positive directional derivative for linesearch
         9 : Iteration limit exceeded        
        
        """
        time = chain.time.copy()

        a, limits = chain.init_function(time)

        w = chain.weight_array
        
        a1, limits1 = chain.init_function(time, pair_limits=True)
        
        res = minimize(chain.lsq_function, a1, args=(time, w), method='SLSQP', bounds=limits1)

        chain.fit    = (chain.fit_function(res.x))[0]
        chain.a      = res.x
        chain.sig    = 0.0
        chain.chis   = res.fun
        chain.badfit = res.status
        
#         yfit, a, sig, chis, wchis, badfit = clm.constrained_levenberg_marquardt(time, w, a, limits, chain.fit_function)
#   
#         if badfit:
#             bob = 10
#             bob += 1
             
        #print( "ccfit vs slsqp diff = "+str(a-chain.a))
  
#         chain.fit    = yfit
#         chain.a      = a
#         chain.sig    = sig
#         chain.chis   = chis
#         chain.badfit = badfit







