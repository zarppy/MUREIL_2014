#
#
# Copyright (C) University of Melbourne 2012
#
#
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
#
"""Test of TxMultiGenerator

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_txmultigenerator.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy

from tools import mureilexception, testutilities
from tools import mureilbuilder

from generator import txmultigeneratormultisite

sea = testutilities.make_sane_equality_array

class TestUpdateStateNewPeriod(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_1(self):
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
    
        tmg = txmultigeneratormultisite.TxMultiGeneratorMultiSite()

        tmg.config['startup_data_name'] = ''
        tmg.config['params_to_site_data_name'] = ''
        data_types = tmg.get_data_types()
        exp_data_types = []
        self.assertTrue((data_types == exp_data_types))

        tmg.config['startup_data_name'] = 'gen_startup'
        data_types = tmg.get_data_types()
        exp_data_types = ['gen_startup']
        self.assertTrue((data_types == exp_data_types))

        tmg.config['params_to_site_data_name'] = 'gen_site_map'
        data_types = tmg.get_data_types()
        exp_data_types = ['gen_startup', 'gen_site_map']
        self.assertTrue((data_types == exp_data_types))
        
        tmg.run_periods = [2010, 2020, 2030]
        
        # Now try out the startup & params to site
        
        params_to_site = numpy.array([33, 22, 44, 55, 11], dtype=int)
        startup_data = numpy.array([[22, 100, 1990, 2020],
                                   [22, 200, 2000, 2030],
                                   [11, 300, 2000, 2010],
                                   [44, 400, 1990, 2010],
                                   [44, 1000, 1990, 2020]], dtype=float)
                        
        data = {}
        data['gen_site_map'] = params_to_site
        data['gen_startup'] = startup_data
        
        tmg.set_data(data)
        self.assertTrue((tmg.params_to_site == params_to_site).all())
        self.assertEqual(tmg.get_param_count(), len(params_to_site))
        self.assertTrue((tmg.extra_periods == [1990, 2000]))

        startup_state = tmg.get_startup_state_handle()

        exp_state = {}
        exp_state['curr_period'] = None
        exp_state['capacity'] = {}
        exp_state['history'] = {}
        cap_list = exp_state['capacity']
        cap_list[22] = [(100, 1990, 2020), (200, 2000, 2030)]
        cap_list[11] = [(300, 2000, 2010)]
        cap_list[44] = [(400, 1990, 2010), (1000, 1990, 2020)]

        self.assertTrue((exp_state == startup_state))

        # Now set some more configs, and check that the expand_config works.
        tmg.config['size'] = {2000: 10, 2010: 20, 2030: 30}
        tmg.config['capital_cost'] = {2000: 5, 2010: 6, 2020: 7, 2030: 8}
        tmg.config['install_cost'] = 0
        tmg.config['decommissioning_cost'] = {2000: 0.1, 2010: 0.2}
        tmg.config['time_period_yrs'] = 10
        tmg.config['lifetime_yrs'] = {2000: 10, 2020: 30}
        tmg.config['timestep_hrs'] = 1.0
        tmg.expand_config([2000, 2010, 2020, 2030, 2040, 2050])
        
        exp_pc = {}
        exp_pc[1990] = {'size': 10, 
            'startup_data_name': 'gen_startup',
            'time_period_yrs': 10,
            'lifetime_yrs': 10,
            'install_cost': 0,
            'timestep_hrs': 1.0,
            'capital_cost': 5,
            'decommissioning_cost': 0.1,
            'params_to_site_data_name': 'gen_site_map'}
        exp_pc[2000] = {'size': 10, 
            'startup_data_name': 'gen_startup',
            'time_period_yrs': 10,
            'timestep_hrs': 1.0,
            'install_cost': 0,
            'lifetime_yrs': 10,
            'capital_cost': 5,
            'decommissioning_cost': 0.1,
            'params_to_site_data_name': 'gen_site_map'}
        exp_pc[2010] = {'size': 20, 
            'startup_data_name': 'gen_startup',
            'time_period_yrs': 10,
            'timestep_hrs': 1.0,
            'install_cost': 0,
            'lifetime_yrs': 10,
            'capital_cost': 6,
            'decommissioning_cost': 0.2,
            'params_to_site_data_name': 'gen_site_map'}
        exp_pc[2020] = {'size': 20, 
            'startup_data_name': 'gen_startup',
            'time_period_yrs': 10,
            'lifetime_yrs': 30,
            'install_cost': 0,
            'timestep_hrs': 1.0,
            'capital_cost': 7,
            'decommissioning_cost': 0.2,
            'params_to_site_data_name': 'gen_site_map'}
        exp_pc[2030] = {'size': 30, 
            'startup_data_name': 'gen_startup',
            'time_period_yrs': 10,
            'lifetime_yrs': 30,
            'install_cost': 0,
            'capital_cost': 8,
            'timestep_hrs': 1.0,
            'decommissioning_cost': 0.2,
            'params_to_site_data_name': 'gen_site_map'}
        exp_pc[2040] = {'size': 30, 
            'startup_data_name': 'gen_startup',
            'time_period_yrs': 10,
            'lifetime_yrs': 30,
            'timestep_hrs': 1.0,
            'capital_cost': 8,
            'install_cost': 0,
            'decommissioning_cost': 0.2,
            'params_to_site_data_name': 'gen_site_map'}
        exp_pc[2050] = {'size': 30, 
            'startup_data_name': 'gen_startup',
            'time_period_yrs': 10,
            'lifetime_yrs': 30,
            'capital_cost': 8,
            'install_cost': 0,
            'timestep_hrs': 1.0,
            'decommissioning_cost': 0.2,
            'params_to_site_data_name': 'gen_site_map'}
        
        self.assertTrue((tmg.period_configs == exp_pc))
        
        # Now update the state from a list
        state_handle = tmg.get_startup_state_handle()
        new_cap = [(33, 1000, 2040), (44, 2000, 2010), (22, 1000, 2020)]
        tmg.update_state_new_period_list(state_handle, 2010, new_cap)

        exp_state_handle = {}
        exp_state_handle['curr_period'] = 2010
        exp_state_handle['capacity'] = cap_list = {}
        exp_state_handle['history'] = hist_list = {}
        cap_list[22] = [(100, 1990, 2020), (200, 2000, 2030), (1000, 2010, 2020)]
        cap_list[11] = [(300, 2000, 2010)]
        cap_list[44] = [(400, 1990, 2010), (1000, 1990, 2020), (2000, 2010, 2010)]
        cap_list[33] = [(1000, 2010, 2040)]

        self.assertTrue((exp_state_handle == state_handle))
        
        # and get the list of sites
        sites = tmg.get_site_indices(state_handle)
        exp_sites = [11, 22, 33, 44]
        self.assertTrue((exp_sites == sites))
        
        # and the capacity and new_capacity costs
        capacity = tmg.get_capacity(state_handle)
        exp_capacity = [300.0, 1300.0, 1000.0, 3400.0]
        self.assertTrue((exp_capacity == capacity))

        total_new_cap_cost, new_capacity_costs = (
            tmg.calculate_new_capacity_cost(state_handle))
            
        exp_total_cost = 24000
        exp_new_capacity_cost = [(22, 1000, 6000),
            (33, 1000, 6000), (44, 2000, 12000)]
        self.assertEqual(exp_total_cost, total_new_cap_cost)
        self.assertTrue((exp_new_capacity_cost, new_capacity_costs))
        
        # and decommission
        total_decomm_cost, decomm = (
            tmg.calculate_update_decommission(state_handle))

        exp_total_cost = 540
        exp_decomm = [(11, 300, 60), (44, 2400, 480)]
        self.assertEqual(exp_total_cost, total_decomm_cost)
        self.assertTrue((exp_decomm, decomm))
        
        exp_state_handle = {}
        exp_state_handle['curr_period'] = 2010
        exp_state_handle['capacity'] = cap_list = {}
        exp_state_handle['history'] = hist_list = {}

        cap_list[22] = [(100, 1990, 2020), (200, 2000, 2030), (1000, 2010, 2020)]
        cap_list[44] = [(1000, 1990, 2020)]
        cap_list[33] = [(1000, 2010, 2040)]
        hist_list[11] = [(300, 2000, 2010)]
        hist_list[44] = [(400, 1990, 2010), (2000, 2010, 2010)]
        
        self.assertTrue((exp_state_handle == state_handle))
        
        # Add some more capacity in 2020, using the params this time
        tmg.update_state_new_period_params(state_handle, 2020, numpy.array(
            [0, 220, 0, 550, 110]))
            
        exp_state_handle = {}
        exp_state_handle['curr_period'] = 2020
        exp_state_handle['capacity'] = cap_list = {}
        exp_state_handle['history'] = hist_list

        cap_list[11] = [(2200, 2020, 2040)]
        cap_list[22] = [(100, 1990, 2020), (200, 2000, 2030), (1000, 2010, 2020),
            (4400, 2020, 2040)]
        cap_list[44] = [(1000, 1990, 2020)]
        cap_list[33] = [(1000, 2010, 2040)]
        cap_list[55] = [(11000, 2020, 2040)]

        #pp.pprint(exp_state_handle)
        #pp.pprint(state_handle)
        self.assertTrue((exp_state_handle == state_handle))

        # and check that get_startup_state still returns a clean one
        startup_state = tmg.get_startup_state_handle()

        exp_state = {}
        exp_state['curr_period'] = None
        exp_state['capacity'] = {}
        exp_state['history'] = {}
        cap_list = exp_state['capacity']
        hist_list = exp_state['history']

        cap_list[22] = [(100, 1990, 2020), (200, 2000, 2030)]
        cap_list[11] = [(300, 2000, 2010)]
        cap_list[44] = [(400, 1990, 2010), (1000, 1990, 2020)]
        
        self.assertTrue((exp_state == startup_state))


    def test_set_config(self):
        config = {}
        config['size'] = {2000: 10, 2010: 20, 2030: 30}
        config['capital_cost'] = {2000: 5, 2010: 6, 2020: 7, 2030: 8}
        config['decommissioning_cost'] = {2000: 0.1, 2010: 0.2}
        config['time_period_yrs'] = 10
        config['lifetime_yrs'] = {2000: 10, 2020: 30}
        config['model'] = 'txmultigenerator'
        config['section'] = 'Generator'
        config['timestep_hrs'] = 1.0

        tmg = txmultigeneratormultisite.TxMultiGeneratorMultiSite()
        tmg.set_config(config, run_periods=[2000, 2010, 2020])

        exp_pc = {}
        exp_pc[2000] = {'size': 10.0, 
            'time_period_yrs': 10,
            'params_to_site_data_name': '',
            'startup_data_name': '',
            'lifetime_yrs': 10,
            'variable_cost_mult': 1.0,
            'time_scale_up_mult': 1.0,
            'carbon_price_m': 0.0,
            'vom': 0.0,
            'model': 'txmultigenerator',
            'timestep_hrs': 1.0,
            'section': 'Generator',
            'startup_data_string': None,
            'install_cost': 0,
            'params_to_site_data_string': [],
            'start_min_param': 1e20,
            'start_max_param': 1e20,
            'capital_cost': 5.0,
            'decommissioning_cost': 0.1}
        exp_pc[2010] = {'size': 20.0, 
            'time_period_yrs': 10,
            'variable_cost_mult': 1.0,
            'timestep_hrs': 1.0,
            'params_to_site_data_name': '',
            'startup_data_name': '',
            'time_scale_up_mult': 1.0,
            'carbon_price_m': 0.0,
            'vom': 0.0,
            'install_cost': 0,
            'startup_data_string': None,
            'params_to_site_data_string': [],
            'start_min_param': 1e20,
            'start_max_param': 1e20,
            'lifetime_yrs': 10,
            'model': 'txmultigenerator',
            'section': 'Generator',
            'capital_cost': 6.0,
            'decommissioning_cost': 0.2}
        exp_pc[2020] = {'size': 20.0, 
            'time_period_yrs': 10,
            'variable_cost_mult': 1.0,
            'vom': 0.0,
            'install_cost': 0,
            'time_scale_up_mult': 1.0,
            'timestep_hrs': 1.0,
            'params_to_site_data_name': '',
            'startup_data_name': '',
            'startup_data_string': None,
            'params_to_site_data_string': [],
            'start_min_param': 1e20,
            'start_max_param': 1e20,
            'carbon_price_m': 0.0,
            'model': 'txmultigenerator',
            'section': 'Generator',
            'lifetime_yrs': 30,
            'capital_cost': 7.0,
            'decommissioning_cost': 0.2}

#        import pprint
#        pp = pprint.PrettyPrinter(indent=4)
#        pp.pprint(tmg.period_configs)
#        pp.pprint(exp_pc)

#        for (period, conf) in exp_pc.iteritems():
#            for (key, value) in conf.iteritems():
#                print key
#                print (exp_pc[period][key] == tmg.period_configs[period][key])

        self.assertTrue((tmg.period_configs == exp_pc))


    def test_set_config_check_lifetime_dict(self):
        config = {}
        config['size'] = {2000: 10, 2010: 20, 2030: 30}
        config['capital_cost'] = {2000: 5, 2010: 6, 2020: 7, 2030: 8}
        config['decommissioning_cost'] = {2000: 0.1, 2010: 0.2}
        config['time_period_yrs'] = 10
        config['lifetime_yrs'] = {2000: 15, 2020: 30}
        config['model'] = 'txmultigenerator'
        config['section'] = 'Generator'
        config['variable_cost_mult'] = 1
        config['time_scale_up_mult'] = 1
        config['carbon_price_m'] = 100
        config['timestep_hrs'] = 1.0

        tmg = txmultigeneratormultisite.TxMultiGeneratorMultiSite()
        
        with self.assertRaises(mureilexception.ConfigException) as cm:
            tmg.set_config(config, run_periods=[2000, 2010, 2020, 2030, 2040, 2050])
               
        self.assertEqual(cm.exception.msg, 
            'In section Generator, lifetime_yrs = 15.0 which is required to be a multiple of time_period_yrs of 10.0')
            

    def test_set_config_check_lifetime_scalar(self):
        config = {}
        config['size'] = {2000: 10, 2010: 20, 2030: 30}
        config['capital_cost'] = {2000: 5, 2010: 6, 2020: 7, 2030: 8}
        config['decommissioning_cost'] = {2000: 0.1, 2010: 0.2}
        config['time_period_yrs'] = 10
        config['lifetime_yrs'] = 8
        config['model'] = 'txmultigenerator'
        config['section'] = 'Generator'
        config['variable_cost_mult'] = 1
        config['time_scale_up_mult'] = 1
        config['carbon_price_m'] = 100
        config['timestep_hrs'] = 1.0

        tmg = txmultigeneratormultisite.TxMultiGeneratorMultiSite()

        with self.assertRaises(mureilexception.ConfigException) as cm:
            tmg.set_config(config, run_periods=[2000, 2010, 2020, 2030, 2040, 2050])
               
        self.assertEqual(cm.exception.msg, 
            'In section Generator, lifetime_yrs = 8.0 which is required to be a multiple of time_period_yrs of 10.0')
            



if __name__ == '__main__':
    unittest.main()
    
