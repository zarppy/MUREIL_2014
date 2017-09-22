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

import string
import numpy

from generator import singlepassgenerator
from tools import mureiltypes

class VariableGeneratorBasic(singlepassgenerator.SinglePassGeneratorBase):
    """Implement a basic model for variable generation that uses
    capacity factor time series to determine output, and calculates
    cost as a multiple of capacity. Capacity is determined by
    optimisable parameters.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            capex - the cost in $M per MW capacity
            size - the size in MW of plant for each unit of param
            type - a string name for the type of generator modelled
            data_type - a string key for the data required from the master for
                the set_data method.
            start_min_param - the minimum starting param value
            start_max_param - the maximum starting param value
        """
        return [
            ('capex', float, None),
            ('size', float, None),
            ('type', None, None),
            ('data_type', None, None),
            ('start_min_param', int, 1e20),
            ('start_max_param', int, 1e20)
            ]

    
    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        return [self.config['data_type']]
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        self.ts_cap_fac = data[self.config['data_type']]

        # For best speed performance, require numpy.array with dtype=float64.
        # This should have been converted in the Data module.
        mureiltypes.check_ndarray_float(self.ts_cap_fac)
        
        
    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised. Returns
        the number of series in the ts_cap_fac array, as
        configured by set_data.
        
        Outputs:
            param_count: non-negative integer - the number of
                parameters required.
        """
        ## TODO - check that this is set up
        return self.ts_cap_fac.shape[1] 
        
        
    def get_param_starts(self):
        list_len = self.get_param_count()
        if list_len > 0:
            if (self.config['start_min_param'] == 1e20):
                start_mins = []
            else:
                start_mins = (numpy.ones(list_len) * self.config['start_min_param']).tolist() 

            if (self.config['start_max_param'] == 1e20):
                start_maxs = []
            else:
                start_maxs = (numpy.ones(list_len) * self.config['start_max_param']).tolist() 
        else:
            start_mins = []
            start_maxs = []
            
        return start_mins, start_maxs
            
        
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation. This generator simply multiplies the capacity
                by a unit cost.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """
        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']
        cost = numpy.sum(params) * self.config['size'] * self.config['capex']

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output
    
    
    def interpret_to_string(self):
        """Return a string that describes the generator type and the
        current capacity, following a call to calculate_cost_and_output
        with set_current set.
        """
        return self.config['type'] + ' with capacities (MW): ' + (
            string.join(map('{:.2f} '.format, self.saved['capacity'])))
        
        
class VariableGeneratorLinearInstall(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by calculating an
    installation cost as well as capacity cost.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            Same config as VariableGeneratorBasic, with the addition of:
            install: float, price in $M to build any plant.
        """        
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None)]
    

    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation. This generator simply multiplies the capacity
                by a unit cost.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """

        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']
        active_sites = params[params > 0]
        cost = numpy.sum(active_sites) * self.config['capex'] * self.config['size'] + (
            self.config['install'] * active_sites.size)

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output


class VariableGeneratorExpCost(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by calculating an
    exponential method capacity cost.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            Same config as VariableGeneratorBasic, with the addition of:
            ### TODO - not yet fixed
            install: float, price in $M to build any plant.
        """        
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None)]
    
    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation, calculated using an exponential function.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """

        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']

        cost_temp = numpy.zeros(params.size)
        for i in range(params.size):
            if params[i] < 1:
                cost_temp[i] = 0
            else:
                cpt = ((self.config['install'] - (self.config['size'] * self.config['capex'])) *
                       numpy.exp(-0.1 * (params[i] - 1))) + (
                        self.config['size'] * self.config['capex'])
                cost_temp[i] = params[i] * cpt
        cost = cost_temp.sum()

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output
                

class VariableGeneratorSqrtCost(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by calculating an
    square-root method capacity cost.
            ### TODO - not yet fixed for units
    """
    
    def get_config_spec(self):
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None),
            ('max_count', float, None)]

    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation, calculated using a square-root function.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """

        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']

        cost_temp = numpy.zeros(params.size)
        m_gen = (self.config['capex'] * self.config['max_count']) / numpy.sqrt(self.config['max_count'])
        gen_add = self.config['install'] + (
            self.config['size'] * self.config['capex']) - m_gen
        for i in range(params.size):
            if params[i] < 1:
                cost_temp[i] = 0
            else:
                cost_temp[i] = m_gen * numpy.sqrt(params[i]) + gen_add
        cost = cost_temp.sum()

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output


class VariableGeneratorAsymptCost(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by using a
    method that has an asymptotic gradient for the capacity cost.
    """
    
    def get_config_spec(self):
        """Config spec as for VariableGeneratorBasic, with the addition of:
        install: in $M
        alpha: ?
        """
        
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None),
            ('alpha', float, None)]


    def get_data_types(self):
        """Ask for data types as for the Basic generator, plus the distances data,
        e.g. ts_wind wants ts_wind_distances.
        """
        basic_list = VariableGeneratorBasic.get_data_types(self)
        return basic_list + [self.config['data_type'] + '_distances'] 


    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        VariableGeneratorBasic.set_data(self, data)
        self.distances = data[self.config['data_type'] + '_distances']
        mureiltypes.check_ndarray_float(self.distances)


    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation, calculated using a square-root function.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """

        clipped = numpy.clip(params, 0, numpy.Inf)
        output = numpy.dot(self.ts_cap_fac, clipped) * self.config['size']

        cost_temp = numpy.zeros(params.size)
        alpha = self.config['alpha']
        a = self.config['capex'] * self.config['size']

        for i in range(params.size):
            if params[i] < 1:
                cost_temp[i] = 0
            else:
                cost_temp[i] = self.config['install'] + (a * ((numpy.sqrt(a + (alpha * params[i])**2)) + 
                    (numpy.sqrt(a) * numpy.log(params[i])) - (numpy.sqrt(a) * 
                    numpy.log(a + numpy.sqrt(a) * numpy.sqrt(a + (alpha * params[i])**2)))) / alpha)

        cost = cost_temp.sum()

        active_sites = (params > 0)
        cost_distance = self.distances[active_sites == True].sum()  #Already in units of $M/km

        cost += cost_distance
        
        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = clipped * self.config['size']
                
        return cost, output


class IncrementalVariableGeneratorBasic(VariableGeneratorBasic):
    """This is a hack for the GE demo, in advance of a decent system for handling
    the incremental / multi-decade operation. The model expects twice as many
    params to what it asked for, and then treats the first set as the total stock
    in that decade, and the second set as stock added in that decade.
    """
    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised. Returns
        the number of series in the ts_cap_fac array, as
        configured by set_data.

        Outputs:
            param_count: non-negative integer - the number of
                parameters required.
        """
        ## TODO - check that this is set up
        self.req_params = self.ts_cap_fac.shape[1]
        return self.req_params


    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.

        Inputs:
            params: list of numbers - from the optimiser, with the list
                twice as long as requested in get_param_count. The first half
                represents total stock in that decade, and the second the
                incremental build. 
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.

        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation. This generator simply multiplies the new capacity
                by a unit cost.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the first half of the params, and the capacity factor data.
        """
        output = numpy.dot(self.ts_cap_fac, params[:self.req_params]) * self.config['size']
        cost = numpy.sum(params[self.req_params:]) * self.config['size'] * self.config['capex']

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params[:self.req_params] * self.config['size']

        return cost, output
