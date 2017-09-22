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
"""Test of basicpumpedhydro

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_basicpumpedhydro.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy as np

from tools import mureilexception, testutilities

import hydro.basicpumpedhydro

class TestBasicPumpedHydro(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.hydro = hydro.basicpumpedhydro.BasicPumpedHydro()

    def tearDown(self):
        os.chdir(self.cwd)


    def do_csv_test(self, filename):
        """ Several test cases have been compiled into separate .csv files
            These files include the input config (column 0 index 0 - 5),
            the input test rem_demand (column 1),
            the calculated output exp_ts (column 2)
            the calculated output exp_cost (column 0, index 6)   
            These test files represent the following conditions:
            test1.csv: rem_demand is positive (ie network requires power) and
                       less than gen capacity, continues until the dam
                       is empty
            test2.csv: rem_demand is positive (ie network requires power)and
                       exceeds the gen capacity, does not empty the dam
            test3.csv: suppy_need is negative (ie excess power for storage) and
                       less than gen capacity,continues until the dam
                       reaches capacity
            test4.csv: rem_demand is negative (ie excess power for storage) and
                       exceeds the gen capacity, does not exceed dam capacity
            test5.csv: randomly generated rem_demand, both positive and
                       negative values, some values exceed gen capacity,
                       does not either exceed dam capacity or empty dam
            test6.csv: alternate value of pumped_round_trip, note that this
                       can be set >1 without any error message
            test7.csv: randomly generated rem_demand initial cap and res are
                       set equal (ie the dam is full initially)            
            test8.csv: randomly generated rem_demand, generating capacity is
                       set to zero
            test9.csv: randomly generated rem_demand, res is set to zero
                       (ie the dam is empty initially)      
            test10.csv: randomly generated rem_demand, alternate value of capex.                                 

        """

        test_file = filename
        config_arr = np.genfromtxt(test_file, delimiter = ',',  usecols = (0))
        config = {
            'capex': config_arr[0],
            'max_gen': config_arr[1],
            'dam_capacity': config_arr[2],
            'starting_level': config_arr[3],
            'water_factor': config_arr[4],
            'pump_round_trip': config_arr[5],
            'section': 'test_basicpumpedhydro',
            'timestep_hrs': 1.0
        }
        
        rem_demand = np.genfromtxt(test_file, delimiter = ',',  usecols = (1))

        exp_ts = np.genfromtxt(test_file, delimiter = ',', usecols = (2))

        exp_cost = config_arr[6]
        
        try:
            self.hydro.set_config(config)
            (out_cost, out_ts) = self.hydro.calculate_cost_and_output([], rem_demand)
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which basicpumpedhydro
        # expects) gets turned into a list, which is what unittest expects.

        # Outputs are rounded to 10 decimal places to remove small floating
        # point errors
        out_cost = out_cost.round(10)
        out_ts = out_ts.round(10)

        self.assertListEqual(out_ts.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
    
    
    def test_1(self):
        self.do_csv_test("test1.csv")        
      
    def test_2(self):
        self.do_csv_test("test2.csv")        

    def test_3(self):
        self.do_csv_test("test3.csv")        

    def test_4(self):
        self.do_csv_test("test4.csv")        

    def test_5(self):
        self.do_csv_test("test5.csv")        

    def test_6(self):
        test_dir = os.path.dirname(os.path.realpath(__file__)) 
        cwd = os.getcwd()
        os.chdir(test_dir)

        test_file = "test6.csv"
        config_arr = np.genfromtxt(test_file, delimiter = ',',  usecols = (0))
        config = {
            'capex': config_arr[0],
            'max_gen': config_arr[1],
            'dam_capacity': config_arr[2],
            'starting_level': config_arr[3],
            'water_factor': config_arr[4],
            'pump_round_trip': config_arr[5],
            'section': 'test_basicpumpedhydro',
            'timestep_hrs': 1.0
        }
        
        self.assertRaises(mureilexception.ConfigException, self.hydro.set_config, config)

        os.chdir(cwd)
        

    def test_7(self):
        self.do_csv_test("test7.csv")        

    def test_8(self):
        self.do_csv_test("test8.csv")        

    def test_9(self):
        self.do_csv_test("test9.csv")        

    def test_10(self):
        self.do_csv_test("test10.csv")        


if __name__ == '__main__':
    unittest.main()
    
