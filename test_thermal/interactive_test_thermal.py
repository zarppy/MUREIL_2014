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
import numpy as np
import sys
sys.path.append('..')
import thermal.slowresponsethermal
config = {'capex': 3.0, 'fuel_price_mwh': 10, 'carbon_price': 5, 'carbon_intensity': 1.0, 'timestep_hrs': 1.0, 'variable_cost_mult': 1.0, 'ramp_time_mins': 240, 'type': 'bc'}
ts_demand = {'ts_demand': np.array([1, 2, 3], dtype=float)}
rem_demand = np.array([3, 4, 5], dtype=float)
t = thermal.slowresponsethermal.SlowResponseThermal()
t.set_config(config)
t.set_data(ts_demand)
cost, ts = t.calculate_cost_and_output([5], rem_demand)
