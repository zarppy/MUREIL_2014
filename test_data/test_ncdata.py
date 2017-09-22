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
"""Test of data/ncdata.py

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_ncdata.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy
import pupynere as nc

from tools import mureilexception, testutilities

import data.ncdata

class TestNcData(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.data = data.ncdata.Data()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_normal(self):
        # first, create some netCDF files to test with
        # create two files, and assign some variables to each
        
        # float timeseries
        ts_wind = numpy.array([[1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, numpy.nan],
         [1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, 4]])
        ts_solar = numpy.array([[4, 3.3], [6, 3], [4, 4], [2, 1],
            [4, 3.3], [4, 3], [4, numpy.nan], [2, 1]])
        
        # integer timeseries
        ts_time = numpy.array([[1, 2, 3, 4], [4, 5, 6, 7], [7, 6, 5, 4], 
            [1, 2, 3, 4], [4, 5, 6, 7], [7, 6, 5, 4], [4, 5, 6, 7],[4, 5, 6, 7]])
        ts_vector = numpy.array([1, 2, 3, 4, 5, 6, 7, 3])
        
        # float other
        float_1 = numpy.array([1.0, numpy.nan, 3.0, 4.0])
        
        # integer other
        int_1 = numpy.array([443, 45, 43, 23, 34])

        f1 = nc.NetCDFFile('test_normal_1.nc','w')
        f2 = nc.NetCDFFile('test_normal_2.nc','w')
        
        # put ts_wind, ts_time and float_1 into file 1
        f1.createDimension('wx', ts_wind.shape[0])
        f1.createDimension('wy', ts_wind.shape[1])
        f1.createDimension('tx', ts_time.shape[0])
        f1.createDimension('ty', ts_time.shape[1])
        f1.createDimension('fx', float_1.shape[0])
        
        # put ts_solar, ts_vector and int_1 into file 2
        f2.createDimension('sx', ts_solar.shape[0])
        f2.createDimension('sy', ts_solar.shape[1])
        f2.createDimension('vx', ts_vector.shape[0])
        f2.createDimension('ix', int_1.shape[0])
        
        ts_wind_var = f1.createVariable('ts_wind','float64',('wx','wy'))
        ts_time_var = f1.createVariable('ts_time','int32',('tx','ty'))
        float_1_var = f1.createVariable('float_1','float32',('fx',))
        
        ts_solar_var = f2.createVariable('ts_solar','float32',('sx','sy'))
        ts_vector_var = f2.createVariable('ts_vector','float32',('vx',))
        int_1_var = f2.createVariable('funny_int_1','int32',('ix',))
        
        ts_wind_var[:,:] = ts_wind
        ts_time_var[:,:] = ts_time
        float_1_var[:] = float_1
        ts_solar_var[:,:] = ts_solar
        ts_vector_var[:] = ts_vector
        int_1_var[:] = int_1
        
        f1.close()
        f2.close()
        
        config = {
            'description': 'test normal',
            'model': 'data.ncdata.py',
            'section': 'Data',
            'ts_float_list': 'ts_wind ts_solar',
            'ts_int_list': 'ts_time ts_vector',
            'other_float_list': 'float_1',
            'other_int_list': 'int_1',
            'ts_wind_file': 'test_normal_1.nc',
            'ts_solar_file': 'test_normal_2.nc',
            'ts_time_file': 'test_normal_1.nc',
            'ts_vector_file': 'test_normal_2.nc',
            'float_1_file': 'test_normal_1.nc',
            'int_1_file': 'test_normal_2.nc',
            'int_1_vbl': 'funny_int_1'
            }
            
        try:
            self.data.set_config(config)
            results = {}
            for series_name in ['ts_wind', 'ts_solar', 'ts_time', 'ts_vector',
                'float_1', 'int_1']:
                results[series_name] = self.data.get_timeseries(series_name)

            ts_len = self.data.get_ts_length()

        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    


        exp_ts_sel = [0,1,2,4,5,7]
        exp_ts_wind = numpy.array(ts_wind[exp_ts_sel], dtype=float)
        exp_ts_solar = numpy.array(ts_solar[exp_ts_sel], dtype=float)
        exp_ts_time = ts_time[exp_ts_sel]
        exp_ts_vector = ts_vector[exp_ts_sel]
        exp_float_1 = numpy.array(float_1, dtype=float)
        exp_int_1 = int_1

        self.assertTrue(numpy.allclose(exp_ts_wind, results['ts_wind']))
        self.assertTrue(numpy.allclose(exp_ts_solar, results['ts_solar']))
        self.assertTrue(numpy.allclose(exp_ts_time, results['ts_time']))
        self.assertTrue(numpy.allclose(exp_ts_vector, results['ts_vector']))
        self.assertTrue(numpy.allclose(exp_int_1, results['int_1']))

        # Can't just compare exp_float_1 because it has a nan in it. Instead,
        # check that the nan is there, and that the rest of the array is as
        # expected.
        self.assertTrue(numpy.all(numpy.isnan(exp_float_1) 
            == numpy.isnan(results['float_1'])))
        self.assertTrue(numpy.allclose(exp_float_1[[0,2,3]], 
            results['float_1'][[0,2,3]]))

        # and check that all the floats are float64
        self.assertTrue(results['ts_wind'].dtype.name == 'float64')
        self.assertTrue(results['ts_solar'].dtype.name == 'float64')
        self.assertTrue(results['float_1'].dtype.name == 'float64')

        self.assertTrue((ts_len == 6))


    def test_file_missing(self):
        
        config = {
            'model': 'data.ncdata.py',
            'section': 'Data',
            'description': 'test file missing',
            'ts_float_list': 'ts_wind ts_solar',
            'ts_wind_file': 'not_there.nc',
            'ts_solar_file': 'also_not_there.nc',
            }

        self.assertRaises(mureilexception.ConfigException, 
            self.data.set_config, config)

    
    def test_config_file_missing_ts_float(self):
        
        config = {
            'model': 'data.ncdata.py',
            'section': 'Data',
            'description': 'test file missing',
            'ts_float_list': 'ts_wind ts_solar',
            'ts_wind_file': 'not_there.nc'
            }
    
        self.assertRaises(mureilexception.ConfigException, 
            self.data.set_config, config)
        

    def test_config_file_missing_ts_int(self):
        
        config = {
            'model': 'data.ncdata.py',
            'section': 'Data',
            'description': 'test file missing',
            'ts_int_list': 'ts_wind ts_solar',
            'ts_wind_file': 'not_there.nc'
            }
    
        self.assertRaises(mureilexception.ConfigException, 
            self.data.set_config, config)


    def test_config_file_missing_other_float(self):
        
        config = {
            'model': 'data.ncdata.py',
            'section': 'Data',
            'description': 'test file missing',
            'other_float_list': 'ts_wind ts_solar',
            'ts_wind_file': 'not_there.nc'
            }
    
        self.assertRaises(mureilexception.ConfigException, 
            self.data.set_config, config)


    def test_config_file_missing_other_int(self):
        
        config = {
            'model': 'data.ncdata.py',
            'section': 'Data',
            'description': 'test file missing',
            'other_int_list': 'ts_wind ts_solar',
            'ts_wind_file': 'not_there.nc'
            }
    
        self.assertRaises(mureilexception.ConfigException, 
            self.data.set_config, config)


    def test_variable_missing(self):
        
        # first, create a netCDF files to test with
        
        # float timeseries
        ts_wind = numpy.array([[1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, numpy.nan],
         [1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, 4]])

        f1 = nc.NetCDFFile('test_missing_1.nc','w')
        
        # put ts_wind, ts_time and float_1 into file 1
        f1.createDimension('wx', ts_wind.shape[0])
        f1.createDimension('wy', ts_wind.shape[1])
        
        ts_wind_var = f1.createVariable('ts_wind_funny','float64',('wx','wy'))
        ts_wind_var[:,:] = ts_wind
        
        f1.close()
        
        config = {
            'description': 'test variable missing',
            'model': 'data.ncdata.py',
            'section': 'Data',
            'ts_float_list': 'ts_wind',
            'ts_wind_file': 'test_missing_1.nc'
            }
            
        self.assertRaises(mureilexception.ConfigException, 
            self.data.set_config, config)


    def test_different_lengths(self):
        
        # first, create a netCDF files to test with
        
        # float timeseries
        ts_wind = numpy.array([[1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, numpy.nan],
         [1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, 4]])

        ts_solar = numpy.array([[1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, numpy.nan],
         [1, 2, 3.4], [4, 5, 6], [4, 3, 2], [5, 5, 4], [5, 5, 4], [5, 5, 4]])

        f1 = nc.NetCDFFile('test_different_lengths.nc','w')
        
        f1.createDimension('wx', ts_wind.shape[0])
        f1.createDimension('wy', ts_wind.shape[1])
        f1.createDimension('sx', ts_solar.shape[0])
        f1.createDimension('sy', ts_solar.shape[1])
        
        ts_wind_var = f1.createVariable('ts_wind','float64',('wx','wy'))
        ts_wind_var[:,:] = ts_wind
        ts_solar_var = f1.createVariable('ts_solar','float64',('sx','sy'))
        ts_solar_var[:,:] = ts_solar
        
        f1.close()
        
        config = {
            'description': 'test different length ts',
            'model': 'data.ncdata.py',
            'section': 'Data',
            'ts_float_list': 'ts_wind ts_solar',
            'ts_wind_file': 'test_different_lengths.nc',
            'ts_solar_file': 'test_different_lengths.nc'
            }
            
        self.assertRaises(mureilexception.ConfigException, 
            self.data.set_config, config)



if __name__ == '__main__':
    unittest.main()
    
