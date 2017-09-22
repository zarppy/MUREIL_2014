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
"""Test of txmultislowthermal

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_txmultislowthermal.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy as np
import tools.mureilexception as mureilexception
import tools.mureilbuilder as mureilbuilder

from tools import testutilities

import thermal.txmultislowthermal

class TestSlowResponseThermal(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.thermal = thermal.txmultislowthermal.TxMultiSlowOptimisableThermal()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_simple(self):
        """ config = {
            'capital_cost': 3.0,
            'fuel_price_mwh': 10,
            'carbon_price_m': 5e-6,
            'carbon_intensity': 1.0,
            'timestep_hrs': 1.0,
            'variable_cost_mult': 1.0,
            'ramp_time_mins': 240,
            'tech_type': 'coal',
            'detail_type': 'BlackCoal',
            'size': 100
        }
        """
        
        test_file = "test1.csv"
        config_arr = np.genfromtxt(test_file, delimiter = ',',  usecols = (0))
        config = {
            'capital_cost': config_arr[0],
            'fuel_price_mwh': config_arr[1],
            'carbon_price_m': config_arr[2] * 1e-6,
            'carbon_intensity': config_arr[3],
            'timestep_hrs': config_arr[4],
            'variable_cost_mult': config_arr[5],
            'ramp_time_mins': config_arr[6],
            'detail_type': 'BlackCoal',
            'tech_type': 'coal',
            'size': 100,
            'model': 'txmultislowthermal',
            'section': 'Thermal',
            'time_period_yrs': 10
        }
             
        supply_request = np.genfromtxt(test_file, delimiter = ',',  usecols = (1))
        
        exp_ts = np.genfromtxt(test_file, delimiter = ',',  usecols = (2))

        exp_cost = config_arr[9]

        print 'supply_request', supply_request
        print 'exp_ts', exp_ts
        print 'exp_cost', exp_cost
        
        run_periods = [2010]
        
        try:
            self.thermal.set_config(config, run_periods=run_periods)
            state_handle = self.thermal.get_startup_state_handle()
            (out_indices, out_cost, out_supply) = self.thermal.calculate_time_period_simple(
                state_handle, 2010, [5], supply_request)
            print 'out_indices', out_indices
            print 'out_cost', out_cost
            print 'out_supply', out_supply
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which test_slowresponsethermal
        # expects) gets turned into a list, which is what unittest expects.

        self.assertListEqual(out_supply.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
    

class TestSlowResponseThermalFixed(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.thermal = thermal.txmultislowthermal.TxMultiSlowOptimisableThermal()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_simple(self):
        """ config = {
            'capital_cost': 3.0,
            'fuel_price_mwh': 10,
            'carbon_price': 5,
            'carbon_intensity': 1.0,
            'timestep_hrs': 1.0,
            'variable_cost_mult': 1.0,
            'ramp_time_mins': 240,
            'type': 'BlackCoal',
            'fixed_capacity': 1200
        }
        """

        test_file = "test2.csv"
        config_arr = np.genfromtxt(test_file, delimiter = ',',  usecols = (0))
        config = {
            'capital_cost': config_arr[0],
            'fuel_price_mwh': config_arr[1],
            'carbon_price_m': config_arr[2] * 1e-6,
            'carbon_intensity': config_arr[3],
            'timestep_hrs': config_arr[4],
            'variable_cost_mult': config_arr[5],
            'ramp_time_mins': config_arr[6],
            'site_index': 54,
            'detail_type': 'BlackCoal',
            'tech_type': 'coal',
            'startup_data_string': '[[54, 1200, 2010, 2020]]',
            'model': 'txmultislowthermal',
            'section': 'Thermal',
            'time_period_yrs': 10
        }
            
        supply_request = np.genfromtxt(test_file, delimiter = ',',  usecols = (1))

        exp_ts = np.genfromtxt(test_file, delimiter = ',',  usecols = (2))
        exp_cost = config_arr[9]

        print 'supply_request', supply_request
        print 'exp_ts', exp_ts
        print 'exp_cost', exp_cost

        run_periods = [2010]
      
        try:
            self.thermal.set_config(config, run_periods=run_periods)
            state_handle = self.thermal.get_startup_state_handle()
            (out_indices, out_cost, out_supply) = self.thermal.calculate_time_period_simple(
                state_handle, 2010, [], supply_request)
            print 'out_indices', out_indices
            print 'out_cost', out_cost
            print 'out_supply', out_supply
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which basicpumpedhydro
        # expects) gets turned into a list, which is what unittest expects.

        self.assertListEqual(out_supply.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
    

if __name__ == '__main__':
    unittest.main()
    
