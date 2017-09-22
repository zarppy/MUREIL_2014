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
"""Test of slowresponsethermal

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_slowresponsethermal.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy as np
import tools.mureilexception as mureilexception
import tools.mureilbuilder as mureilbuilder

from tools import testutilities

import thermal.slowresponsethermal

class TestSlowResponseThermal(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.thermal = thermal.slowresponsethermal.SlowResponseThermal()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_simple(self):
        """ config = {
            'capex': 3.0,
            'fuel_price_mwh': 10,
            'carbon_price': 5,
            'carbon_intensity': 1.0,
            'timestep_hrs': 1.0,
            'variable_cost_mult': 1.0,
            'ramp_time_mins': 240,
            'type': 'BlackCoal'
        }
        """
        
        test_file = "test1.csv"
        config_arr = np.genfromtxt(test_file, delimiter = ',',  usecols = (0))
        config = {
            'capex': config_arr[0],
            'fuel_price_mwh': config_arr[1],
            'carbon_price': config_arr[2],
            'carbon_intensity': config_arr[3],
            'timestep_hrs': config_arr[4],
            'variable_cost_mult': config_arr[5],
            'ramp_time_mins': config_arr[6],
            'type': 'BlackCoal'
        }
             
        
        # rem_demand = np.array([10, 20, 30, 40, 40, 40, 40, 30, 20, 10])  
        rem_demand = np.genfromtxt(test_file, delimiter = ',',  usecols = (1))
          
             
        #ts_demand1 = {'ts_demand': np.array([110, 120, 130, 140, 140, 140, 140, 130, 120, 110])}     
        ts_demand = {'ts_demand': np.ones(len(rem_demand))*10000} # dummy demand
        
        # for original no-code version, just output at full capacity all the time
        # will test here with capacity = 500MW
        #exp_ts = np.array([500, 500, 500, 500, 500, 500, 500, 500, 500, 500])
        
        exp_ts = np.genfromtxt(test_file, delimiter = ',',  usecols = (2))

        # exp_cost = (10 * 500 * (10 + 5)) * 1e-6 + (3 * 500)
        exp_cost = config_arr[9]

        print 'rem_demand', rem_demand
        print 'ts_demand', ts_demand
        print 'exp_ts', exp_ts
        print 'exp_cost', exp_cost

        
        
        try:
            self.thermal.set_config(config)
            self.thermal.set_data(ts_demand)
            # param is multiplied by 100 to give capacity in MW, so '5' is used here.
            (out_cost, out_ts) = self.thermal.calculate_cost_and_output([5], rem_demand)
            print 'out_cost', out_cost
            print 'out_ts', out_ts
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which test_slowresponsethermal
        # expects) gets turned into a list, which is what unittest expects.

        self.assertListEqual(out_ts.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
    

class TestSlowResponseThermalFixed(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.thermal = thermal.slowresponsethermal.SlowResponseThermalFixed()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_simple(self):
        """ config = {
            'capex': 3.0,
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
            'capex': config_arr[0],
            'fuel_price_mwh': config_arr[1],
            'carbon_price': config_arr[2],
            'carbon_intensity': config_arr[3],
            'timestep_hrs': config_arr[4],
            'variable_cost_mult': config_arr[5],
            'ramp_time_mins': config_arr[6],
            'type': 'BlackCoal',
            'fixed_capacity': 1200
        }
            

          
        #rem_demand = np.array([10, 20, 30, 40, 40, 40, 40, 30, 20, 10])
        rem_demand = np.genfromtxt(test_file, delimiter = ',',  usecols = (1))

        #ts_demand = {'ts_demand': np.array([110, 120, 130, 140, 140, 140, 140, 130, 120, 110])}
        ts_demand = {'ts_demand': np.ones(len(rem_demand))*10000} # dummy demand
            
        # for original no-code version, just output at full capacity all the time
        # will test here with capacity = 1200 MW
        #exp_ts = np.array([1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200])
        exp_ts = np.genfromtxt(test_file, delimiter = ',',  usecols = (2))
            
        #exp_cost = (10 * 1200 * (10 + 5)) * 1e-6 + (3 * 1200)
        exp_cost = config_arr[9]

        print 'rem_demand', rem_demand
        print 'ts_demand', ts_demand
        print 'exp_ts', exp_ts
        print 'exp_cost', exp_cost
      
        try:
            self.thermal.set_config(config)
            self.thermal.set_data(ts_demand)
            (out_cost, out_ts) = self.thermal.calculate_cost_and_output([], rem_demand)
            print 'out_cost', out_cost
            print 'out_ts', out_ts
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which basicpumpedhydro
        # expects) gets turned into a list, which is what unittest expects.

        self.assertListEqual(out_ts.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
    

if __name__ == '__main__':
    unittest.main()
    
