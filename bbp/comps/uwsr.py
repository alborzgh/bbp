#!/usr/bin/env python
"""
Southern California Earthquake Center Broadband Platform
Copyright 2010-2016 Southern California Earthquake Center

Broadband Platform Version of UW Site Response
Outputs velocity (cm/s)
$Id: uwsr.py #### 2018-10-31 17:40:00Z alborzgh $
"""
from __future__ import division, print_function

# Import Python modules
import ast
import os
import sys

# Import Broadband modules
import bband_utils
import validation_cfg
from install_cfg import InstallCfg
from station_list import StationList

class uwsr(object):
    """
    Implement UW Site Response model as a python component
    """
    def __init__(self, i_r_stations, i_r_locfile, sim_id=0):
        self.r_stations = i_r_stations
        self.r_locfile = i_r_locfile
        self.sim_id = sim_id
        self.log = "out"

    def run(self):
        """
        This function prepares the parameters for UW Site response and then calls it
        """
        print("Nonlinear Site Response Analysis".center(80, '-'))

        install = InstallCfg.getInstance()
        sim_id = self.sim_id

        a_outdir = os.path.join(install.A_OUT_DATA_DIR, str(sim_id))
        a_indir = os.path.join(install.A_IN_DATA_DIR, str(sim_id))

        a_statlist = os.path.join(a_indir, self.r_stations)
        slo = StationList(a_statlist)
        site_list = slo.getStationList()

        for site in site_list:
            print("==> Running nonlinear site response for station: %s" % (site.scode))
            
            # the velocity files for this site
            vel_file = os.path.join(a_outdir, "%d.%s.vel.bbp" %
                                    (sim_id, site.scode))

            progstring = ("%s " %
                        (os.path.join(install.A_GP_BIN_DIR, "../../uwsr/bin/siteresponse")) +
                        "%s " % (self.r_locfile) +
                        "-bbp " +
                        "%s " % (vel_file))
            bband_utils.runprog(progstring)
            print(progstring)


if __name__ == "__main__":
    print("Testing Module: %s" % os.path.basename((sys.argv[0])))
