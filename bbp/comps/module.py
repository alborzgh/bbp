#!/usr/bin/env python
"""
Southern California Earthquake Center Broadband Platform
Copyright 2010-2016 Southern California Earthquake Center

Generic container for Broadband's modules
$Id: module.py 1778 2017-01-09 21:47:59Z fsilva $
"""
from __future__ import division, print_function

# Import Python modules
import os
import shutil

# Import Broadband modules
from genslip import Genslip
from ucrmg import UCrmg
from jbsim import Jbsim
from lf_seismograms import LFSeismograms
from hfsims import Hfsims
from syn1D import Syn1D
from uc_stitch import UCStitch
from bbtoolbox import BBToolbox
from uc_site import UCSite
from wcc_siteamp import WccSiteamp
from rotd50 import RotD50
from fas import FAS
from obs_seismograms import ObsSeismograms
from copy_seismograms import CopySeismograms
from gen_plots import GenPlots
from gp_gof import GPGof
from sdsu_mogof import SDSUMOGoF
from gmpe_plot import GMPEPlot
from gmpe_comparison import GMPEComparison
from calculate_gmpe import CalculateGMPE
from match import Match
from plot_seis import PlotSeis
from plot_map import Plot_Map
from genhtml import GenHTML
from exsim import ExSim
from csm import CSM
from rmg import RMG
from as16 import AS16
from rzz2015 import RZZ2015
from rzz2015_gmpe import RZZ2015GMPE
from rotd100 import RotD100
from anderson_gof import AndersonGOF
from irikura import Irikura
from uwsr import uwsr

class Module(object):
    def __init__(self):
        self.module_name = ""
        self.module_args = []
        self.kw_args = dict()
        self.files_to_stage = []

    def setName(self, name):
        self.module_name = name

    def getName(self):
        return self.module_name

    def addArg(self, arg):
        self.module_args.append(arg)

    def addArgs(self, args):
        for arg in args:
            self.module_args.append(arg)

    def setArgs(self, args):
        self.module_args = []
        self.addArgs(args)

    def addKeywordArg(self, keyword, value):
        self.kw_args[keyword] = value

    def addStageFile(self, file_to_stage):
        self.files_to_stage.append(file_to_stage)

    def addStageFiles(self, files):
        for file_to_stage in files:
            self.files_to_stage.append(file_to_stage)

    def resetStageFiles(self):
        self.files_to_stage = []

    def getStageFiles(self):
        return self.files_to_stage

    def stage(self, stage_dir):
        for file_to_stage in self.files_to_stage:
            if os.path.dirname(file_to_stage) == stage_dir:
                # File is already there, skip it
                continue
            if os.path.exists(os.path.join(stage_dir,
                                           os.path.basename(file_to_stage))):
                # File is already there, skip it
                continue
            # print("Staging: %s to %s" % (file, stage_dir))
            shutil.copy2(file_to_stage, stage_dir)

    def getArgs(self):
        return self.module_args

    def getKeywordArgs(self):
        return self.kw_args

    def instantiate(self, sim_id):
        print()
        #print(self.module_name)
        #for arg in self.module_args:
        #       print arg
        #for kw_arg in self.kw_args.keys():
        #       print "keyword %s: value %s" % (kw_arg, self.kw_args[kw_arg])
        #       print kw_arg.__class__
        self.kw_args['sim_id'] = sim_id
        #kwargs = {"simID" : sim_id}
        #return globals()[self.module_name](*self.module_args, simID=my_simID)
        return globals()[self.module_name](*self.module_args, **self.kw_args)
