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

"""Module for an instant-thermal model using the txmultigenerator base class.
"""

from tools import configurablebase, mureilexception
from generator import txmultigeneratormultisite
from master import interfacesflowmaster

import copy
import numpy


class TxMultiInstantOptimisableThermal(txmultigeneratormultisite.TxMultiGeneratorMultiSite,
    interfacesflowmaster.InterfaceInstantDispatch):
    """A simple implementation of an instant-output thermal generator, such
    as a peaking gas turbine, which requires an optimisation parameter. This
    implementation handles only one site.
    """

    def get_details(self):
        """Return a list of flags indicating the properties of the generator.
        """
        flags = txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_details(self)
        flags['dispatch'] = 'instant'
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
        """
        return txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_config_spec(self) + [
            ('tech_type', None, 'generic_instant_thermal'),
            ('detail_type', None, 'generic_instant_thermal'),
            ('site_index', int, 0),
            ('fuel_price_mwh', float, None),
            ('carbon_price_m', float, None),
            ('carbon_intensity', float, None),
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
        

    def calculate_dispatch_offer(self, period, param=None):
        """Calculate the dispatch offer in $/MWh based on the carbon intensity, fuel price and
        vom.
        """
        
        this_conf = self.period_configs[period]
        return (this_conf['fuel_price_mwh'] + this_conf['carbon_price_m'] * 1e6 * this_conf['carbon_intensity'] +
            this_conf['vom'])


    def get_offers_instant(self, state_handle):
        """Get offers for this instant generator.
        
        Outputs:
            site_indices: the identifying indices of each site with active capacity. All lists of
                    sites below will correspond with this list.
            offer_price: the offer price, one per site (interpreted as same for all timesteps)
            quantity: the offer quantity, one timeseries per site, in MW.
        """
        offer_price = self.calculate_dispatch_offer(state_handle['curr_period'])
        quantity = self.get_capacity(state_handle)
        site_indices = self.get_site_indices(state_handle) 

        return site_indices, offer_price, quantity


    def calculate_variable_costs(self, state_handle, site_indices, schedule):
        """Calculate variable costs and carbon based on schedule.
        
        Inputs:
            state_handle
            site_indices
            schedule: The scheduled output, a set of timeseries
            
        Outputs:
            variable_cost, carbon, other
        """
        num_sites = len(site_indices)
        vble_cost = numpy.zeros(num_sites)
        carbon = numpy.zeros(num_sites)
        
        this_conf = self.period_configs[state_handle['curr_period']]
        vom_m = this_conf['vom'] * 1e-6

        ### This model only handles a single site
        if num_sites > 0:
            i = 0
            site = site_indices[i]

            total_supply = numpy.sum(schedule[i,:])
            vble_cost[i] = numpy.sum(schedule[i,:]) * self.config['timestep_hrs'] * (
                this_conf['fuel_price_mwh_m'] + vom_m)

            ### TODO - this could use the full set of carbon intensity values over time.
            ### Here it assumes that all capacity, regardless of when it was built, has
            ### the same carbon intensity as the current period. 
            ### This would require allocating the supply to
            ### capacity from each period in turn, ordering by carbon intensity.
            carbon[i] = (total_supply * this_conf['carbon_intensity'] *
                self.config['timestep_hrs'])
        
        return vble_cost, carbon, {}


    def calculate_outputs_and_costs(self, state_handle, supply_request, max_supply=[], price=[]):
        """Implement calculate_outputs_and_costs as defined by TxMultiGeneratorBase, for the 
        instant-thermal model.

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

        ### This model only handles a single site
        if num_sites > 0:
            i = 0
            site = site_indices[i]
            capacity = [tup[0] for tup in cap_list[site]]
            max_cap = numpy.sum(capacity)
            supply[i,:] = supply_request.clip(0, max_cap)
        
        vble_cost, carbon, other = self.calculate_variable_costs(
            state_handle, site_indices, supply)

        return supply, vble_cost, carbon, {}
        

    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined by TxMultiGeneratorBase.
        """
        if len(results['capacity']) == 0:
            cap = 0
        else:
            cap = results['capacity'][0]

        return 'Instant Fossil Thermal, optimisable, max capacity (MW) {:.2f}'.format(
            cap)

        
    def get_full_desc_string(self, results, state_handle):
        """Implement get_full_desc_string as defined by TxMultiGeneratorBase.
        """
        return self.get_simple_desc_string(results, state_handle)


class TxMultiInstantFixedThermal(TxMultiInstantOptimisableThermal):
    """An instant-output thermal generator, that can be set up with
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

        return 'Instant Fossil Thermal, fixed, max capacity (MW) {:.2f}'.format(
            cap)
    

class TxMultiInstantMaxThermal(TxMultiInstantOptimisableThermal):
    """A simple implementation of an instant-output thermal generator, such
    as a peaking gas turbine, is built as big as necessary. This
    implementation handles only one site.
    """

    def get_param_count(self):
        """No optimisable parameters required for this model.
        """
        return 0
        
        
    def get_params_starts(self):
        """No optimisable parameters required for this model.
        """
        return [[]], [[]]


    def calculate_time_period_simple(self, state_handle, period, new_params, 
        supply_request, full_results=False):
        """Override calculate_time_period_simple to first determine what the
        capacity to install will be.
        """
        
        curr_conf = self.period_configs[period]
        
        req_capacity = numpy.max(supply_request)
        current_capacity = self.get_capacity(state_handle)
        
        if len(current_capacity) == 0:
            current_capacity = 0
        else:
            current_capacity = current_capacity[0]
        
        if (req_capacity > current_capacity):
            decomm_date = int(curr_conf['lifetime_yrs'] - curr_conf['time_period_yrs'] + period)
            new_cap = (self.config['site_index'], req_capacity - current_capacity, decomm_date)
            self.update_state_new_period_list(state_handle, period, [new_cap])
        
        return TxMultiInstantOptimisableThermal.calculate_time_period_simple(self,
            state_handle, period, new_params, supply_request, full_results)


    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined by TxMultiGeneratorBase.
        """
        if len(results['capacity']) == 0:
            cap = 0
        else:
            cap = results['capacity'][0]

        return 'Instant Fossil Max Thermal, max capacity (MW) {:.2f}'.format(
            cap)

        
    def get_full_desc_string(self, results, state_handle):
        """Implement get_full_desc_string as defined by TxMultiGeneratorBase.
        """
        return self.get_simple_desc_string(results, state_handle)
