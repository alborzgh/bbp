#!/usr/bin/env python
"""
Southern California Earthquake Center Broadband Platform
Copyright 2010-2016 Southern California Earthquake Center

This module takes care of building a workflow using either user
choices interactively, or an option file containing all needed
parameters.
$Id: build_workflow.py 1802 2017-02-16 23:05:54Z fsilva $
"""
from __future__ import division, print_function

# Import Python modules
import os
import sys

# Import Broadband modules
import bband_utils
import gmpe_config
import validation_cfg
import velocity_models
from module import Module
from install_cfg import InstallCfg

#
# Workflow consists of the following components:
# 1) Rupture generator - optional - GP or UCSB
#	a) Needs general fault description
#	b) Otherwise, must point to SRF file
# 2) Low frequency - GP, UCSB
# 3) High frequency - GP, UCSB, SDSU
# 4) Site response - GP, UCSB, SDSU
# 5) Merge (if necessary)
# 6) Map and Seismogram Plotting
# 7) Sa calculation (RotD50 code)
# 8) FAS Calculation (smc2fs2 code)
# 9) Goodness of Fit, if requested
#

class ConfigurationError(Exception):
    """
    Exception used to indicate that a configuration error was detected
    in the platform
    """
    pass

class WorkflowBuilder(object):
    """
    This class asks the user to select all simulation options and
    creates a workflow
    """
    def __init__(self, sim_id, expert_mode, opt_obj=None):
        """
        Initialize class parameters
        """
        self.sim_id = sim_id
        self.opt_obj = opt_obj
        self.expert_mode = expert_mode
        self.validation = None
        self.src_file = ""
        self.srf_file = None
        self.vel_file = None
        self.workflow = []
        self.install = InstallCfg.getInstance()
        self.tmpdir = os.path.join(self.install.A_TMP_DATA_DIR, str(sim_id))
        self.indir = os.path.join(self.install.A_IN_DATA_DIR, str(sim_id))
        self.vmodel_name = None
        self.vmodel_obj = None
        self.val_obj = None
        self.stations = None
        self.supplied_seis = False
        self.method = None
        self.added_obs_seis = False

    def select_simulation_method(self, sim_type):
        """
        This function asks the user what method he/she wants to use
        """
        while True:
            if self.opt_obj is not None:
                method = self.opt_obj.get_next_option()
            else:
                # Print header information about method selection
                print("=" * 80)
                print()
                print("The Broadband Platform includes several scientific"
                      " methods that can be used to calculate synthetic"
                      " seismograms.")
                print()
                method = raw_input("Choose a Method to use in this "
                                   "Broadband %s simulation:\n" % (sim_type) +
                                   "(1) GP (Graves & Pitarka)\n"
                                   "(2) UCSB\n"
                                   "(3) SDSU\n"
                                   "(4) EXSIM\n"
                                   "(5) CSM (Composite Source Model)"
                                   " - Beta Version\n"
                                   "(6) Song\n"
                                   "(7) Irikura Recipe Method 1\n"
                                   "? ")
            if (method == '1' or method.lower() == "graves & pitarka" or
                method.lower() == "gp"):
                return "GP"
            elif method == '2' or method.lower() == "ucsb":
                return "UCSB"
            elif method == '3' or method.lower() == "sdsu":
                return "SDSU"
            elif method == '4' or method.lower() == "exsim":
                return "EXSIM"
            elif method == '5' or method.lower() == "csm":
                return "CSM"
            elif (method == "6" or method.lower() == "song" or
                  method.lower() == "rmg"):
                return "SONG"
            elif method == "7" or method.lower() == "irikura":
                return "IRIKURA"
            else:
                print("%s is not a valid choice for method!\n" % (method))
                if self.opt_obj is not None:
                    sys.exit(1)

    def select_simulation_method_expert_mode(self, sim_type):
        """
        This function asks the user what method he/she wants to use
        """
        while True:
            if self.opt_obj is not None:
                method = self.opt_obj.get_next_option()
            else:
                # Print header information about method selection
                print("=" * 80)
                print()
                print("The Broadband Platform includes several scientific"
                      " methods that can be used to calculate synthetic"
                      " seismograms.")
                print()
                method = raw_input("Choose a Method to use in this "
                                   "Broadband %s simulation:\n" % (sim_type) +
                                   "(1) GP (Graves & Pitarka)\n"
                                   "(2) GP Seis (using precomp seismograms)\n"
                                   "(3) UCSB\n"
                                   "(4) SDSU\n"
                                   "(5) SDSU Seis (using precomp seismograms)\n"
                                   "(6) EXSIM\n"
                                   "(7) CSM (Composite Source Model)"
                                   " - Beta Version\n"
                                   "(8) Song\n"
                                   "(9) Irikura Recipe Method 1\n"
                                   "? ")
            if (method == '1' or method.lower() == "graves & pitarka" or
                method.lower() == "gp"):
                return "GP"
            elif (method == '2' or method.lower() == "gp seis" or
                  method.lower() == "gp precomp seismograms" or
                  method.lower() == "gp precomputed seismograms"):
                return "GPSeis"
            elif method == '3' or method.lower() == "ucsb":
                return "UCSB"
            elif method == '4' or method.lower() == "sdsu":
                return "SDSU"
            elif (method == '5' or method.lower() == "sdsu seis" or
                  method.lower() == "sdsu precomp seismograms" or
                  method.lower() == "sdsu seismograms"):
                return "SDSUSeis"
            elif method == '6' or method.lower() == "exsim":
                return "EXSIM"
            elif method == '7' or method.lower() == "csm":
                return "CSM"
            elif (method == "8" or method.lower() == "song" or
                  method.lower() == "rmg"):
                return "SONG"
            elif method == '9' or method.lower() == "irikura":
                return "IRIKURA"
            else:
                print("%s is not a valid choice for method!\n" % (method))
                if self.opt_obj is not None:
                    sys.exit(1)

    def get_validation_source_file(self, method):
        """
        This function selects a source file from a validation package.
        If multiple files exist, it asks the user to select which one
        to use for the simulation
        """
        src_file = self.val_obj.get_input(method, "source")
        if src_file is None or src_file == "":
            # We need an src file, cannot proceed
            print('*' * 80)
            print("The %s validation package does not " %
                  (self.val_obj.get_print_name()))
            print("include a source file for codebase %s" %
                  (method) +
                  ". Aborting...")
            print('*' * 80)
            sys.exit(1)

        # Only one file
        if isinstance(src_file, str):
            return src_file

        while True:
            if self.opt_obj is not None:
                src_option = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                question = ("Please select a src_file from the list"
                            " below:\n\n")
                for i in range(len(src_file)):
                    question = "%s(%d) %s\n" % (question,
                                                i + 1,
                                                os.path.basename(src_file[i]))

                src_option = raw_input("%s? " % question)
            try:
                choice = int(src_option)
            except ValueError:
                print("You must enter an integer!")
                if self.opt_obj is not None:
                    # Exit if processing an option file
                    sys.exit(1)
                continue
            try:
                if choice >= 1 and choice <= len(src_file):
                    src_file = src_file[choice - 1]
                    break
                else:
                    print("You must enter an integer from 1 to %d." %
                          (len(src_file)))
                    if self.opt_obj is not None:
                        # Exit if processing an option file
                        sys.exit(1)
            except TypeError:
                print("Invalid choice: %s" % (src_option))
                if self.opt_obj is not None:
                    # Exit if processing an option file
                    sys.exit(1)

        # Return src_file
        return src_file

    def select_source_file(self):
        """
        This function asks the user if he/she wants to provide a
        custom src file
        """
        if self.validation:
            while True:
                # Ask if user wants to provide a src_file
                if not self.expert_mode:
                    # Unless in expert mode, answer is no
                    user_src_file = 'n'
                elif self.opt_obj is not None:
                    user_src_file = self.opt_obj.get_next_option()
                else:
                    print("=" * 80)
                    print()
                    print("Each validation package includes a default source"
                          " description (SRC) file for a historical"
                          " event. Would you like to provide a different"
                          " file instead of the default file provided?"
                          " Answer 'no' here if you would like to use"
                          " the standard source file for this event.")
                    print()
                    user_src_file = raw_input("Do you want to provide "
                                              "a custom source file "
                                              "(y/n)? ")
                if (user_src_file.lower() == 'y' or
                    user_src_file.lower() == 'yes'):
                    # Get custom file from user (note that
                    # this overrides the selection in the
                    # validation package)
                    self.src_file = self.get_input_file("source "
                                                        "description",
                                                        ".src")
                    # Remember this src_file for later...
                    self.val_obj.set_input(self.method,
                                           "source",
                                           self.src_file)
                    break
                elif (user_src_file.lower() == 'n' or
                      user_src_file.lower() == 'no'):
                    src_method = self.method
                    if src_method == "SDSUSeis":
                        src_method = "SDSU"
                    if src_method == "GPSeis":
                        src_method = "GP"
                    # The src_file is provided as a "source" parameter
                    # to the selected rupture generator codebase
                    self.src_file = self.get_validation_source_file(src_method)
                    print('=' * 80)
                    print("SRC file: %s" % (self.src_file))
                    break
                else:
                    print("Invalid answer!")
                    if self.opt_obj is not None:
                        sys.exit(1)
        else:
            # Need source file
            if self.opt_obj is None:
                print()
                print("=" * 80)
                print()
                print("The source description (SRC) file contains a"
                      " description of the hypothetical (or scenario)"
                      " earthquake, including information like location"
                      ", geometry, magnitude, and mechanism.")
                print()
            self.src_file = self.get_input_file("source description",
                                                ".src")

    def select_site_response(self):
        """
        This function asks the user if he/she wants to run the site
        response module
        """
        while True:
            if self.opt_obj is not None:
                site_resp = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("Site Response")
                print("=============")
                print("Running a site response module is an optional step"
                      " while running a Broadband Platform simulation. It"
                      " requires a station list file containing the Vs30"
                      " values for each station location.")
                print()
                site_resp = raw_input("Do you want to run the "
                                      "site response module (y/n)? ")
            if site_resp.lower() == 'y' or site_resp.lower() == 'yes':
                return True
            elif site_resp.lower() == 'n' or site_resp.lower() == 'no':
                return False
            else:
                print("Invalid answer: %s " % (site_resp))
                if self.opt_obj is not None:
                    sys.exit(1)

    def check_velocity_models(self):
        """
        This function is used to make sure the needed velocity model
        file(s) exist(s)
        """
        # List of velocity models to check for...
        need_vm = []

        if self.method == "GP" or self.method == "GPSeis":
            need_vm = ["GP"]
        elif self.method == "UCSB":
            need_vm = ["UCSB"]
        elif self.method == "SDSU":
            need_vm = ["GP", "SDSU"]
        elif self.method == "SDSUSeis":
            need_vm = ["SDSU"]
        elif self.method == "EXSIM":
            need_vm = []
        elif self.method == "CSM":
            need_vm = ["CSM"]
        elif self.method == "SONG":
            need_vm = ["GP"]
        elif self.method == "IRIKURA":
            need_vm = ["GP"]
        else:
            raise ConfigurationError("Method %s not supported in the Platform" %
                                     (self.method))

        # Now check if they exist
        for item in need_vm:
            try:
                _ = self.vmodel_obj.get_velocity_model(item)
            except KeyError:
                print('*' * 80)
                print("Missing velocity model %s needed by the %s method!" %
                      (item, self.method))
                print("Aborting...")
                print('*' * 80)
                sys.exit(1)

    def run_gp_method(self, gen_srf):
        """
        This function creates a workflow for the Graves & Pitarka
        method
        """
        # Select velocity model for GP method
        self.vel_file = self.vmodel_obj.get_velocity_model("GP")

        # Set the supplied_seis flag if needed
        if self.method == "GPSeis":
            self.supplied_seis = True

        # Low Frequency GP module
        lf_module = Module()
        if self.supplied_seis:
            lf_module.setName("LFSeismograms")
            seis_dir = self.select_lf_seismograms()
            lf_module.addArg(seis_dir)
            lf_module.addStageFile(self.stations)
            lf_module.addArg(os.path.basename(self.stations))
            self.src_file = self.get_validation_source_file("GP")
        else:
            lf_module.setName("Jbsim")
            if self.validation:
                if not gen_srf:
                    self.srf_file = self.val_obj.get_input(self.method,
                                                           "srf")
                    if not self.srf_file:
                        self.srf_file = self.get_input_file("SRF", "srf")
            lf_module.addStageFile(self.vel_file)
            lf_module.addArg(os.path.basename(self.vel_file))
            if self.src_file is not None and self.src_file != "":
                # we supplied a source file, so stage it
                lf_module.addStageFile(self.src_file)
            if not gen_srf:
                # not generating an SRF, so we stage it
                lf_module.addStageFile(self.srf_file)
            lf_module.addArg(os.path.basename(self.src_file))
            lf_module.addArg(os.path.basename(self.srf_file))
            lf_module.addStageFile(self.stations)
            lf_module.addArg(os.path.basename(self.stations))
            lf_module.addArg(self.vmodel_name)
        self.workflow.append(lf_module)

        # High Frequency GP module
        hf_module = Module()
        hf_module.setName("Hfsims")
        hf_module.addStageFile(self.vel_file)
        hf_module.addArg(os.path.basename(self.vel_file))

        if self.validation:
            if not gen_srf:
                # If we are not running the rupture generator,
                # pick up srf_file from the validation
                # configuration
                if not self.srf_file:
                    self.srf_file = self.val_obj.get_input("GP", "srf")
            hf_module.addKeywordArg("val_name",
                                    self.val_obj.get_validation_name())
        if self.src_file is not None and self.src_file != "":
            hf_module.addStageFile(self.src_file)
        if not gen_srf and self.srf_file is not None and self.srf_file != "":
            hf_module.addStageFile(self.srf_file)
        hf_module.addArg(os.path.basename(self.src_file))
        hf_module.addArg(os.path.basename(self.srf_file))
        hf_module.addStageFile(self.stations)
        hf_module.addArg(os.path.basename(self.stations))
        hf_module.addArg(self.vmodel_name)
        self.workflow.append(hf_module)

        # Site response module
        if self.expert_mode:
            run_site_resp = self.select_site_response()
        else:
            run_site_resp = False
        if run_site_resp:
            site_module = Module()
            site_module.setName("WccSiteamp")
            site_module.addStageFile(self.stations)
            site_module.addArg(os.path.basename(self.stations))
            site_module.addArg("GP")
            self.workflow.append(site_module)

            # And then, add the Match module
            merge_module = Module()
            merge_module.setName("Match")
            merge_module.addStageFile(self.stations)
            merge_module.addArg(os.path.basename(self.stations))
            merge_module.addArg(self.vmodel_name)
            merge_module.addKeywordArg('acc', True)
            self.workflow.append(merge_module)
        else:
            # Not running site response
            merge_module = Module()
            merge_module.setName("Match")
            merge_module.addStageFile(self.stations)
            merge_module.addArg(os.path.basename(self.stations))
            merge_module.addArg(self.vmodel_name)
            merge_module.addKeywordArg('acc', False)
            self.workflow.append(merge_module)

    def run_ucsb_method(self, gen_srf):
        """
        This function creates a workflow for the UCSB method
        """
        # Select velocity model for UCSB method
        self.vel_file = self.vmodel_obj.get_velocity_model("UCSB")

        # Low and High Frequency module (we only need to run Syn1D once)
        lf_module = Module()
        lf_module.setName("Syn1D")
        if self.validation:
            if not gen_srf:
                self.srf_file = self.val_obj.get_input("UCSB", "srf")
                if not self.srf_file:
                    raise ConfigurationError("Not running rupture generator"
                                             " and no SRF file specified "
                                             "for code UCSB")
        lf_module.addStageFile(self.vel_file)
        lf_module.addArg(os.path.basename(self.vel_file))
        if self.src_file is not None and self.src_file != "":
            # we supplied a source file, so stage it
            lf_module.addStageFile(self.src_file)
        if not gen_srf:
            # not generating an SRF, so we stage it
            lf_module.addStageFile(self.srf_file)
        lf_module.addArg(os.path.basename(self.src_file))
        lf_module.addArg(os.path.basename(self.srf_file))
        lf_module.addStageFile(self.stations)
        lf_module.addArg(os.path.basename(self.stations))
        lf_module.addArg(self.vmodel_name)
        self.workflow.append(lf_module)

        # Site response module
        if self.expert_mode:
            if self.select_site_response():
                site_module = Module()
                site_module.setName("WccSiteamp")
                site_module.addStageFile(self.stations)
                site_module.addArg(os.path.basename(self.stations))
                site_module.addArg("UCSB")
                self.workflow.append(site_module)
                return

        #if run_site_resp:
        #    site_module = Module()
        #    site_module.setName("UCSite")
        #    site_module.addStageFile(self.vel_file)
        #    site_module.addArg(os.path.basename(self.vel_file))
        #    if self.src_file is not None and self.src_file != "":
        #        site_module.addStageFile(self.src_file)
        #    site_module.addArg(os.path.basename(self.src_file))
        #    site_module.addStageFile(self.stations)
        #    site_module.addArg(os.path.basename(self.stations))
        #    self.workflow.append(site_module)

        # This method produces a hybrid velocity seismogram in
        # the tmpdata directory, we just need to create the
        # acceleration seismograms, and make sure both
        # velocity and acceleration seismograms are copied
        # also to the outdata directory
        merge_module = Module()
        merge_module.setName("CopySeismograms")
        merge_module.addStageFile(self.stations)
        merge_module.addArg(os.path.basename(self.stations))
        merge_module.addKeywordArg('hybrid', True)
        self.workflow.append(merge_module)

    def run_sdsu_method(self, gen_srf):
        """
        This function creates a workflow for the SDSU method
        """
        # Set the supplied_seis flag if needed
        if self.method == "SDSUSeis":
            self.supplied_seis = True

        lf_module = Module()
        if self.supplied_seis:
            lf_module.setName("LFSeismograms")
            seis_dir = self.select_lf_seismograms()
            if not gen_srf:
                self.srf_file = self.val_obj.get_input("GP", 'SRF')
                if self.srf_file is None:
                    raise ConfigurationError("SRF parameter is missing"
                                             " from codebase GP!")
            self.src_file = self.get_validation_source_file("SDSU")
            lf_module.addArg(seis_dir)
            lf_module.addStageFile(self.stations)
            lf_module.addArg(os.path.basename(self.stations))
        else:
            lf_module.setName("Jbsim")
            if self.validation:
                if not gen_srf:
                    self.srf_file = self.val_obj.get_input("GP", "srf")
                    if not self.srf_file:
                        self.srf_file = self.get_input_file("SRF", "srf")
            # Select velocity model for GP method for now
            self.vel_file = self.vmodel_obj.get_velocity_model("GP")
            lf_module.addStageFile(self.vel_file)
            lf_module.addArg(os.path.basename(self.vel_file))
            if self.src_file is not None and self.src_file != "":
                # we supplied a source file, so stage it
                lf_module.addStageFile(self.src_file)
            if not gen_srf:
                # not generating an SRF, so we stage it
                lf_module.addStageFile(self.srf_file)
            lf_module.addArg(os.path.basename(self.src_file))
            lf_module.addArg(os.path.basename(self.srf_file))
            lf_module.addStageFile(self.stations)
            lf_module.addArg(os.path.basename(self.stations))
            lf_module.addArg(self.vmodel_name)
        self.workflow.append(lf_module)

        # Select velocity model for SDSU method
        self.vel_file = self.vmodel_obj.get_velocity_model("SDSU")

        # High Frequency GP module
        hf_module = Module()
        hf_module.setName("BBToolbox")
        scattering = None
        if self.validation:
            # If we are doing validation, allow user to
            # override default scattering file
            scattering = self.val_obj.get_input("SDSU", "scattering")
        if scattering is None:
            scattering = ""
        else:
            hf_module.addStageFile(scattering)
        hf_module.addArg(os.path.basename(scattering))
        hf_module.addStageFile(self.vel_file)
        hf_module.addArg(os.path.basename(self.vel_file))
        if self.validation:
            if not gen_srf:
                # If we are not running the rupture generator,
                # pick up srf_file from the validation
                # configuration
                if not self.srf_file:
                    if not self.supplied_seis:
                        self.srf_file = self.val_obj.get_input("GP", "srf")
                    else:
                        # self.srf_file is already set about 70 lines above
                        pass
        if self.src_file is not None and self.src_file != "":
            hf_module.addStageFile(self.src_file)
        if not gen_srf and self.srf_file is not None and self.srf_file != "":
            hf_module.addStageFile(self.srf_file)
        hf_module.addArg(os.path.basename(self.src_file))
        hf_module.addArg(os.path.basename(self.srf_file))
        hf_module.addStageFile(self.stations)
        hf_module.addArg(os.path.basename(self.stations))
        hf_module.addArg(self.vmodel_name)
        self.workflow.append(hf_module)

        # Site response module
        if self.expert_mode:
            if self.select_site_response():
                site_module = Module()
                site_module.setName("WccSiteamp")
                site_module.addStageFile(self.stations)
                site_module.addArg(os.path.basename(self.stations))
                site_module.addArg("SDSU")
                self.workflow.append(site_module)
                return

        # Not running site response, use the
        # CopySeismograms module to wrap things up

        # This method produces a hybrid velocity seismogram in
        # the tmpdata directory, we just need to create the
        # acceleration seismograms, and make sure both
        # velocity and acceleration seismograms are copied
        # also to the outdata directory
        merge_module = Module()
        merge_module.setName("CopySeismograms")
        merge_module.addStageFile(self.stations)
        merge_module.addArg(os.path.basename(self.stations))
        merge_module.addKeywordArg('hybrid', True)
        self.workflow.append(merge_module)

    def run_exsim_method(self):
        """
        This function creates a workflow for the EXSIM method
        """
        exsim_module = Module()
        exsim_module.setName("ExSim")
        # Make sure SRC file exists and is valid
        if self.src_file is None or self.src_file == "":
            raise ConfigurationError("ExSim module requires a SRC file")
        exsim_module.addStageFile(self.src_file)
        exsim_module.addArg(os.path.basename(self.src_file))
        # Now, figure out where is the ExSim's template file
        template_file = None
        # See if we have a default template file for this region
        vmodel_params = self.vmodel_obj.get_codebase_params('exsim')
        if 'GENERIC_PARAM' in vmodel_params:
            if (vmodel_params['GENERIC_PARAM'] != "" and
                vmodel_params['GENERIC_PARAM'] is not None):
                template_file = os.path.join(self.vmodel_obj.base_dir,
                                             vmodel_params['GENERIC_PARAM'])
                if self.expert_mode:
                    # If in expert mode, ask if user wants to provide
                    # custom file even if we already have a default
                    # one
                    while True:
                        if self.opt_obj is not None:
                            custom = self.opt_obj.get_next_option()
                        else:
                            print()
                            print("=" * 80)
                            print()
                            custom = raw_input("Would you like to specify a "
                                               "custom ExSIM template file "
                                               "(y/n)? ")
                        if custom.lower() == 'y' or custom.lower() == 'yes':
                            template_file = self.get_input_file("ExSim "
                                                                "Template "
                                                                "file",
                                                                ".exsim")
                            break
                        elif (custom.lower() == 'n' or
                              custom.lower() == 'no'):
                            break
                        else:
                            print("Invalid choice (custom template): %s" %
                                  (custom))
                            if self.opt_obj is not None:
                                sys.exit(1)
        # No default file, ask the user
        if template_file is None:
            template_file = self.get_input_file("ExSim Template file",
                                                ".exsim")
        exsim_module.addStageFile(template_file)
        exsim_module.addArg(os.path.basename(template_file))
        exsim_module.addStageFile(self.stations)
        exsim_module.addArg(os.path.basename(self.stations))
        exsim_module.addArg(self.vmodel_name)
        self.workflow.append(exsim_module)

        # Site response module
        if self.expert_mode:
            if self.select_site_response():
                site_module = Module()
                site_module.setName("WccSiteamp")
                site_module.addStageFile(self.stations)
                site_module.addArg(os.path.basename(self.stations))
                site_module.addArg("EXSIM")
                self.workflow.append(site_module)

    def run_csm_method(self):
        """
        This function creates a workflow for the CSM method
        """
        csm_module = Module()
        csm_module.setName("CSM")
        # Make sure SRC file exists and is valid
        if self.src_file is None or self.src_file == "":
            raise ConfigurationError("CSM module requires a SRC file")
        csm_module.addStageFile(self.src_file)
        csm_module.addArg(os.path.basename(self.src_file))
        # Select CSM velocity model for the Composite Source Model method
        self.vel_file = self.vmodel_obj.get_velocity_model("CSM")
        csm_module.addStageFile(self.vel_file)
        csm_module.addArg(os.path.basename(self.vel_file))
        csm_module.addStageFile(self.stations)
        csm_module.addArg(os.path.basename(self.stations))
        csm_module.addArg(self.vmodel_name)
        # Add validation name if running a validation run
        if self.validation:
            csm_module.addKeywordArg("val_name",
                                     self.val_obj.get_validation_name())
        self.workflow.append(csm_module)

    def make_choices(self, gen_srf):
        """
        This function calls a method-specific function, then adds the
        common processing modules used in the Broadband Platform
        """
        # Fist, call the method-specific function
        if self.method == "GP" or self.method == "GPSeis":
            self.run_gp_method(gen_srf)
        elif self.method == "UCSB":
            self.run_ucsb_method(gen_srf)
        elif self.method == "SDSU" or self.method == "SDSUSeis":
            self.run_sdsu_method(gen_srf)
        elif self.method == "EXSIM":
            self.run_exsim_method()
        elif self.method == "CSM":
            self.run_csm_method()
        elif self.method == "SONG":
            self.run_gp_method(gen_srf)
        elif self.method == "IRIKURA":
            self.run_gp_method(gen_srf)
        else:
            raise ConfigurationError("Method %s not supported in the Platform" %
                                     (self.method))

        # Now, add the plot modules
        if self.srf_file is None:
            # To allow basename to work
            self.srf_file = ""

        # Plot Map module
        plot_map_module = Module()
        plot_map_module.setName("Plot_Map")
        if not gen_srf and self.srf_file is not None and self.srf_file != "":
            # Use the SRF file for plotting when we are not running
            # the rupture generator and already have a user-provided
            # SRF file
            plot_map_module.addStageFile(self.srf_file)
            plot_map_module.addArg(os.path.basename(self.srf_file))
        else:
            # Otherwise, if we run the rupture generator, let's use
            # the src file instead
            plot_map_module.addStageFile(self.src_file)
            plot_map_module.addArg(os.path.basename(self.src_file))
        plot_map_module.addStageFile(self.stations)
        plot_map_module.addArg(os.path.basename(self.stations))
        self.workflow.append(plot_map_module)

        # Now the plot seismograms module
        plot_seis_module = Module()
        plot_seis_module.setName("PlotSeis")
        plot_seis_module.addArg(os.path.basename(self.stations))
        plot_seis_module.addStageFile(self.stations)
        if self.src_file is not None and self.src_file != "":
            plot_seis_module.addStageFile(self.src_file)
            plot_seis_module.addArg(os.path.basename(self.src_file))
        else:
            plot_seis_module.addArg(self.src_file)

        if self.expert_mode:
            # Plot velocity seismograms?
            while True:
                if self.opt_obj is not None:
                    plot_vel = self.opt_obj.get_next_option()
                else:
                    print("=" * 80)
                    plot_vel = raw_input("Do you want to generate "
                                         "velocity seismograms' plots (y/n)? ")
                if plot_vel.lower() == 'y' or plot_vel.lower() == 'yes':
                    plot_seis_module.addArg(True)
                    break
                elif plot_vel.lower() == 'n' or plot_vel.lower() == 'no':
                    plot_seis_module.addArg(False)
                    break
                else:
                    print("Invalid choice: " % (plot_vel))
                    if self.opt_obj is not None:
                        sys.exit(1)
        else:
            plot_seis_module.addArg(True)

        if self.expert_mode:
            # Plot acceleration seismograms?
            while True:
                if self.opt_obj is not None:
                    plot_acc = self.opt_obj.get_next_option()
                else:
                    print("=" * 80)
                    plot_acc = raw_input("Do you want to generate acceleration"
                                         " seismograms' plots (y/n)? ")
                if plot_acc.lower() == 'y' or plot_acc.lower() == 'yes':
                    plot_seis_module.addArg(True)
                    break
                elif plot_acc.lower() == 'n' or plot_acc.lower() == 'no':
                    plot_seis_module.addArg(False)
                    break
                else:
                    print("Invalid choice: %s " % (plot_acc))
                    if self.opt_obj is not None:
                        sys.exit(1)
        else:
            plot_seis_module.addArg(True)

        self.workflow.append(plot_seis_module)

        # RotD50 module
        rotd50_module = Module()
        rotd50_module.setName("RotD50")
        rotd50_module.addStageFile(self.stations)
        rotd50_module.addArg(os.path.basename(self.stations))
        self.workflow.append(rotd50_module)

    def do_val_gmpe(self):
        """
        This function asks the user if we should generate GMPE
        comparisons for this validation simulation
        """
        # Generate GMPE comparison plot?
        while True:
            if not self.expert_mode:
                # Only ask user in expert mode
                plot_gmpe = 'y'
            elif self.opt_obj is not None:
                plot_gmpe = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("The Broadband Platform can generate comparison"
                      " plots of the validation data against GMPEs to"
                      " show how GMPEs match the recorded data for a"
                      " certain event.")
                print()
                plot_gmpe = raw_input("Do you want to generate "
                                      "a GMPE comparison plot (y/n)? ")
            if plot_gmpe.lower() == 'y' or plot_gmpe.lower() == 'yes':
                break
            elif plot_gmpe.lower() == 'n' or plot_gmpe.lower() == 'no':
                return
            else:
                print("Invalid choice: %s" % (plot_gmpe))
                if self.opt_obj is not None:
                    sys.exit(1)

        # User wants GMPE comparison plots, ask which gmpe set to use
        gmpe_group_name = self.select_gmpe_model()

        if self.src_file is None or self.src_file == "":
            # We need an src file, cannot proceed
            print("SRC file is not specified, skipping GMPE comparison!")
            return

        # Create GMPE results
        gmpe_module = Module()
        gmpe_module.setName("CalculateGMPE")
        gmpe_module.addStageFile(self.stations)
        gmpe_module.addArg(os.path.basename(self.stations))
        gmpe_module.addStageFile(self.src_file)
        gmpe_module.addArg(os.path.basename(self.src_file))
        gmpe_module.addArg(self.val_obj.get_validation_name())
        if self.val_obj.get_obs_corrections():
            gmpe_module.addArg(True)
        else:
            gmpe_module.addArg(False)
        gmpe_module.addArg(gmpe_group_name)
        self.workflow.append(gmpe_module)

        if self.val_obj.get_event_type().lower() == "gmpe":
            # Generate per-station comparison plots between calculated
            # seismograms and GMPE data
            gmpe_module = Module()
            gmpe_module.setName("GMPEPlot")
            gmpe_module.addStageFile(self.stations)
            gmpe_module.addArg(os.path.basename(self.stations))
            gmpe_module.addArg(self.val_obj.get_obs_format())
            gmpe_module.addArg(self.val_obj.get_magnitude())
            gmpe_module.addArg(self.val_obj.get_validation_name())
            gmpe_module.addArg(gmpe_group_name)
            self.workflow.append(gmpe_module)
        else:
            if not self.added_obs_seis:
                # First, we prepare the observations
                obs_module = Module()
                obs_module.setName("ObsSeismograms")
                obs_module.addStageFile(self.stations)
                if self.val_obj.get_obs_corrections():
                    obs_module.addStageFile(self.val_obj.get_obs_corrections())
                obs_module.addArg(os.path.basename(self.stations))
                obs_module.addArg(self.val_obj.get_obs_path())
                obs_module.addArg(self.val_obj.get_obs_format())
                obs_module.addArg(os.path.basename(self.val_obj.get_obs_corrections()))
                self.added_obs_seis = True
                self.workflow.append(obs_module)

            gmpe_comp_module = Module()
            gmpe_comp_module.setName("GMPEComparison")
            gmpe_comp_module.addStageFile(self.stations)
            gmpe_comp_module.addArg(os.path.basename(self.stations))
            gmpe_comp_module.addStageFile(self.src_file)
            gmpe_comp_module.addArg(os.path.basename(self.src_file))
            gmpe_comp_module.addArg(self.val_obj.get_validation_name())
            gmpe_comp_module.addArg(gmpe_group_name)
            self.workflow.append(gmpe_comp_module)

    def do_calculate_validation_parameters(self):
        """
        This function prompts the user to select what additional
        parameters (if any) to calculate.
        """
        # No extra parameters calculated in expert mode for now
        if not self.expert_mode:
            return

        while True:
            if self.opt_obj is not None:
                do_more_metrics = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("Additional Metrics")
                print("==================")
                print("Calculating additional metrics is an optional step "
                      "on the Broadband Platform. It creates additional "
                      "plots and data files that can be used to study "
                      "the simulation.")
                print()
                do_more_metrics = raw_input("Do you want to calculate "
                                            "additional metrics (y/n)? ")

            if do_more_metrics.lower() == 'n':
                # Nothing to do, return
                return
            elif do_more_metrics.lower() == 'y':
                # Ok, let ask more questions...
                break
            else:
                print("Invalid choice (Additional Metrics): %s" %
                      (do_more_metrics))
                if self.opt_obj is not None:
                    sys.exit(1)

        while True:
            if self.opt_obj is not None:
                do_rzz2015 = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("RZZ2015 Metrics")
                print("===============")
                print("Additional metrics defined in "
                      "Rezaeian-Zhong-Zareian 2015")
                print()
                do_rzz2015 = raw_input("Do you want to calculate "
                                       "the RZZ2015 metrics (y/n)? ")

            if do_rzz2015.lower() == 'n':
                # Skip this one
                break
            elif do_rzz2015.lower() == 'y':
                # Let's add the RZZ2015 module
                rzz_module = Module()
                rzz_module.setName("RZZ2015")
                rzz_module.addStageFile(self.stations)
                rzz_module.addArg(os.path.basename(self.stations))
                rzz_module.addArg(self.val_obj.get_validation_name())
                self.workflow.append(rzz_module)
                # Now, let's add the RZZ2015 GMPE module
                rzz_gmpe_module = Module()
                rzz_gmpe_module.setName("RZZ2015GMPE")
                rzz_gmpe_module.addStageFile(self.stations)
                rzz_gmpe_module.addArg(os.path.basename(self.stations))
                if self.src_file is not None and self.src_file != "":
                    rzz_gmpe_module.addStageFile(self.src_file)
                else:
                    raise bband_utils.ParameterError("SRC file needed for "
                                                     "RZZ2015 GMPE module!")
                rzz_gmpe_module.addArg(os.path.basename(self.src_file))
                self.workflow.append(rzz_gmpe_module)
                break
            else:
                print("Invalid choice (RZZ2015): %s" % (do_rzz2015))
                if self.opt_obj is not None:
                    sys.exit(1)

        while True:
            if self.opt_obj is not None:
                do_fas = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("FAS")
                print("===============")
                print("Additional FAS metrics")
                print()
                do_fas = raw_input("Do you want to calculate "
                                   "FAS metrics (y/n)? ")

            if do_fas.lower() == 'n':
                # Skip this one
                break
            elif do_fas.lower() == 'y':
                # Let's add the FAS module
                fas_module = Module()
                fas_module.setName("FAS")
                fas_module.addStageFile(self.stations)
                fas_module.addArg(os.path.basename(self.stations))
                self.workflow.append(fas_module)
                break
            else:
                print("Invalid choice (FAS): %s" % (do_fas))
                if self.opt_obj is not None:
                    sys.exit(1)

        while True:
            if self.opt_obj is not None:
                do_as2016 = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("AS2016 GMPE")
                print("===========")
                print("Additional GMPE for significant duration defined in "
                      "Afshari and Stewart 2016")
                print()
                do_as2016 = raw_input("Do you want to calculate "
                                      "the AS2016 metrics (y/n)? ")

            if do_as2016.lower() == 'n':
                # Skip this one
                break
            elif do_as2016.lower() == 'y':
                # Let's add the module
                as16_module = Module()
                as16_module.setName("AS16")
                as16_module.addStageFile(self.stations)
                if self.src_file is not None and self.src_file != "":
                    as16_module.addStageFile(self.src_file)
                else:
                    raise bband_utils.ParameterError("SRC file needed for "
                                                     "AS16 module!")
                as16_module.addArg(os.path.basename(self.stations))
                as16_module.addArg(os.path.basename(self.src_file))
                as16_module.addArg(self.val_obj.get_validation_name())
                self.workflow.append(as16_module)
                break
            else:
                print("Invalid choice (AS2016): %s" % (do_as2016))
                if self.opt_obj is not None:
                    sys.exit(1)

        while True:
            if self.opt_obj is not None:
                do_rd100 = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("RotD100")
                print("===========")
                print("Ratio of maximum to median responses across orientations")
                print()
                do_rd100 = raw_input("Do you want to calculate "
                                     "the RotD100 metrics (y/n)? ")

            if do_rd100.lower() == 'n':
                # Skip this one
                break
            elif do_rd100.lower() == 'y':
                # Let's add the module
                rd100_module = Module()
                rd100_module.setName("RotD100")
                rd100_module.addStageFile(self.stations)
                if self.val_obj.get_obs_corrections():
                    rd100_module.addStageFile(self.val_obj.get_obs_corrections())
                if self.src_file is not None and self.src_file != "":
                    rd100_module.addStageFile(self.src_file)
                else:
                    raise bband_utils.ParameterError("SRC file needed for "
                                                     "RotD100 module!")
                rd100_module.addArg(os.path.basename(self.src_file))
                rd100_module.addArg(os.path.basename(self.stations))
                rd100_module.addArg(self.val_obj.get_obs_path())
                rd100_module.addArg(self.val_obj.get_obs_format())
                rd100_module.addArg(os.path.basename(self.val_obj.get_obs_corrections()))
                rd100_module.addArg(self.val_obj.get_magnitude())
                rd100_module.addArg(self.val_obj.get_validation_name())
                rd100_module.addArg(self.val_obj.get_cutoff())
                self.workflow.append(rd100_module)
                break
            else:
                print("Invalid choice (RotD100): %s" % (do_rd100))
                if self.opt_obj is not None:
                    sys.exit(1)

        while True:
            if self.opt_obj is not None:
                do_anderson_gof = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("Anderson GoF (2004)")
                print("===========")
                print("Anderson GoF (2004) calculates 10 extra metrics")
                print()
                do_anderson_gof = raw_input("Do you want to calculate "
                                            "the Anderson GoF (2004) "
                                            "metrics (y/n)? ")

            if do_anderson_gof.lower() == 'n':
                # Skip this one
                break
            elif do_anderson_gof.lower() == 'y':
                # Let's add the module
                anderson_module = Module()
                anderson_module.setName("AndersonGOF")
                anderson_module.addStageFile(self.stations)
                anderson_module.addArg(os.path.basename(self.stations))
                anderson_module.addArg(self.val_obj.get_validation_name())
                self.workflow.append(anderson_module)
                break
            else:
                print("Invalid choice (Anderson GoF): %s" % (do_anderson_gof))
                if self.opt_obj is not None:
                    sys.exit(1)

    def do_gof(self, gen_srf):
        """
        This function prompts the user to select a Goofness of Fit
        module. It adds the selected module to the workflow.
        """

        while True:
            if not self.expert_mode:
                gof = 'y'
            elif self.opt_obj is not None:
                gof = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("Goodness-of-Fit Plot")
                print("====================")
                print("Running a goodness-of-fit (GoF) module is an optional "
                      " step while running a Broadband Platform simulation. It"
                      " creates a comparison plot showing how well the "
                      " calculated seismograms fit recorded data.")
                print()
                gof = raw_input("Do you want to run a "
                                "goodness-of-fit module (y/n)? ")

            if gof.lower() == 'n':
                # Nothing to do, return
                return
            elif gof.lower() == 'y':
                # Ok, let's ask what type
                break
            else:
                print("Invalid choice (GOF Module): %s" % (gof))
                if self.opt_obj is not None:
                    sys.exit(1)

        if self.validation:
            # doing GOF
            while True:
                if not self.expert_mode:
                    # We do GP GOF unless in expert mode
                    gof_opt = '1'
                elif self.opt_obj is not None:
                    gof_opt = self.opt_obj.get_next_option()
                else:
                    print("=" * 80)
                    print()
                    print("Users can optionally select a Goodness of Fit"
                          " module to plot a comparison of how well"
                          " the simulated seismograms match the"
                          " recorded data in a historical event.")
                    print()
                    gof_opt = raw_input("Choose a "
                                        "Goodness of Fit (GOF) Module:\n"
                                        "(1) GP\n"
                                        "(2) SDSU\n"
                                        "(3) Both\n"
                                        "? ")
                # Check if response is valid
                if gof_opt == "1" or gof_opt == "2" or gof_opt == "3":
                    if not self.added_obs_seis:
                        # First, we prepare the observations
                        obs_module = Module()
                        obs_module.setName("ObsSeismograms")
                        obs_module.addStageFile(self.stations)
                        if self.val_obj.get_obs_corrections():
                            obs_module.addStageFile(self.val_obj.get_obs_corrections())
                        obs_module.addArg(os.path.basename(self.stations))
                        obs_module.addArg(self.val_obj.get_obs_path())
                        obs_module.addArg(self.val_obj.get_obs_format())
                        obs_module.addArg(os.path.basename(self.val_obj.get_obs_corrections()))
                        self.workflow.append(obs_module)
                        self.added_obs_seis = True
                    # Now, we generate basic plots, such as
                    # rotd50, and seismogram overlay
                    # comparisons But, we don't do this for EXSIM,
                    # as we don't have calculated seismograms to
                    # compare against
                    gen_plots_module = Module()
                    gen_plots_module.setName("GenPlots")
                    gen_plots_module.addStageFile(self.stations)
                    gen_plots_module.addArg(os.path.basename(self.stations))
                    gen_plots_module.addArg(self.val_obj.get_obs_path())
                    gen_plots_module.addArg('acc')
                    gen_plots_module.addArg(self.val_obj.get_validation_name())
                    self.workflow.append(gen_plots_module)
                    # Now pick the GOF module(s) that we want
                    if gof_opt == "1" or gof_opt == "3":
                        # Add GP GOF module
                        gof_module = Module()
                        gof_module.setName("GPGof")
                        if (self.src_file is not None and
                            self.src_file != ""):
                            # Always use the SRC file if we have one!
                            gof_module.addStageFile(self.src_file)
                            gof_module.addArg(os.path.basename(self.src_file))
                        elif (not gen_srf and
                            self.srf_file is not None and
                            self.srf_file != ""):
                            # Use the SRF file for plotting when we are not running
                            # the rupture generator and already have a user-provided
                            # SRF file
                            gof_module.addStageFile(self.srf_file)
                            gof_module.addArg(os.path.basename(self.srf_file))
                        else:
                            # Otherwise, if we run the rupture generator, let's use
                            # the src file instead
                            raise bband_utils.ParameterError("SRC file needed for GoF")
                        gof_module.addStageFile(self.stations)
                        gof_module.addArg(os.path.basename(self.stations))
                        gof_module.addArg(self.val_obj.get_magnitude())
                        gof_module.addArg(self.val_obj.get_validation_name())
                        gof_module.addArg(self.val_obj.get_cutoff())
                        if self.method == "EXSIM":
                            gof_module.addKeywordArg("single_component", True)
                        else:
                            gof_module.addKeywordArg("single_component", False)
                        self.workflow.append(gof_module)
                    if gof_opt == "2" or gof_opt == "3":
                        # Add SDSU GOF module
                        gof_module = Module()
                        gof_module.setName("SDSUMOGoF")
                        gof_module.addStageFile(self.stations)
                        gof_module.addArg(os.path.basename(self.stations))
                        gof_weights = self.do_gof_metrics()
                        gof_module.addArg(gof_weights)
                        # Next param is MOGof_Plot_Map
                        gof_module.addArg(True)
                        gof_module.addArg(self.val_obj.get_obs_path())
                        gof_module.addArg('A')
                        gof_module.addArg(self.val_obj.get_magnitude())
                        gof_module.addArg(self.val_obj.get_validation_name())
                        self.workflow.append(gof_module)
                    break

                # Not a valid option!
                print("Invalid choice: %s" % (gof_opt))
                if self.opt_obj is not None:
                    sys.exit(1)
#         else:
#             while True:
#                 if self.opt_obj is not None:
#                     gof = self.opt_obj.get_next_option()
#                 else:
#                     gof = raw_input("Do you want to run goodness of fit (y/n)? ")

#                 if gof.lower() == 'y':
#                     # Need to get the data directory, magnitude, comparison label
#                     if self.opt_obj is not None:
#                         data_id = self.opt_obj.get_next_option()
#                     else:
#                         data_id = raw_input("What reference files would you "
#                                             "like to compare to? Enter a "
#                                             "simulation ID or "
#                                             "a scenario name: ")
#                     try:
#                         data_num = int(data_id)
#                     except ValueError:
#                         if self.install.A_VAL_DIR is not None:
#                             # Let's check if data exists for this scenario
#                             if os.path.exists(os.path.join(self.install.A_VAL_DIR,
#                                                            data_id, "gp", "AccBBP")):
#                                 # Directory exists
#                                 data_num = -1
#                             else:
#                                 raise ValueError("Cannot find scenario %s data" %
#                                                  (data_id))
#                         else:
#                             raise ValueError("Cannot find validation package!")

#                     if self.src_file != "":
#                         src_fp = open(self.src_file, 'r')
#                         for line in src_fp:
#                             pieces = line.split('=')
#                             if pieces[0].strip() == 'MAGNITUDE':
#                                 mag = float(pieces[1])
#                                 break
#                         src_fp.close()
#                     else:
#                         # Calculate from SRF
#                         mag = fault_utils.get_magnitude(self.vel_file, self.srf_file)

#                     if self.opt_obj is not None:
#                         comp_label = self.opt_obj.getNextInput()
#                     else:
#                         comp_label = raw_input("Enter a label to use for the "
#                                                "comparison seismograms: ")

#                     # Figure out the observation directory
#                     if data_num != -1:
#                         obs_dir = os.path.join(self.install.A_OUT_DATA_DIR,
#                                                data_num)
#                     else:
#                         obs_dir = os.path.join(self.install.A_VAL_DIR,
#                                                data_id, "gp", "AccBBP")

#                     # First, we prepare the observations
#                     obs_module = Module()
#                     obs_module.setName("ObsSeismograms")
#                     obs_module.addStageFile(self.stations)
#                     obs_module.addArg(os.path.basename(self.stations))
#                     obs_module.addArg(obs_dir)
#                     if data_num != -1:
#                         obs_module.addArg("vel")
#                     else:
#                         obs_module.addArg("acc_bbp")
#                     # No correction file
#                     obs_module.addArg("")
#                     self.workflow.append(obs_module)
#                     # Now, we generate basic plots, such as
#                     # rotd50, and seismogram overlay comparisons
#                     gen_plots_module = Module()
#                     gen_plots_module.setName("GenPlots")
#                     gen_plots_module.addStageFile(self.stations)
#                     gen_plots_module.addArg(os.path.basename(self.stations))
#                     gen_plots_module.addArg(obs_dir)
#                     gen_plots_module.addArg('acc')
#                     gen_plots_module.addArg(comp_label)
#                     self.workflow.append(gen_plots_module)

#                     while True:
#                         if self.opt_obj is not None:
#                             gof_opt = self.opt_obj.get_next_option()
#                         else:
#                             gof_opt = raw_input("Choose a Goodness of Fit (GOF) "
#                                                 "Module: \n(1) GP\n(2) SDSU\n"
#                                                 "(3) Both\n? ")

#                         if gof_opt == "1" or gof_opt == "3":
#                             gof_module = Module()
#                             gof_module.setName("GPGof")
#                             gof_module.addStageFile(self.stations)
#                             gof_module.addArg(os.path.basename(self.stations))
#                             gof_module.addArg(mag)
#                             gof_module.addArg(comp_label)
#                             gof_module.addKeywordArg("single_component", False)
#                             self.workflow.append(gof_module)
#                             break
#                         if gof_opt == "2" or gof_opt == "3":
#                             gof_module = Module()
#                             gof_module.setName("SDSUMOGoF")
#                             gof_module.addStageFile(self.stations)
#                             gof_module.addArg(os.path.basename(self.stations))
#                             gof_weights = self.do_gof_metrics()
#                             gof_module.addArg(gof_weights)
#                             MOGof_Plot_Map = True
#                             gof_module.addArg(MOGof_Plot_Map)
#                             gof_module.addArg(obs_dir)
#                             if data_num != -1:
#                                 gof_module.addArg("V")
#                             else:
#                                 gof_module.addArg("A")
#                             gof_module.addArg(mag)
#                             gof_module.addArg(comp_label)
#                             self.workflow.append(gof_module)
#                             break

#                         # Invalid option!
#                         print " (GOF Module):", gof_opt
#                         if self.opt_obj is not None:
#                             sys.exit(1)

#                     # From outer loop
#                     break
#                 elif gof.lower() == 'n':
#                     break
#                 else:
#                     print "Invalid choice (GOF Module):", gof_opt
#                     if self.opt_obj is not None:
#                         sys.exit(1)

    def do_gof_metrics(self):
        """
        This function asks the user which specific metrics to calculate
        """

        gof_weights = dict()
        if self.opt_obj is not None:
            gof_metrics = self.opt_obj.get_next_option()
        else:
            print("=" * 80)
            print()
            print("The SDSU MO-GOF module includes a number of metrics"
                  " to compare recorded and calculates seismograms.")
            print()
            gof_metrics = raw_input("Do you want to calculate "
                                    "all MO-GOF metrics (y/n)? ")
        if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
            #  Weighting on PGA
            gof_weights["pga"] = 1.0
            #  Weighting on PGV
            gof_weights["pgv"] = 1.0
            #  Weighting on PGD
            gof_weights["pgd"] = 1.0
            #  Weighting on PSA
            gof_weights["psa"] = 1.0
            #  Weighting on Spectral Fit
            gof_weights["spectral_Fit"] = 1.0
            #  Weighting on Cumulative Energy Fit
            gof_weights["cumulative_energy_fit"] = 1.0
            #  Weighting on Inelastic/Elastic Fit (16)
            gof_weights["inelastic_elastic_fit"] = 1.0
            #  Weighting on Spec Acc (16)
            gof_weights["sepctral_acc"] = 1.0
            #  Weighting on Spec Dur (16)
            gof_weights["spec_duration"] = 1.0
            #  Weighting on Data Energy Release Duration (5%-75%)
            gof_weights["data_energy_release_duration"] = 1.0
            #  Weighting on Cross-Correlation
            gof_weights["cross_correlation"] = 1.0
            #  Weighting on Fourier Spectrum
            gof_weights["fourier_spectrum"] = 1.0
        else:
            #  Weighting on PGA
            gof_weights["pga"] = 0.0
            #  Weighting on PGV
            gof_weights["pgv"] = 0.0
            #  Weighting on PGD
            gof_weights["pgd"] = 0.0
            #  Weighting on PSA
            gof_weights["psa"] = 0.0
            #  Weighting on Spectral Fit
            gof_weights["spectral_Fit"] = 0.0
            #  Weighting on Cumulative Energy Fit
            gof_weights["cumulative_energy_fit"] = 0.0
            #  Weighting on Inelastic/Elastic Fit (16)
            gof_weights["inelastic_elastic_fit"] = 0.0
            #  Weighting on Spec Acc (16)
            gof_weights["sepctral_acc"] = 0.0
            #  Weighting on Spec Dur (16)
            gof_weights["spec_duration"] = 0.0
            #  Weighting on Data Energy Release Duration (5%-75%)
            gof_weights["data_energy_release_duration"] = 0.0
            #  Weighting on Cross-Correlation
            gof_weights["cross_correlation"] = 0.0
            #  Weighting on Fourier Spectrum
            gof_weights["fourier_spectrum"] = 0.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate Peak values "
                                        "- PGA,PGV,PGD and PSA (y/n)? ")
            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                #  Weighting on PGA
                gof_weights["pga"] = 1.0
                #  Weighting on PGV
                gof_weights["pgv"] = 1.0
                #  Weighting on PGD
                gof_weights["pgd"] = 1.0
                #  Weighting on PSA
                gof_weights["psa"] = 1.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate "
                                        "Spectral Fit (y/n)? ")

            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                # Weighting on Spectral Fit
                gof_weights["spectral_Fit"] = 1.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate "
                                        "Cumulative Energy Fit and "
                                        "Data Energy Release Duration (y/n)? ")

            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                #  Weighting on Cumulative Energy Fit
                gof_weights["cumulative_energy_fit"] = 1.0
                #  Weighting on Data Energy Release Duration (5%-75%)
                gof_weights["data_energy_release_duration"] = 1.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate "
                                        "Inelastic/Elastic Fit (y/n)? ")

            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                # Weighting on Inelastic/Elastic Fit (16)
                gof_weights["inelastic_elastic_fit"] = 1.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate "
                                        "Spectral Acceleration (y/n)? ")

            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                # Weighting on Spec Acc (16)
                gof_weights["sepctral_acc"] = 1.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate "
                                        "Spectral Duration (y/n)? ")

            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                # Weighting on Spec Dur (16)
                gof_weights["spec_duration"] = 1.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate "
                                        "Cross-Correlation (y/n)? ")

            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                # Weighting on Cross-Correlation
                gof_weights["cross_correlation"] = 1.0

            if self.opt_obj is not None:
                gof_metrics = self.opt_obj.get_next_option()
            else:
                gof_metrics = raw_input("Do you want to calculate "
                                        "Fourier Spectrum Fit (y/n)? ")

            if gof_metrics.lower() == 'y' or gof_metrics.lower() == 'yes':
                # Weighting on Fourier Spectrum
                gof_weights["fourier_spectrum"] = 1.0

        return gof_weights

    def get_input_file(self, description, extension):
        """
        This function asks the user to select a file from a list, or
        provide a path to a file of a specific extension.
        """

        # Loop until we get an answer
        while True:
            if self.opt_obj is not None:
                stat_opt = self.opt_obj.get_next_option()
            else:
                stat_opt = raw_input("Do you want to\n"
                                     "   (1) select a %s in %s\n" %
                                     (description,
                                      self.install.A_USER_DATA_DIR) +
                                     "       OR\n" +
                                     "   (2) enter the path of a %s file\n? " %
                                     (description))

            if stat_opt == "1":
                entries = os.listdir(self.install.A_USER_DATA_DIR)
                candidate_list = []
                for entry in entries:
                    if entry.endswith(extension):
                        candidate_list.append(entry)
                # Sort list of files alphabetically
                candidate_list.sort()
                # Create second list with basenames of the files
                file_list = []
                for entry in candidate_list:
                    file_list.append(os.path.basename(entry))
                if len(candidate_list) == 0:
                    print("*" * 80)
                    print("Couldn't find any %s files in the run directory" %
                          (description))
                    print("Aborting...")
                    print("*" * 80)
                    sys.exit(-1)

                if self.opt_obj is not None:
                    op_num = self.opt_obj.get_next_option()
                    # Check if user selected the file name
                    if op_num in file_list:
                        op_num = file_list.index(op_num) + 1
                    else:
                        try:
                            op_num = int(op_num)
                        except ValueError:
                            print("Must select integer from 1 to %d!" %
                                  len(candidate_list))
                            sys.exit(1)
                    if op_num < 1 or op_num > len(candidate_list):
                        print("Must select integer from 1 to %d!" %
                              len(candidate_list))
                        sys.exit(1)
                    print("Selecting file %s." %
                          candidate_list[int(op_num) - 1])
                    return os.path.join(self.install.A_USER_DATA_DIR,
                                        candidate_list[int(op_num) - 1])

                print("Here are the %s files in the run directory." %
                      (description))
                print("Please select one: ")
                choose_string = ""
                for i in range(0, len(candidate_list)):
                    choose_string = ("%s\n(%d) %s" %
                                     (choose_string, (i + 1),
                                      os.path.basename(candidate_list[i])))
                while True:
                    choose_string = "%s\n? " % choose_string
                    try:
                        choice_str = raw_input(choose_string)
                        # Check if user typed a filename
                        if choice_str in file_list:
                            return os.path.join(self.install.A_USER_DATA_DIR,
                                                candidate_list[file_list.index(choice_str)])
                        choice = int(choice_str)
                        if choice >= 1 and choice <= len(candidate_list):
                            return os.path.join(self.install.A_USER_DATA_DIR,
                                                candidate_list[choice - 1])
                        else:
                            print("You must enter an integer from 1 to %d." %
                                  len(candidate_list))
                    except TypeError:
                        print("You must enter a valid integer from 1 to %d." %
                              len(candidate_list))

            elif stat_opt == "2":
                while True:
                    if self.opt_obj is not None:
                        choice_str = self.opt_obj.get_next_option()
                    else:
                        choice_str = raw_input("Enter path and "
                                               "filename of %s: " %
                                               (description))

                    if ((os.path.exists(choice_str) and
                         (choice_str.find(extension) >= 0))):
                        break
                    else:
                        print("File "
                              "%s not found or invalid %s, please re-enter" %
                              (choice_str, description))
                return choice_str
            else:
                print("You must enter an integer from 1 to 2.")

    def get_input_directory(self, description):
        """
        This function asks the user to specify an input directory
        """
        # Loop until we get an answer
        while True:
            if self.opt_obj is not None:
                choice_str = self.opt_obj.get_next_option()
            else:
                choice_str = raw_input('Enter path for %s: ' %
                                       (description))

            if os.path.exists(choice_str):
                break
            else:
                print("Directory %s not found or invalid, please re-enter" %
                      (choice_str))
                if self.opt_obj is not None:
                    sys.exit(1)
        return choice_str

    def select_lf_seismograms(self):
        """
        This function asks the user to select LF seismograms
        """
        if self.validation:
            seis_dir = self.val_obj.get_input("GP", 'LF')
            if seis_dir is None:
                lf_seismograms = self.get_input_directory("LF precomputed seismograms")
            else:
                while True:
                    if self.opt_obj is not None:
                        user_seismograms = self.opt_obj.get_next_option()
                    else:
                        print("=" * 80)
                        print()
                        print("The validation packages includes a default"
                              " set of LF seismograms for this event.")
                        print()
                        user_seismograms = raw_input("Would you like to use "
                                                     "the LF seismograms "
                                                     "in %s (y/n)? " %
                                                     seis_dir)
                    if (user_seismograms.lower() == 'y' or
                        user_seismograms.lower() == 'yes'):
                        lf_seismograms = seis_dir
                        break
                    elif (user_seismograms.lower() == 'n' or
                          user_seismograms.lower() == 'no'):
                        lf_seismograms = self.get_input_directory("LF "
                                                                  "precomputed "
                                                                  "seismograms")
                        break
                    else:
                        print("Invalid choise for user seismograms: %s" %
                              (user_seismograms))
                        if self.opt_obj is not None:
                            sys.exit(1)
        else:
            lf_seismograms = self.get_input_directory("LF precomputed seismograms")

        # All done!
        return lf_seismograms

    def select_velocity_model(self):
        """
        This function prompts the user to select a velocity model
        """
        models = velocity_models.get_all_names()
        if len(models) == 0:
            raise velocity_models.MissingVelocityModel("Velocity models are " +
                                                       "not available! Cannot" +
                                                       " proceed!")
        # Create list of options
        choose_string = ("\nThe Broadband Platform provides the following "
                         "velocity models, which also include several "
                         "method-specific and region-specific parameters.\n\n"
                         "Please select a velocity model "
                         "(either number or name is ok):\n")
        for i in range(0, len(models)):
            choose_string = "%s\n(%d) %s" % (choose_string,
                                             (i + 1),
                                             models[i])
        choose_string = "%s\n? " % choose_string

        # Handle option file
        if self.opt_obj is not None:
            option = self.opt_obj.get_next_option()
            # Check if it matches one of the velocity model names
            if option in models:
                # Match, option is a valid velocity model, just return it
                return option
            # Now, check if it is a number
            try:
                option = int(option)
            except ValueError:
                raise ValueError("Invalid velocity model option!")
            if option >= 1 and option <= len(models):
                return models[option - 1]
            else:
                raise IndexError("Option outside range!")

        # Handle interactive mode
        while True:
            print("=" * 80)
            option = raw_input(choose_string)
            # Check if it matches one of the velocity model names
            if option in models:
                # Match, just return the name
                return option
            try:
                option = int(option)
                if option >= 1 and option <= len(models):
                    return models[option - 1]
                else:
                    print("You must enter an integer from 1 to %d." %
                          len(models))
            except ValueError:
                print("You must enter a valid integer from 1 to %d." %
                      len(models))

    def select_gmpe_model(self):
        """
        This function prompts the user to select a GMPE model
        """
        # Figure out which models are configured in BBP
        models = gmpe_config.GMPES.keys()
        models.sort()
        if len(models) == 0:
            raise RuntimeError("No GMPE models configured in BBP!")
        # Create list of options
        choose_string = ("\nPlease select a GMPE set to use "
                         "in the comparison "
                         "(number of name are ok):\n")
        for i in range(0, len(models)):
            choose_string = "%s\n(%d) %s" % (choose_string,
                                             (i + 1),
                                             models[i])
        choose_string = "%s\n? " % choose_string

        # If not in expert mode
        if not self.expert_mode:
            gmpe_opt = self.val_obj.get_gmpe_set()
            # Check if it matches GMPE name
            if gmpe_opt in models:
                # We're good!
                return gmpe_opt
            # We don't know this gmpe_set!
            raise ValueError("Invalid GMPE set: %s" %
                             (gmpe_opt))

        # Handle option file
        if self.opt_obj is not None:
            gmpe_opt = self.opt_obj.get_next_option()
            # Check if it matches GMPE name
            if gmpe_opt in models:
                # Match, we are good!
                return gmpe_opt
            # Now, check if it is a number
            try:
                gmpe_opt = int(gmpe_opt)
            except ValueError:
                raise ValueError("Invalid GMPE model option!")
            if gmpe_opt >= 1 and gmpe_opt <= len(models):
                return models[gmpe_opt - 1]
            else:
                raise IndexError("Option outside range!")

        # Handle interactive mode
        while True:
            print("=" * 80)
            gmpe_opt = raw_input(choose_string)
            # Check if it matches one of the GMPE model names
            if gmpe_opt in models:
                # Match, just return the name
                return gmpe_opt
            try:
                gmpe_opt = int(gmpe_opt)
                if gmpe_opt >= 1 and gmpe_opt <= len(models):
                    return models[gmpe_opt - 1]
                else:
                    print("You must enter an integer from 1 to %d." %
                          len(models))
            except ValueError:
                print("You must enter a valid integer from 1 to %d." %
                      len(models))

    def do_rupture_generator(self):
        """
        This function asks the user to choose a rupture generator
        """
        if self.method == "EXSIM" or self.method == "CSM":
            # For EXSIM and CSM, the method requires a source file but
            # no extra module is needed
            self.select_source_file()
            return False

        while True:
            if not self.expert_mode:
                rup_gen = 'y'
            elif self.opt_obj is not None:
                rup_gen = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("When starting a simulation from a source"
                      " description (SRC) file, the Broadband"
                      " Platform workflow should include a"
                      " rupture generator. Answer 'yes' here"
                      " unless providing a complex Standard"
                      " Rupture Format (SRF) file.")
                print()
                rup_gen = raw_input("Do you want to run the "
                                    "rupture generator (y/n)? ")
            if rup_gen.lower() == 'y' or rup_gen.lower() == 'yes':
                rupture_module = Module()
                if (self.method == "GP" or
                    self.method == "GPSeis" or
                    self.method == "SDSU" or
                    self.method == "SDSUSeis"):
                    # add GP rupture generator
                    rupture_module.setName("Genslip")
                    codebase = "GP"
                elif self.method == "SONG":
                    # add Song (RMG) rupture generator
                    rupture_module.setName("RMG")
                    codebase = "GP"
                elif self.method == "IRIKURA":
                    # add Irikura rupture generator
                    rupture_module.setName("Irikura")
                    codebase = "GP"
                elif self.method == "UCSB":
                    # add UCSB rupture generator
                    rupture_module.setName("UCrmg")
                    codebase = "UCSB"
                # Now go find necessary input files
                self.select_source_file()
                # Determine velocity model file
                self.vel_file = self.vmodel_obj.get_velocity_model(codebase)
                rupture_module.addStageFile(self.vel_file)
                rupture_module.addArg(os.path.basename(self.vel_file))
                rupture_module.addStageFile(self.src_file)
                rupture_module.addArg(os.path.basename(self.src_file))
                src_base = os.path.basename(self.src_file)
                self.srf_file = os.path.join(self.tmpdir,
                                             "%s.srf" %
                                             (src_base[0:src_base.rfind('.')]))
                rupture_module.addArg(os.path.basename(self.srf_file))
                rupture_module.addArg(self.vmodel_name)
                self.workflow.append(rupture_module)
                return True

            elif rup_gen.lower() == 'n' or rup_gen.lower() == 'no':

                if self.method == "GPSeis" or self.method == "SDSUSeis":
                    # These methods do not require a rupture generator and do
                    # not need a source_file (for SDSUSeis, one should be
                    # configured in SDSU_SRC and will be picked up later in
                    # the run_sdsu_method function).
                    return False

                if not self.validation:
                    # Then we need a srf file
                    self.srf_file = self.get_input_file("SRF", ".srf")
                    self.src_file = ""
                return False
            else:
                print(" Invalid answer: %s" % (rup_gen))
                if self.opt_obj is not None:
                    sys.exit(1)

    def do_scenario(self):
        """
        This function creates a scenario simulation workflow
        """
        # Run in scenario simulation mode
        self.validation = False

        # Get velocity model
        self.vmodel_name = self.select_velocity_model()
        self.vmodel_obj = velocity_models.get_velocity_model_by_name(self.vmodel_name)

        # Select method
        if self.expert_mode:
            self.method = self.select_simulation_method_expert_mode("scenario")
        else:
            self.method = self.select_simulation_method("scenario")

        # Check for the needed velocity model(s)
        self.check_velocity_models()

        # Check if we need to run the rupture generator
        gen_srf = self.do_rupture_generator()

        # Now pick the station file
        self.stations = self.get_input_file("BBP station list",
                                            ".stl")

        # Build the workflow
        self.make_choices(gen_srf)

        # run nonlinear site response analysis
        self.do_nonlinear_siteresponse()

        # Don't do GOF for forward simulations FS: 5-Mar-2013
        # self.do_gof()
        self.do_html_generation()

    def do_validation(self):
        """
        This function creates a validation workflow
        """
        # Run in validation simulation mode
        self.validation = True

        # Figure out how many events we have
        event_names = validation_cfg.VE_EVENTS.get_all_names()
        # Get them sorted
        event_names.sort()
        event_names_lc = [event.lower() for event in event_names]
        num_event_choices = validation_cfg.VE_EVENTS.get_num_events()

        # Check if we have events available for validation
        if num_event_choices == 0:
            print()
            print('*' * 80)
            print("No validation events available on the Broadband Platform")
            print("Make sure the BBP_VAL_DIR is set properly")
            print('*' * 80)
            print()
            sys.exit(1)

        while True:
            if self.opt_obj is not None:
                event = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                question = ("Please select a validation event from the list"
                            " below:\n\n")
                for i in range(num_event_choices):
                    # Let's figure out if the needed velocity model exists
                    event = event_names_lc[i]
                    val_obj = (validation_cfg.VE_EVENTS
                               .get_event_by_print_name(event))
                    # Find out what the velocity model is
                    vmodel = val_obj.get_velocity_model()
                    if (velocity_models.
                        get_velocity_model_by_name(vmodel) is None):
                        # Let user knows it is missing
                        suffix = ' --> velocity model %s is missing!' % (vmodel)
                    else:
                        suffix = ''
                    question = "%s(%d) %s%s\n" % (question,
                                                  i + 1,
                                                  event_names[i],
                                                  suffix)

                event = raw_input("%s? " % question)
            if event.lower() in event_names_lc:
                # User specified an event by its name
                self.val_obj = validation_cfg.VE_EVENTS.get_event_by_print_name(event)
                break
            try:
                choice = int(event)
            except ValueError:
                print("You must enter an integer or an event name!")
                if self.opt_obj is not None:
                    # Exit if processing an option file
                    sys.exit(1)
                continue
            try:
                if choice >= 1 and choice <= num_event_choices:
                    self.val_obj = validation_cfg.VE_EVENTS.get_event_by_print_name(event_names[choice-1])
                    break
                else:
                    print("You must enter an integer from 1 to %d." %
                          (num_event_choices))
                    if self.opt_obj is not None:
                        # Exit if processing an option file
                        sys.exit(1)
            except TypeError:
                print("Invalid choice: %s" % (event))
                if self.opt_obj is not None:
                    # Exit if processing an option file
                    sys.exit(1)

        # Set velocity model
        self.vmodel_name = self.val_obj.get_velocity_model()
        validation_event = self.val_obj.get_print_name()

        # Make sure velocity model exists
        if velocity_models.get_velocity_model_by_name(self.vmodel_name) is None:
            raise velocity_models.MissingVelocityModel("Velocity model %s " %
                                                       (self.vmodel_name) +
                                                       "needed by %s " %
                                                       (validation_event) +
                                                       "cannot be found!")
        # Good, it does
        self.vmodel_obj = velocity_models.get_velocity_model_by_name(self.vmodel_name)

        # Select method
        if self.expert_mode:
            self.method = self.select_simulation_method_expert_mode("validation")
        else:
            self.method = self.select_simulation_method("validation")

        # Check for the needed velocity model(s)
        self.check_velocity_models()

        # Ask user if we should run the rupture generator
        gen_srf = self.do_rupture_generator()

        # Select what stations to use for the validation
        while True:
            if not self.expert_mode:
                # In regular mode, we always run all stations!
                stat_opt = '1'
            elif self.opt_obj is not None:
                stat_opt = self.opt_obj.get_next_option()
            else:
                print("=" * 80)
                print()
                print("Station Selection")
                print("=================")
                stat_opt = raw_input("Would you like to:\n"
                                     "   (1) generate seismograms for all "
                                     "stations in the validation package\n"
                                     "       OR\n"
                                     "   (2) provide a custom list with "
                                     "a subset of the stations\n? ")
            if stat_opt == "1":
                stations = None
                if self.method == "GPSeis" or self.method == "SDSUSeis":
                    stations = self.val_obj.get_input("GP", "seis_stations")
                if stations is None:
                    stations = self.val_obj.get_input("GP", "stations")
                if stations is None:
                    raise ConfigurationError("Missing stations parameter "
                                             "for the %s validation!" %
                                             (self.vmodel_name))
                self.stations = stations
                break
            elif stat_opt == "2":
                self.stations = self.get_input_file("BBP station list",
                                                    ".stl")
                break
            else:
                print("Invalid choice (Station List): %s" % (stat_opt))
                if self.opt_obj is not None:
                    sys.exit(1)

        if self.opt_obj is None:
            # Print station list file we are using
            print('=' * 80)
            print("STL file: %s" % (self.stations))

        # Ask user what method to run
        self.make_choices(gen_srf)

        # Should we do any gmpe plot?
        self.do_val_gmpe()
        # Check if user wants GoF plots
        self.do_gof(gen_srf)
        # Check if user wants to run validations
        self.do_calculate_validation_parameters()
        # All done, create html index file
        self.do_html_generation()

    def do_html_generation(self):
        """
        This function adds the html generator to the workflow
        """
        # Add optional html index module
        html_module = Module()
        html_module.setName("GenHTML")
        html_module.addStageFile(self.stations)
        html_module.addArg(os.path.basename(self.stations))
        if self.src_file is not None and self.src_file != "":
            html_module.addStageFile(self.src_file)
            html_module.addArg(os.path.basename(self.src_file))
        else:
            html_module.addArg(self.src_file)
        html_module.addArg(self.vmodel_name)
        if self.val_obj is not None:
            html_module.addArg(self.val_obj.get_validation_name())
        else:
            html_module.addArg(None)
        html_module.addArg(self.method)
        self.workflow.append(html_module)

    def do_nonlinear_siteresponse(self):
        # ask if nonlinear site response analysis needs to run
        while True:
            try:
                val_choice = raw_input("Do you want to perform a "
                                       "nonlinear site response analysis (y/n)? ")
                if (val_choice.lower() == 'y' or val_choice.lower() == 'n' or
                    val_choice.lower() == 'yes' or val_choice.lower() == 'no'):
                    break
                else:
                    print("Invalid input.")
            except KeyboardInterrupt:
                print("\nAborting...")
                sys.exit(1)

        # Create site response workflow
        try:
            if val_choice.lower() == 'y' or val_choice.lower() == 'yes':
                nonlinearSR_module = Module()
                nonlinearSR_module.setName("uwsr")
                nonlinearSR_module.addArg(os.path.basename(self.stations))
                nonlinearSR_module.addStageFile(self.stations)
                siteLayering = self.get_input_file("Local Site Layering",
                                            ".loc")
                nonlinearSR_module.addArg(siteLayering)
                self.workflow.append(nonlinearSR_module)

            else:
                return
        except KeyboardInterrupt:
            print("\nAborting...")
            sys.exit(1)
