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
import thermal.slowresponsethermal_beta

class TestSlowResponseThermal(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.thermal = thermal.slowresponsethermal_beta.SlowResponseThermal()

    def tearDown(self):
        os.chdir(self.cwd)

    def do_csv_test(self, filename):
 
        test_file = "Beta_test3.csv"

        """
        beta_test1.csv : base test case where rem_demand exceeds max cap
        beta_test2.csv : alternate value of time_const_mins
        beta_test3.csv : alternate value of variabl_cost_mult
        beta_test4.csv : negative values of rem_demand
        beta_test5.csv : alternate value of time_const_hrs
        beta_test6.csv : max capacity is zero
        beta_test7.csv : alternate value of capex
        beta_test8.csv : alternate value of fuel_price_tonne
        beta_test9.csv : alternate value of carbon_price        
        beta_test10.csv : alternate value of c_intensity_ratio
        beta_test11.csv : alternate value of eta_max
        beta_test12.csv : alternate value of lwr_heat_value
         
        """

        test_file = filename
        config_arr = np.genfromtxt(test_file, delimiter = ',',  usecols = (0))
        config = {
            'capex': config_arr[0],
            'fuel_price_tonne': config_arr[1],
            'carbon_price': config_arr[2],
            'c_intensity_ratio': config_arr[3],
            'timestep_mins': config_arr[4],
            'variable_cost_mult': config_arr[5],
            'time_const_mins': config_arr[6],
            'eta_max': config_arr[7],
            'size': config_arr[8],
            'lwr_heat_val': config_arr[9],
            'type': 'BlackCoal'
        }

                      
        rem_demand = np.genfromtxt(test_file, delimiter = ',',  usecols = (1))        
        ts_demand = {'ts_demand': np.ones(len(rem_demand))*10000} # dummy demand   
        exp_ts = np.genfromtxt(test_file, delimiter = ',',  usecols = (2))
        exp_cost = config_arr[10]

        
        try:
            self.thermal.set_config(config)
            self.thermal.set_data(ts_demand)

            # param is multiplied by 100 to give capacity in MW.
            (out_cost, out_ts) = self.thermal.calculate_cost_and_output([config_arr[8]/100], rem_demand)
            out_cost = np.round(out_cost, 6)
            out_ts = np.round(out_ts, 6)
            print 'out_cost', out_cost
            print 'out_ts', out_ts
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which test_slowresponsethermal
        # expects) gets turned into a list, which is what unittest expects.

        self.assertListEqual(out_ts.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)


    def test_1(self):
        print "Beta_test1.csv"
        self.do_csv_test("beta_test1.csv")        

    def test_2(self):
        print "Beta_test2.csv"
        self.do_csv_test("beta_test2.csv")        

    def test_3(self):
        print "Beta_test3.csv"
        self.do_csv_test("beta_test3.csv")        

    def test_4(self):
        print "Beta_test4.csv"
        self.do_csv_test("beta_test4.csv")        

    def test_5(self):
        print "Beta_test5.csv"
        self.do_csv_test("beta_test5.csv")              

    def test_6(self):
        print "Beta_test6.csv"
        self.do_csv_test("beta_test6.csv")

    def test_7(self):
        print "Beta_test7.csv"
        self.do_csv_test("beta_test7.csv") 

    def test_8(self):
        print "Beta_test8.csv"
        self.do_csv_test("beta_test8.csv") 

    def test_9(self):
        print "Beta_test9.csv"
        self.do_csv_test("beta_test9.csv")

    def test_10(self):
        print "Beta_test10.csv"
        self.do_csv_test("beta_test10.csv")

    def test_11(self):
        print "Beta_test11.csv"
        self.do_csv_test("beta_test11.csv")

    def test_12(self):
        print "Beta_test12.csv"
        self.do_csv_test("beta_test12.csv")

class TestSlowResponseThermalFixed(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.thermal = thermal.slowresponsethermal_beta.SlowResponseThermalFixed()

    def tearDown(self):
        os.chdir(self.cwd)

    def do_csv_test(self, filename):
           
        test_file = filename
        config_arr = np.genfromtxt(test_file, delimiter = ',',  usecols = (0))
        config = {
            'capex': config_arr[0],
            'fuel_price_tonne': config_arr[1],
            'carbon_price': config_arr[2],
            'c_intensity_ratio': config_arr[3],
            'timestep_mins': config_arr[4],
            'variable_cost_mult': config_arr[5],
            'time_const_mins': config_arr[6],
            'eta_max': config_arr[7],
            'size': config_arr[8],
            'lwr_heat_val': config_arr[9],
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
        exp_cost = config_arr[10]

        #print 'rem_demand', rem_demand
        #print 'ts_demand', ts_demand
        #print 'exp_ts', exp_ts
        #print 'exp_cost', exp_cost
      
        try:
            self.thermal.set_config(config)
            self.thermal.set_data(ts_demand)

            (out_cost, out_ts) = self.thermal.calculate_cost_and_output(config['fixed_capacity']/100, rem_demand)
            out_cost = np.round(out_cost, 6)
            out_ts = np.round(out_ts, 6)
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
    
