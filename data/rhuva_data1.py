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
# Based on Robert's case1
import pupynere as nc

import numpy

from data import datasinglepassbase

class Data(datasinglepassbase.DataSinglePassBase):
    def complete_configuration(self):
        self.data = {}
        
        dir = '/export/karoly2/rhuva/phd/ACCESS/muriel/access_2month_optim/'
        file = 'CoV_wind_station_output_prox_penalty.nc' #file with _II has smaller exclusion zone
        infile = dir + file
        f = nc.NetCDFFile(infile)
        self.data['ts_wind'] = f.variables['CoV_wind'][:,:]

        file = 'CoV_dsr_station_output_prox_penalty.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        self.data['ts_solar'] = f.variables['CoV_dsr'][:,:]

        file = 'Aus_demand_sample_raw.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        self.data['ts_demand'] = f.variables['ts_demand'][:]
        
        wind_nan = numpy.isnan(self.data['ts_wind'])
        solar_nan = numpy.isnan(self.data['ts_solar'])
        demand_nan = numpy.isnan(self.data['ts_demand'])
        
        wind_row = wind_nan.any(1)
        solar_row = solar_nan.any(1)
        
        combo = numpy.array([wind_row, solar_row, demand_nan])
        combo_flat = combo.any(0)
        
        self.data['ts_wind'] = numpy.array(
            self.data['ts_wind'][combo_flat == False, :], dtype=float)
        self.data['ts_solar'] = numpy.array(
            self.data['ts_solar'][combo_flat == False, :], dtype=float)
        self.data['ts_demand'] = numpy.array(
            self.data['ts_demand'][combo_flat == False], dtype=float)
        
        print self.data['ts_wind'].shape
        print self.data['ts_solar'].shape
        print self.data['ts_demand'].shape
              
        self.ts_length = self.data['ts_wind'].shape[0]
        
        return None
