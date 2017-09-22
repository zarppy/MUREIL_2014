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

from generator import singlepassgenerator
from tools import mureiltypes

import numpy
import copy

class SlowResponseThermal(singlepassgenerator.SinglePassGeneratorBase):
    """A slow-response thermal generator that looks at the timeseries to
    determine when to turn on. Optimisable capacity.
    """

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)
        
        Configuration:
            capex: float - Cost in $M per MW of capacity installed
            fuel_price_mwh: float - Cost in $ per MWh generated
            carbon_price: float - Cost in $ per Tonne
            carbon_intensity: float - in kg/kWh or equivalently T/MWh
            timestep_hrs: float - the system timestep in hours
            variable_cost_mult: float - the value to multiply the calculated variable
                cost by, to account for a shorter dataset than the capex lifetime.
            ramp_time_mins: float - the ramp-time to full power. Model will linearly
                ramp to this.
            size - the size in MW of plant for each unit of param
        """
        return [
            ('capex', float, None),
            ('fuel_price_mwh', float, None),
            ('carbon_price', float, None),
            ('carbon_intensity', float, None),
            ('timestep_hrs', float, None),
            ('variable_cost_mult', float, None),
            ('ramp_time_mins', float, None),
            ('type', None, None),
            ('size', float, 100)
            ]

    def get_param_count(self):
        """Ask for 1 parameter to specify the capacity of fossil to build.
        """
        return 1


    def get_data_types(self):
        """The demand timeseries is supplied for use in forecasting the required demand.
        """
        
        return ['ts_demand']

        
    def set_data(self, data):
        """The demand timeseries is supplied for use in forecasting the required demand.
        """
        
        self.ts_demand = data['ts_demand']
        mureiltypes.check_ndarray_float(self.ts_demand)
    
    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Attempts to meet remaining demand by burning fossil fuel, and
        builds capacity as directed by its params. Chooses when to ramp up
        based on ts_demand and rem_demand.
        
        Inputs:
            params: specifies capacity in MW as params * 100
            rem_demand: numpy.array - a time series of the demand remaining
                 to be met.
            save_result: boolean, default False - if set, save the results
                 from these params and rem_demand into the self.saved dict.
         Outputs:
            cost: number - capex cost plus fuel and carbon tax cost. 
            output: numpy.array - Power generated at each timestep.
         """
 
        capacity = params[0] * self.config['size']
        # numpy.clip sets lower and upper bounds on array values
        # output = rem_demand.clip(0, max_cap)

   
        # output = numpy.ones(len(rem_demand), dtype=float) * capacity
        output = numpy.zeros(len(rem_demand))

        ###################################################################

        # Now write code to decide when to turn it on! 'rem_demand' is demand at this point in the 
        # dispatch hierarchy, and 'self.ts_demand' is the total demand. Put the result into
        # 'output'. Parameter 'self.config['ramp_time_mins']' is available, representing the ramp
        # time to full power in minutes.

        ts_demand = self.ts_demand
        avail_demand = copy.deepcopy(rem_demand)
        ramp_time_mins = self.config['ramp_time_mins']

        therm_out = 0 # initial thermal output assumed zero
        max_grad = capacity/(ramp_time_mins/60) # max response gradient
          
        max_inc = max_grad * self.config['timestep_hrs'] # max inc/dec based on ramp

        for i in range(len(rem_demand)):
            des_inc = rem_demand[i] - therm_out # desired increase to meet rem_demand if no ramp limit
            if abs(des_inc) <= max_inc: # if the inc/dec in demand is less than max ramp
                therm_out =  therm_out + des_inc 
            else:  # the inc/dec in demand is greater than max ramp
                therm_out = therm_out + max_inc * cmp(des_inc,0)
               

            if therm_out > capacity: # if calc ramped output greater than capacity 
                therm_out = capacity # limit to max capacity
            if therm_out < 0: # if calc ramped output less than zero
                therm_out = 0 # limit to  zero


            output[i] = therm_out



         # TODO - precalculate the functions of config in set_config for improved speed
         
        variable_cost = numpy.sum(output) * self.config['timestep_hrs'] * (
            self.config['fuel_price_mwh'] + (
            self.config['carbon_price'] * self.config['carbon_intensity'])) / 1e6
        cost = variable_cost * self.config['variable_cost_mult'] + self.config['capex'] * capacity
        
        if save_result:
            self.saved['capacity'] = capacity
            self.saved['cost'] = cost
            self.saved['output'] = numpy.copy(output)
 
        return cost, output
         
 
    def interpret_to_string(self):
        if self.saved:
            return 'Ramped Fossil Thermal, type ' + self.config['type'] + ', optimisable, capacity (MW) {:.2f}'.format(
                self.saved['capacity'])
        else:
            return None



class SlowResponseThermalFixed(SlowResponseThermal):
    """A slow-response thermal generator that looks at the timeseries to
    determine when to turn on. Capacity is fixed at fixed_capacity.
    """

    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Return the cost and output function from the optimisable slow
        response thermal, with capacity parameter set to fixed capacity.
        """
        return SlowResponseThermal.calculate_cost_and_output(self, 
            [self.config['fixed_capacity'] / self.config['size']], rem_demand, save_result)

    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)
        
        Configuration:
            as for SlowResponseThermal, with the addition of:
            fixed_capacity: MW of capacity installed
        """
        return (
            SlowResponseThermal.get_config_spec(self) + [
            ('fixed_capacity', float, None)
            ])

    def get_param_count(self):
        """No parameters required
        """
        return 0

    def interpret_to_string(self):
        if self.saved:
            return 'Ramped Fossil Thermal, type ' + self.config['type'] + ', fixed capacity (MW) {:.2f}'.format(
                self.saved['capacity'])
        else:
            return None

            
