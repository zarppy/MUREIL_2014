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
"""Test of config-spec components of tools/mureilbuilder.py.

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_config_spec.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy

from tools import mureilexception, testutilities

from tools import globalconfig

class TestCalcs(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_convert_single_1(self):
        # provides timestep_mins
        global_conf = {}
        global_conf['timestep_mins'] = 30
        global_conf['carbon_price'] = 25
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()

        gc.set_config(global_conf)
        exp_pre = {'timestep_mins': 30, 'timestep_hrs': 0.5,
            'carbon_price': 25, 'carbon_price_m': 25e-6,
            'data_ts_length': 365 * 3, 'time_period_yrs': 5}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        exp_post['time_scale_up_mult'] = 16 * 5 * (365.25 / 365)
        exp_post['variable_cost_mult'] = exp_post['time_scale_up_mult']
        self.assertTrue((exp_post == gc.get_config()))


    def test_convert_multi_1(self):
        # provides timestep_mins
        global_conf = {}
        global_conf['timestep_mins'] = 30
        global_conf['carbon_price'] = {2040:25, 2030:12.5, 2010:6}
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)
        exp_pre = {'timestep_mins': 30, 
            'timestep_hrs': 0.5,
            'carbon_price': {2040:25, 2030:12.5, 2010:6}, 
            'carbon_price_m': {2040:25e-6, 2030:12.5e-6, 2010:6e-6},
            'data_ts_length': 365 * 3, 'time_period_yrs': 5}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        exp_post['time_scale_up_mult'] = 16 * 5 * (365.25 / 365)
        exp_post['variable_cost_mult'] = exp_post['time_scale_up_mult']
        self.assertTrue((exp_post == gc.get_config()))


    def test_reject_multi_1(self):
        # provides timestep_hrs, but as a multi-period
        global_conf = {}
        global_conf['timestep_hrs'] = {2010:0.5, 2020:1.0,2030:1.5}
        global_conf['carbon_price'] = {2040:25, 2030:12.5, 2010:6}
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()
        with self.assertRaises(mureilexception.ConfigException) as cm:
            gc.set_config(global_conf)
            
        self.assertEqual(cm.exception.msg,
            'Global timestep_hrs is required to have the same value across the sim.')


    def test_reject_multi_2(self):
        # provides timestep_mins, but as a multi-period
        global_conf = {}
        global_conf['timestep_mins'] = {2010:0.5, 2020:1.0,2030:1.5}
        global_conf['carbon_price'] = {2040:25, 2030:12.5, 2010:6}
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()
        with self.assertRaises(mureilexception.ConfigException) as cm:
            gc.set_config(global_conf)
       
        self.assertEqual(cm.exception.msg, 
            'Global timestep_mins is required to have the same value across the sim.')


    def test_reject_multi_3(self):
        # provides a multi-period time_period_yrs
        global_conf = {}
        global_conf['timestep_mins'] = 0.5
        global_conf['carbon_price'] = {2040:25, 2030:12.5, 2010:6}
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = {2010:55, 2030:4}
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)
        
        with self.assertRaises(mureilexception.ConfigException) as cm: 
            gc.post_data_global_calcs()
            
        self.assertEqual(cm.exception.msg, 
            'Global time_period_yrs is required to have the same value across the sim.')


    def test_convert_single_2(self):
        # provides timestep_hrs
        global_conf = {}
        global_conf['timestep_hrs'] = 0.5
        global_conf['carbon_price'] = 12.5
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)

        exp_pre = {'timestep_mins': 30, 'timestep_hrs': 0.5,
            'carbon_price': 12.5, 'carbon_price_m': 12.5e-6,
            'data_ts_length': 365 * 3, 'time_period_yrs': 5}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        exp_post['time_scale_up_mult'] = 16 * 5 * (365.25 / 365)
        exp_post['variable_cost_mult'] = exp_post['time_scale_up_mult']
        self.assertTrue((exp_post == gc.get_config()))


    def test_convert_single_3(self):
        # provides both timestep_mins and timestep_hrs. timestep_mins takes priority.
        global_conf = {}
        global_conf['timestep_mins'] = 30
        global_conf['timestep_hrs'] = 1.5
        global_conf['carbon_price'] = 12.5
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)

        exp_pre = {'timestep_mins': 30, 'timestep_hrs': 0.5,
            'carbon_price': 12.5, 'carbon_price_m': 12.5e-6,
            'data_ts_length': 365 * 3, 'time_period_yrs': 5}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        exp_post['time_scale_up_mult'] = 16 * 5 * (365.25 / 365)
        exp_post['variable_cost_mult'] = exp_post['time_scale_up_mult']
        self.assertTrue((exp_post == gc.get_config()))

    
    def test_missing_timestep_carbon(self):
        # provides not very much
        global_conf = {}
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)
        exp_pre = {'data_ts_length': 365 * 3, 'time_period_yrs': 5}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        self.assertTrue((exp_post == gc.get_config()))


    def test_missing_timeperiod_yrs(self):
        global_conf = {}
        global_conf['timestep_mins'] = 30
        global_conf['carbon_price'] = 25
        global_conf['data_ts_length'] = 365 * 3
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)

        exp_pre = {'timestep_mins': 30, 'timestep_hrs': 0.5,
            'carbon_price': 25, 'carbon_price_m': 25e-6,
            'data_ts_length': 365 * 3}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        self.assertTrue((exp_post == gc.get_config()))

    
    def test_time_scale_up_mult(self):
        # provides both timestep_mins and timestep_hrs. timestep_mins takes priority.
        global_conf = {}
        global_conf['timestep_mins'] = 30
        global_conf['timestep_hrs'] = 1.5
        global_conf['carbon_price'] = 12.5
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        global_conf['time_scale_up_mult'] = 100
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)

        exp_pre = {'timestep_mins': 30, 'timestep_hrs': 0.5,
            'carbon_price': 12.5, 'carbon_price_m': 12.5e-6,
            'data_ts_length': 365 * 3, 'time_period_yrs': 5,
            'time_scale_up_mult': 100}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        exp_post['time_scale_up_mult'] = 100
        exp_post['variable_cost_mult'] = exp_post['time_scale_up_mult']
        self.assertTrue((exp_post == gc.get_config()))


    def test_variable_cost_mult(self):
        # provides both timestep_mins and timestep_hrs. timestep_mins takes priority.
        global_conf = {}
        global_conf['timestep_mins'] = 30
        global_conf['timestep_hrs'] = 1.5
        global_conf['carbon_price'] = 12.5
        global_conf['data_ts_length'] = 365 * 3
        global_conf['time_period_yrs'] = 5
        global_conf['variable_cost_mult'] = 100
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)

        exp_pre = {'timestep_mins': 30, 'timestep_hrs': 0.5,
            'carbon_price': 12.5, 'carbon_price_m': 12.5e-6,
            'data_ts_length': 365 * 3, 'time_period_yrs': 5,
            'variable_cost_mult': 100}
        self.assertTrue((exp_pre == gc.get_config()))

        gc.post_data_global_calcs()
        exp_post = exp_pre
        exp_post['time_scale_up_mult'] = 16 * 5 * (365.25 / 365)
        exp_post['variable_cost_mult'] = 100
        self.assertTrue((exp_post == gc.get_config()))


    def test_missing_ts_length(self):
        # provides both timestep_mins and timestep_hrs. timestep_mins takes priority.
        global_conf = {}
        global_conf['timestep_mins'] = 30
        global_conf['timestep_hrs'] = 1.5
        global_conf['carbon_price'] = 12.5
        global_conf['time_period_yrs'] = 5
        
        gc = globalconfig.GlobalBase()
        gc.set_config(global_conf)

        exp_pre = {'timestep_mins': 30, 'timestep_hrs': 0.5,
            'carbon_price': 12.5, 'carbon_price_m': 12.5e-6,
            'time_period_yrs': 5}
        self.assertTrue((exp_pre == gc.get_config()))

        with self.assertRaises(mureilexception.ConfigException) as cm:
            gc.post_data_global_calcs()
            
        self.assertEqual(cm.exception.msg, 
            'Global calculations of time_scale_up_mult require the data_ts_length parameter to be set')


if __name__ == '__main__':
    unittest.main()
    
