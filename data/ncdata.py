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

"""Implements a Data class that reads in a list of variables from
   netCDF files, on a single pass into an array. Also reads in 
   a CSV matrix format.
"""

import pupynere as nc
import csv

from data import datasinglepassbase
from tools import mureilbuilder, mureiltypes, mureilexception

import numpy
import copy

class Data(datasinglepassbase.DataSinglePassBase):
    """Read in a list of variables from netCDF files.
    Checks if they are numpy.array(dtype=float), and if not,
    copies them to a numpy.array(dtype=float) array.
    """

    def process_initial_config(self):
        for list_type in ['ts_float_list', 'ts_int_list', 
            'other_float_list', 'other_int_list']:
            for series_name in self.config[list_type]:
                self.config_spec += [(series_name + '_vbl', None, series_name)]
                self.config_spec += [(series_name + '_file', None, None)]
        
        # CSV format requires a header and a 'time' column (ignored)
        # Will create a data object named series_name, and another named
        # series_name_hdr.
        for list_type in ['ts_csv_list']:
            for series_name in self.config[list_type]:
                self.config_spec += [(series_name + '_file', None, None)]


    def complete_configuration(self):
        self.data = {}

        for list_type in ['ts_float_list', 'ts_int_list', 
            'other_float_list', 'other_int_list']:

            for series_name in self.config[list_type]:        
                infile = self.config['dir'] + self.config[series_name + '_file']

                try:
                    f = nc.NetCDFFile(infile)
                except:
                    msg = ('File ' + infile + ' for data series ' + series_name +
                        ' was not opened.')
                    raise mureilexception.ConfigException(msg, {})

                try:
                    vbl = f.variables[self.config[series_name + '_vbl']]
                except:
                    msg = ('Variable ' + self.config[series_name + '_vbl'] +
                        ' not found in file ' + infile)
                    raise mureilexception.ConfigException(msg, {})
                    
                dims = len(vbl.shape)

                if (dims == 1):
                    temp = vbl[:]
                elif (dims == 2):
                    temp = vbl[:,:]
                else:
                    msg = 'Data series ' + series_name + ' has more than 2 dimensions, so is not handled.'
                    raise mureilexception.ConfigException(msg, {})

                if 'float' in list_type:
                    if not mureiltypes.check_ndarray_float(temp, True):
                        self.data[series_name] = numpy.array(temp, dtype=float)
                    else:
                        self.data[series_name] = temp
                else:
                    if not mureiltypes.check_ndarray_int(temp, True):
                        self.data[series_name] = numpy.array(temp, dtype=int)
                    else:
                        self.data[series_name] = temp

        for list_type in ['ts_csv_list']:
            for series_name in self.config[list_type]:        
                infile = self.config['dir'] + self.config[series_name + '_file']
                temp = []
                
                try:
                    with open(infile, 'rU') as n:
                        reader = csv.reader(n)
                        for row in reader:
                            if reader.line_num == 1:
                                self.data[series_name + '_hdr'] = row[1:]
                            else:
                                if reader.line_num == 2:
                                    temp = [map(float, (row[1:]))]
                                else:
                                    temp.append(map(float, (row[1:])))

                    self.data[series_name] = numpy.array(temp, dtype=float)
                    if not mureiltypes.check_ndarray_float(temp, True):
                        self.data[series_name] = numpy.array(temp, dtype=float)
                    else:
                        self.data[series_name] = temp

                except:
                    msg = ('File ' + infile + ' for data series ' + series_name +
                        ' was not opened or had an error in reading.')
                    raise mureilexception.ConfigException(msg, {})


        # Now apply the NaN filter to the ts lists, but note that the integer
        # ones are not identified as nan.
        all_ts = self.config['ts_float_list'] + self.config['ts_int_list'] + self.config['ts_csv_list']
        
        if len(all_ts) == 0:
            self.ts_length = 0
            logger.warning('No timeseries data defined')
        else:
            self.ts_length = self.data[all_ts[0]].shape[0]

            # Start with an array of 'False'
            nan_acc = (numpy.ones(self.ts_length) == 0)

            # Accumulate 'True' entries in nan_acc where NaN found in timeseries
            for ts_name in all_ts:
                ts_nan = numpy.isnan(self.data[ts_name])
                if ts_nan.ndim > 1:
                    ts_nan = ts_nan.any(1)

                # Check all the timeseries are the same length
                if not (len(ts_nan) == self.ts_length):
                    msg = ('Data series ' + ts_name +
                        ' is length {:d}, not matching {:d} of '.format(
                        len(ts_nan), self.ts_length) + all_ts[0])
                    raise mureilexception.ConfigException(msg, {})

                nan_acc = numpy.logical_or(nan_acc, ts_nan)

            # Clean up the timeseries using slices
            nan_acc = numpy.logical_not(nan_acc)
            for ts_name in all_ts:
                if self.data[ts_name].ndim == 1:
                    self.data[ts_name] = self.data[ts_name][nan_acc]            
                else:
                    self.data[ts_name] = self.data[ts_name][nan_acc, :]            

            self.ts_length = self.data[all_ts[0]].shape[0]

        self.is_configured = True

        return None


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
        description: a single-line text description of the dataset - e.g. VIC Feb 2009, 4x wind, 2x solar
        dir: full or relative path to file directory

        ts_float_list: list of names of floating point timeseries data - e.g. ts_wind, ts_solar.
            The ts_float_list and ts_int_list data are filtered for NaNs and timepoints with
            NaNs in any of the series are dropped out of all in ts_float_list and ts_int_list.
        ts_int_list: list of names of integer timeseries data, filtered for NaN with the ts_list. Note
            that numpy.nan cannot be stored in an integer array, so if you want nans, they must be in
            float arrays.

        other_float_list: list of names of other datasets, floating point type
        other_int_list: list of names of other datasets, integer type
        
        then for each name in ts_float_list, ts_int_list, other_float_list, other_int_list, e.g. ts_wind:
        ts_wind_file: filename of netCDF file with wind data
        ts_wind_vbl: optional - the name of the variable within the netCDF file. Defaults to 
            the series name, here ts_wind.
            
        ts_csv_list: list of names of csv timeseries data - e.g. ts_demand_matrix. The data is read into 
            series_name and the header into series_name_hdr. A timestamp column to the left is expected
            and ignored. Data is read in as floats.
            
        and for each name in ts_csv_list, e.g. ts_demand_matrix:
        ts_demand_matrix_file: string filename of the CSV file with the data.
        """
        return [
            ('description', None, 'None'),
            ('dir', None, './'),
            ('ts_float_list', mureilbuilder.make_string_list, []),
            ('ts_int_list', mureilbuilder.make_string_list, []),
            ('other_float_list', mureilbuilder.make_string_list, []),
            ('other_int_list', mureilbuilder.make_string_list, []),
            ('ts_csv_list', mureilbuilder.make_string_list, [])
            ]
        
