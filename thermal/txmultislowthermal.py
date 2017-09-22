#
#
# Copyright (C) University of Melbourne 2013
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

"""Module for a slow-response thermal model using the txmultigenerator base class.
"""

from tools import configurablebase, mureilexception
from generator import txmultigeneratormultisite
import copy
import numpy


class TxMultiSlowOptimisableThermal(txmultigeneratormultisite.TxMultiGeneratorMultiSite):
    """A simple implementation of an instant-output thermal generator, such
    as a peaking gas turbine, which requires an optimisation parameter. This
    implementation handles only one site.
    """

    def get_details(self):
        """Return a list of flags indicating the properties of the generator.
        """
        flags = txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_details(self)
        flags['dispatch'] = 'ramp'
        flags['technology'] = self.config['tech_type']
        
        return flags
        

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            as for txmultigenerator.TxMultiGeneratorMultiSite, plus:
            
            tech_type: string - the generic technology type, to report in get_details() as technology.
            detail_type: string - a specific name, e.g. 'onshore_wind_vic', for printing in an output string
            site_index: integer - the index of the site where this instant thermal is located
            fuel_price_mwh: float - Cost in $ per MWh generated
            carbon_price_m: float - Cost in $M per Tonne
            carbon_intensity: float - in kg/kWh or equivalently T/MWh
            timestep_hrs: float - the system timestep in hours
            ramp_time_mins: float - the ramp-time to full power. Model will linearly
                ramp to this.
        """
        return txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_config_spec(self) + [
            ('tech_type', None, 'generic_slow_thermal'),
            ('detail_type', None, 'generic_slow_thermal'),
            ('site_index', int, 0),
            ('fuel_price_mwh', float, None),
            ('carbon_price_m', float, None),
            ('carbon_intensity', float, None),
            ('ramp_time_mins', float, None),
            ('timestep_hrs', float, None)
            ]


    def complete_configuration_pre_expand(self):
        """Complete the configuration by setting the param-site map and pre-calculating the
        fuel cost in $m/mwh.
        """
        
        txmultigeneratormultisite.TxMultiGeneratorMultiSite.complete_configuration_pre_expand(self)
        
        if isinstance(self.config['site_index'], dict):
            msg = ('In model ' + self.config['model'] + 
                ', the site_index parameter must not vary with time.')
            raise mureilexception.ConfigException(msg, {})
            
        self.params_to_site = numpy.array([self.config['site_index']])
        
        fuel_price = self.config['fuel_price_mwh']
        if isinstance(fuel_price, dict):
            self.config['fuel_price_mwh_m'] = fpm = {}
            for key, value in fuel_price:
                fpm[key] = value / 1e6
        else:
            self.config['fuel_price_mwh_m'] = fuel_price / 1e6
        

    def calculate_outputs_and_costs(self, state_handle, supply_request, max_supply=[], price=[]):
        """Implement calculate_outputs_and_costs as defined by TxMultiGeneratorBase, for the 
        slow-thermal model.

        Calculate the supply output of each site at each point in the timeseries. Return
        a set of timeseries of supply. Also calculate, for the length of time
        represented by the timeseries length, the variable cost (fuel, maintenance etc)
        for each site, and the carbon emissions.
        """
        
        cap_list = state_handle['capacity']
        site_indices = self.get_site_indices(state_handle)
        num_sites = len(site_indices)

        if num_sites > 1:
            raise mureilexception.MureilException(
                'TxMultiInstantOptimsableThermal class handles only one site.', {})

        supply = numpy.zeros((num_sites, len(supply_request)))
        vble_cost = numpy.zeros(num_sites)
        carbon = numpy.zeros(num_sites)
        
        this_conf = self.period_configs[state_handle['curr_period']]

        ### TODO: This model only handles a single site
        ### and assumes identical performance from all capacity regardless of age
        
        if num_sites > 0:
            j = 0
            site = site_indices[j]
            capacity = sum([tup[0] for tup in cap_list[site]])
            ramp_time_mins = this_conf['ramp_time_mins']
 
            therm_out = 0 # initial thermal output assumed zero
            max_grad = capacity/(ramp_time_mins/60) # max response gradient
           
            max_inc = max_grad * this_conf['timestep_hrs'] # max inc/dec based on ramp
 
            for i in range(len(supply_request)):
                des_inc = supply_request[i] - therm_out # desired increase to meet rem_demand if no ramp limit
                if abs(des_inc) <= max_inc: # if the inc/dec in demand is less than max ramp
                    therm_out =  therm_out + des_inc 
                else:  # the inc/dec in demand is greater than max ramp
                    therm_out = therm_out + max_inc * cmp(des_inc,0)

                if therm_out > capacity: # if calc ramped output greater than capacity 
                    therm_out = capacity # limit to max capacity
                if therm_out < 0: # if calc ramped output less than zero
                    therm_out = 0 # limit to  zero

                supply[j,i] = therm_out

            total_supply = numpy.sum(supply[j,:])
            vble_cost[j] = numpy.sum(supply[j,:]) * this_conf['timestep_hrs'] * (
                this_conf['fuel_price_mwh_m'])

            ### TODO - this could use the full set of carbon intensity values over time.
            ### Here it assumes that all capacity, regardless of when it was built, has
            ### the same carbon intensity as the current period. 
            ### This would require allocating the supply to
            ### capacity from each period in turn, ordering by carbon intensity.
            carbon[j] = (total_supply * this_conf['carbon_intensity'] *
                this_conf['timestep_hrs'])
        
        return supply, vble_cost, carbon, {}
        

    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined by TxMultiGeneratorBase.
        """
        if len(results['capacity']) == 0:
            cap = 0
        else:
            cap = results['capacity'][0]

        return 'Slow Fossil Thermal, type ' + self.config['detail_type'] + ', optimisable, capacity (MW) {:.2f}'.format(
            cap)

        
    def get_full_desc_string(self, results, state_handle):
        """Implement get_full_desc_string as defined by TxMultiGeneratorBase.
        """
        return self.get_simple_desc_string(results, state_handle)


class TxMultiSlowFixedThermal(TxMultiSlowOptimisableThermal):
    """A slow-response thermal generator, that can be set up with
    startup data but which does not take an optimisable param for
    capacity increase. This implementation handles only one site.
    """
    
    def get_param_count(self):
        """This generator takes no parameters.
        """
        return 0
        

    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined by TxMultiGeneratorBase.
        """
        if len(results['capacity']) == 0:
            cap = 0
        else:
            cap = results['capacity'][0]

        return 'Slow Fossil Thermal, type ' + self.config['detail_type'] + ', fixed, capacity (MW) {:.2f}'.format(
            cap)
    