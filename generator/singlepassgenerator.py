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

"""Module with base class for single-pass generator objects.
"""

from tools import configurablebase

class SinglePassGeneratorBase(configurablebase.ConfigurableBase):
    """The base class for generic generators that calculate the
    output and cost based on the full timeseries in one pass. 
    """
    
    def __init__(self):
        """Do very basic initialisation of class members.
        Valid operation does not occur until all of the 'set'
        functions below, and set_config(), have been called.
        """
        configurablebase.ConfigurableBase.__init__(self)
        self.data = {}
        self.saved = {'capacity': None, 'output': None, 'cost': None, 'other': None}
        

    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        return []
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        self.data = data
        
        
    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised.
        
        Outputs:
            param_count: non-negative integer - the number of
                parameters required.
        """
        return 0
        
    
    def get_param_starts(self):
        """Return two lists - one for min, one max, for starting values for the
        params. Must be either empty or the same length as param_count.
        
        Outputs:
            min_start_list: list of param integers, or []
            max_start_list: list of param integers, or []
        """
    
        return [], []
        
    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        This function is required to be thread-safe (when save_result is False) to allow 
        multiprocessing.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation.
            output: numpy.array - a time series of the power output in MW
                from this generator.
        """
        return None
    
    
    def interpret_to_string(self):
        """Return a string that describes the generator type and the
        current capacity, following a call to calculate_cost_and_output
        with set_current set.
        """
        return None
        
        
    def get_saved_result(self):
        """Return a dict with capacity, output, cost and other, following a call
        to calculate_cost_and_output with save_result set.
        """
        return self.saved
        
    