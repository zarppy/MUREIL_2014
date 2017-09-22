#
#
# Copyright (C) University of Melbourne 2013
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
"""Test of demandmatrix.py

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_demandmatrix.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy as np
import tools.mureilexception as mureilexception
import tools.mureilbuilder as mureilbuilder

from tools import testutilities

import numpy

import demand.demandmatrix
import data.ncdata

class TestDemandMatrix(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.demand = demand.demandmatrix.DemandMatrix()
        self.data = data.ncdata.Data()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_simple(self):
        demand_config = {
            'data_name': 'demand_data',
            'node_list_name': 'demand_data_hdr',
            'bid_price': {2010: 10000, 2020: 20000},
            'scale': {2010: 1.0, 2030: 1.5}
        }

        data_config = {
            'ts_csv_list' : 'demand_data',
            'demand_data_file' : 'short_data.csv'
        }
        
        run_periods = [2010, 2020, 2030]
        
        try:
            self.data.set_config(data_config)
            self.demand.set_config(demand_config, run_periods=run_periods)

            mureilbuilder.supply_single_pass_data(self.demand, self.data, 'demand')

        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    

        exp_names = ['DAT1','DAT2','DAT3']
        names = self.demand.get_node_names()
        self.assertEqual(names, exp_names)

        exp_data = numpy.array([[1,2,3],
            [4,5,6],[7,8,9],[10,11,12]])
        data = self.demand.get_data(2010)
        self.assertTrue(numpy.allclose(data, exp_data))

        data = self.demand.get_data(2030)
        self.assertTrue(numpy.allclose(data, exp_data * 1.5))

        bid = self.demand.get_bid_prices(2010)
        self.assertTrue(numpy.allclose(bid, [10000, 10000, 10000]))

        bid = self.demand.get_bid_prices(2030)
        self.assertTrue(numpy.allclose(bid, [20000, 20000, 20000]))
 
        self.assertEqual(self.data.ts_length, 4)

if __name__ == '__main__':
    unittest.main()
    
