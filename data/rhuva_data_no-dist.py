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
# Based on Robert's case2
import pupynere as nc

import numpy

from data import datasinglepassbase
from tools import mureiltypes


class Data(datasinglepassbase.DataSinglePassBase):
    def complete_configuration(self):
        self.data = {}
                
        wind_gap = '11'
        solar_gap = '21'
        
        dir = '/mnt/meteo0/data/dargaville/rhuva/'
        file = 'RegGrid_wind_output_'+wind_gap+'point_gap.nc' 
        infile = dir + file
        f = nc.NetCDFFile(infile)
        temp = f.variables['wind_power'][:,:]
        if not mureiltypes.check_ndarray_float(temp, True):
            self.data['ts_wind'] = numpy.array(temp, dtype=float)
        else:
            self.data['ts_wind'] = temp

        file = 'RegGrid_dsr_output_'+solar_gap+'point_gap.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        temp = f.variables['dsr'][:,:]
        if not mureiltypes.check_ndarray_float(temp, True):
            self.data['ts_solar'] = numpy.array(temp, dtype=float)
        else:
            self.data['ts_solar'] = temp


        file = 'Aus_demand_2010_2011.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        temp = f.variables['ts_demand'][:]
        if not mureiltypes.check_ndarray_float(temp, True):
            self.data['ts_demand'] = numpy.array(temp, dtype=float)
        else:
            self.data['ts_demand'] = temp
        
        wind_nan = numpy.isnan(self.data['ts_wind'])
        solar_nan = numpy.isnan(self.data['ts_solar'])
        demand_nan = numpy.isnan(self.data['ts_demand'])
        
        wind_row = wind_nan.any(1)
        solar_row = solar_nan.any(1)
        
        combo = numpy.array([wind_row, solar_row, demand_nan])
        combo_flat = combo.any(0)
        
        self.data['ts_wind'] = self.data['ts_wind'][combo_flat == False, :]
        self.data['ts_solar'] = self.data['ts_solar'][combo_flat == False, :]
        self.data['ts_demand'] = self.data['ts_demand'][combo_flat == False]
        
        print self.data['ts_wind'].shape
        print self.data['ts_solar'].shape
        print self.data['ts_demand'].shape

        self.ts_length = self.data['ts_wind'].shape[0]

        file = 'Dist-to-nearest-cap_wind_'+wind_gap+'_gap.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        temp = f.variables['ts_wind_distances'][:]
        no_dist = numpy.zeros(len(temp))
        self.data['ts_wind_distances'] = no_dist #Give the distances zero for everywhere

        file = 'Dist-to-nearest-cap_dsr_'+solar_gap+'_gap.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        temp = f.variables['ts_solar_distances'][:]
        no_dist = numpy.zeros(len(temp))
        self.data['ts_solar_distances'] = no_dist
        
        return None

