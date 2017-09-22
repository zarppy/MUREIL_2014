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
import math

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
            ('fuel_price_tonne', float, None),
            ('carbon_price', float, None),
            ('c_intensity_ratio', float, None),
            ('timestep_mins', float, None),
            ('variable_cost_mult', float, None),
            ('time_const_mins', float, None),
            ('eta_max', float, None),
            ('lwr_heat_val', float, None),
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
 
        capacity = params[0] * 100
        
        # numpy.clip sets lower and upper bounds on array values
        # output = rem_demand.clip(0, max_cap)
        # output = numpy.ones(len(rem_demand), dtype=float) * capacity



        # Beta generation profile
        # assumes initial thermal output is zero, can be changed at init_therm_out
        # assumes maximum input demand signal is max capacity (see clip_demand)

        output = numpy.zeros(len(rem_demand)+1)
        init_therm_out = 0 # initial thermal output assumed zero
        output[0] = init_therm_out     
        ts_demand = self.ts_demand
        avail_demand = copy.deepcopy(rem_demand)
        max_eff = self.config['eta_max']
        time_step = self.config['timestep_mins']/60
        time_const_hrs = self.config['time_const_mins']/60
        fuel_flow_rate = numpy.zeros(len(rem_demand))
        
        clip_demand = rem_demand.clip(0, capacity)  # clips generator demand to max capactiy
   

        if self.config['size'] >0 and self.config['eta_max'] >0: 

            eta_ss = numpy.ones(len(rem_demand))* max_eff * numpy.sqrt(clip_demand/capacity)
            exponent = -1*math.expm1(-1*time_step/time_const_hrs) # precalculate exponent       

            for i in numpy.delete(range(len(clip_demand)), [0]):
                output[i] = output[i-1]+(clip_demand[i] - output[i-1])* exponent

                if eta_ss[i] > 0:
                    # print 'eta_ss:', eta_ss[i]
                    fuel_flow_rate[i] = clip_demand[i]/(self.config['lwr_heat_val']*eta_ss[i])
                                                
            #fuel_flow_rate = numpy.where(eta_ss>0, clip_demand/(self.config['lwr_heat_val']*eta_ss), 0) #kg/s
        

        output = numpy.delete(output, len(output)-1) 

        fuel_kg = fuel_flow_rate * time_step * 60 * 60 # kg
        fuel_cost_mil = (numpy.sum(fuel_kg)/1000 * self.config['fuel_price_tonne'])/1e6
        carbon_cost_mil = (numpy.sum(fuel_kg)/1000 * self.config['c_intensity_ratio']*\
                        self.config['carbon_price'])/1e6                 
        variable_cost_mil = fuel_cost_mil + carbon_cost_mil

        cost = variable_cost_mil * self.config['variable_cost_mult'] + self.config['capex'] * capacity



        #TODO - precalculate the functions of config in set_config for improved speed
         
    

        """
            variable_cost = numpy.sum(output) * self.config['timestep_hrs'] * (
            self.config['fuel_price_mwh'] + (
            self.config['carbon_price'] * self.config['carbon_intensity'])) / 1e6


      
        cost = variable_cost * self.config['variable_cost_mult'] + self.config['capex'] * capacity

        """

        
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
            [self.config['fixed_capacity'] / 100], rem_demand, save_result)

    
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

            
