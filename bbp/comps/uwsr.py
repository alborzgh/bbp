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
import plot_seismograms
from install_cfg import InstallCfg
from station_list import StationList
from shutil import copy2

class uwsr(object):
    """
    Implement UW Site Response model as a python component
    """
    def __init__(self, i_r_stations, i_r_locfile, sim_id=0):
        self.r_stations = i_r_stations
        self.r_locfile = i_r_locfile
        self.sim_id = sim_id
        self.log = "uwsr_" + "%d" % (sim_id) + ".log"

    def convert_srt_to_bbp(self, inFilename, outFilename, type="acc"):
        outFile = open(outFilename, 'w')

        # write the headers
        if (type == "acc"):
            text = "# %15s %15s %15s %15s\n" % ("time(sec)  ", 
                    "N-S(cm/s/s)", "E-W(cm/s/s)","U-D(cm/s/s)")
        elif (type == "vel"):
            text = "# %15s %15s %15s %15s\n" % ("time(sec)  ", 
                    "N-S(cm/s)", "E-W(cm/s)","U-D(cm/s)")
        else:
            text = "# %15s %15s %15s %15s\n" % ("time(sec)  ", 
                    "N-S(cm)", "E-W(cm)","U-D(cm)")
        outFile.write(text)

        # the first line is zeros
        text = "%12.6e\t%12.6e\t%12.6e\t%12.6e\n" % (0,0,0,0)
        outFile.write(text)

        with open(inFilename, 'r') as f:
            for line in f:
                t, v1, v2, v3 = [float(x) for x in line.split()]
                text = "%12.6e\t%12.6e\t%12.6e\t%12.6e\n" % (t, 
                                  v1*100.0, v3*100.0, 0.0)
                outFile.write(text)

        outFile.close()

    def run(self):
        """
        This function prepares the parameters for UW Site response and then calls it
        """
        print("Nonlinear Site Response Analysis".center(80, '-'))

        install = InstallCfg.getInstance()
        sim_id = self.sim_id

        a_outdir = os.path.join(install.A_OUT_DATA_DIR, str(sim_id))
        a_tmpdir = os.path.join(install.A_TMP_DATA_DIR, str(sim_id))
        a_logdir = os.path.join(install.A_OUT_LOG_DIR, str(sim_id))
        a_indir  = os.path.join(install.A_IN_DATA_DIR, str(sim_id))

        a_statlist = os.path.join(a_indir, self.r_stations)
        slo = StationList(a_statlist)
        site_list = slo.getStationList()

        for idx,site in enumerate(site_list):
            print("==> Running nonlinear site response for station: %s" % (site.scode))
            
            # the velocity files for this site
            vel_file = os.path.join(a_outdir, "%d.%s.vel.bbp" %
                                    (sim_id, site.scode))

            log_file = os.path.join(a_logdir, "%d.%s.siteresponse.log" %
                                    (sim_id, site.scode))

            progstring = ("%s " %
                        (os.path.join(install.A_UW_BIN_DIR, "siteresponse")) +
                        "%s " % (self.r_locfile[idx]) +
                        "-bbp " +
                        "%s " % (vel_file)+
                        "%s " % (a_tmpdir)+
                        "%s " % (log_file))
            bband_utils.runprog(progstring)
            
            # copy results to the output directory
            tmp_acc_file = os.path.join(a_tmpdir, 'surface.acc')
            out_acc_file = os.path.join(a_outdir, "%d.%s.surf.acc.bbp" %
                                    (sim_id, site.scode))
            out_acc_png  = os.path.join(a_outdir, "%d.%s.surf.acc.png" %
                                    (sim_id, site.scode))
            self.convert_srt_to_bbp(tmp_acc_file, out_acc_file, "acc")

            tmp_vel_file = os.path.join(a_tmpdir, 'surface.vel')
            out_vel_file = os.path.join(a_outdir, "%d.%s.surf.vel.bbp" %
                                    (sim_id, site.scode))
            out_vel_png  = os.path.join(a_outdir, "%d.%s.surf.vel.png" %
                                    (sim_id, site.scode))
            self.convert_srt_to_bbp(tmp_vel_file, out_vel_file, "vel")

            # tmp_dsp_file = os.path.join(a_tmpdir, 'surface.disp')
            # out_dsp_file = os.path.join(a_outdir, "%d.%s.surf.disp.bbp" %
            #                         (sim_id, site.scode))
            # out_dsp_png  = os.path.join(a_outdir, "%d.%s.surf.disp.png" %
            #                         (sim_id, site.scode))
            # self.convert_srt_to_bbp(tmp_dsp_file, out_dsp_file, "disp")

            # plot seismograms at surface
            plot_seismograms.plot_seis(site.scode, out_acc_file, sim_id, 
                                                    'acc', out_acc_png)
            plot_seismograms.plot_seis(site.scode, out_vel_file, sim_id, 
                                                    'vel', out_vel_png)


if __name__ == "__main__":
    print("Testing Module: %s" % os.path.basename((sys.argv[0])))
