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

import numpy

class LinearMissedSupply(singlepassgenerator.SinglePassGeneratorBase):
    """Missed supply model charging a flat rate per
    MWh missed.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)
        
        Config:
            cost_per_mwh: float - the cost in $ per MWh of missed supply
            timestep_hrs: float - the system timestep in hours
            variable_cost_mult: float - the value to multiply the calculated variable
                cost by, to account for a shorter dataset than the capex lifetime.
        """
        return [
            ('cost_per_mwh', float, None),
            ('timestep_hrs', float, None),
            ('variable_cost_mult', float, None)
            ]


    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Meets all remaining demand by pricing the missed supply
        penalty.
        
        Inputs:
            params: ignored
            rem_demand: numpy.array - a time series of the demand remaining
                to be met.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.

        Outputs:
            cost: number - sum of 'output' times configured cost_per_mwh, adjusted
                for timestep. 
            output: numpy.array - Power 'generated' at each timestep,
                simply rem_demand where > 0.
        """
        output = rem_demand.clip(0)
        sum_out = numpy.sum(output)
        # cost is in $M but cost_per_mwh is $
        cost = 1e-6 * sum_out * self.config['cost_per_mwh'] * self.config['timestep_hrs']
        # scale up to capex timescale
        cost *= self.config['variable_cost_mult'] 
        
        if save_result:
            self.saved['capacity'] = sum_out
            self.saved['output'] = numpy.copy(output)
            self.saved['cost'] = cost
            
        return cost, output


    def interpret_to_string(self):
        if self.saved:
            return 'Linear Missed-Supply, total {:.2f} MW-timestamps missed'.format(
                self.saved['capacity'])
        else:
            return None

            
class CappedMissedSupply(singlepassgenerator.SinglePassGeneratorBase):
    """Missed supply model charging a flat rate per
    MWh missed, and a penalty for going over a total limit.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Config:
            cost_per_mwh: float - the cost in $ per MWh of missed supply
            reliability_reqt: float - a percentage of total demand that can be
                missed before the penalty applies.
            penalty: float - in $M, the penalty if reliability is not met.
            timestep_hrs: float - the system timestep in hours
            variable_cost_mult: float - the value to multiply the calculated variable
                cost by, to account for a shorter dataset than the capex lifetime.
        """
        return [
            ('cost_per_mwh', float, None),
            ('reliability_reqt', float, None),
            ('penalty', float, None),
            ('timestep_hrs', float, None),
            ('variable_cost_mult', float, None)
            ]


    def get_data_types(self):
        """The demand timeseries is required to calculate the reliability requirement.
        """
        return ['ts_demand']

        
    def set_data(self, data):
        """The demand timeseries is required to calculate the reliability requirement,
        summed here to find total demand.
        """
        self.total_demand = float(sum(data['ts_demand']))
        
    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Meets all remaining demand by pricing the missed supply
        penalty per MW-timestep, with additional penalty for exceeding 
        average reliability limit over time period.
        
        Inputs:
            params: ignored
            rem_demand: numpy.array - a time series of the demand remaining
                to be met.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.

        Outputs:
            cost: number - sum of 'output' times configured cost_per_mwh,
                adjusted for timestep,
                plus configured penalty if total output / total demand 
                > reliability_reqt. 
            output: numpy.array - Power 'generated' at each timestep,
                simply rem_demand where > 0.
        """
        output = rem_demand.clip(0)
        sum_out = numpy.sum(output)

        # final cost is in $M, but cost_per_mwh is in $
        cost = 1e-6 * sum_out * self.config['cost_per_mwh'] * self.config['timestep_hrs']
        
        # unreliability as a percentage
        unreliability = sum_out / self.total_demand * 100.0
        
        # TODO - how often does the penalty apply?
        if (unreliability > self.config['reliability_reqt']): 
            cost += self.config['penalty']

        # Scale up to match capex timescales
        cost *= self.config['variable_cost_mult'] 

        if save_result:
            self.saved['capacity'] = sum_out
            self.saved['output'] = numpy.copy(output)
            self.saved['cost'] = cost
            self.saved['other'] = {'unreliability': unreliability}
            
        return cost, output


    def interpret_to_string(self):
        if self.saved:
            return 'Capped Missed-Supply, total {:.2f} MW-timestamps missed, unreliability {:.3f}%'.format(
                self.saved['capacity'], self.saved['other']['unreliability'])
        else:
            return None

class TimestepReliabilityMissedSupply(singlepassgenerator.SinglePassGeneratorBase):
    """Missed supply model charging a flat rate per
    MWh missed.  Reliability reported as a percentage of timesteps.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)
        
        Config:
            cost_per_mwh: float - the cost in $ per MWh of missed supply
            timestep_hrs: float - the system timestep in hours
            variable_cost_mult: float - the value to multiply the calculated variable
                cost by, to account for a shorter dataset than the capex lifetime.
        """
        return [
            ('cost_per_mwh', float, None),
            ('timestep_hrs', float, None),
            ('variable_cost_mult', float, None)
            ]


    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Meets all remaining demand by pricing the missed supply
        penalty.
        
        Inputs:
            params: ignored
            rem_demand: numpy.array - a time series of the demand remaining
                to be met.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.

        Outputs:
            cost: number - sum of 'output' times configured cost_per_mwh, adjusted
                for timestep. 
            output: numpy.array - Power 'generated' at each timestep,
                simply rem_demand where > 0.
        """
        
        output = rem_demand.clip(0)
        sum_out = numpy.sum(output)
        # cost is in $M but cost_per_mwh is $
        cost = 1e-6 * sum_out * self.config['cost_per_mwh'] * self.config['timestep_hrs']
        # scale up to capex timescale
        cost *= self.config['variable_cost_mult'] 

        timesteps_missed = numpy.count_nonzero(output)
        reliability_percent = (1 - float(timesteps_missed) / float(len(output))) * 100

        if save_result:
            self.saved['capacity'] = sum_out
            self.saved['output'] = numpy.copy(output)
            self.saved['cost'] = cost
            self.saved['other'] = {'reliability': reliability_percent}
        
        return cost, output


    def interpret_to_string(self):
        if self.saved:
            return 'Timestep Linear Missed-Supply, total {:.2f} MW-timestamps missed, reliability {:.3f}%'.format(
                self.saved['capacity'], self.saved['other']['reliability'])
        else:
            return None
