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

"""Module subclassing TxMultiGeneratorBase that provides an implementation for
multi-site generators. 
"""

from tools import mureilexception, mureilbuilder
import copy
import numpy
from generator import txmultigeneratorbase

import logging
logger = logging.getLogger(__name__)

class TxMultiGeneratorMultiSite(txmultigeneratorbase.TxMultiGeneratorBase):
    """Module subclassing TxMultiGeneratorBase that provides an implementation of
    state_handle and related handling functions for multi-site generators. 
    
    The 'capacity' term in state_handle is implemented as a dict with one item per site. 
    Each site item is a list of tuples containing (site_index,build_period,decommissioning_period),
    describing the set of installed capacity. 
    """
    
    def __init__(self):
        """Initialise as for the base class, and also initialise the params_to_site map.
        """
        
        txmultigeneratorbase.TxMultiGeneratorBase.__init__(self)

        # params_to_site maps the index in the params list to the site indices.
        self.params_to_site = []
        

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            time_period_yrs: float - the length of the time period in years
            time_scale_up_mult: float - the value to multiply non-discounted items,
                such as carbon emissions, by to account for a shorter dataset than the
                calculation period length.
            variable_cost_mult: as for time_scale_up_mult, but may include a factor for
                cost discounting.

            size: float, optional - relates param to new capacity

            carbon_price_m: float - carbon price in $M/tonne
            
            startup_data_name: string, optional - the name of the data array that contains
                data on startup capacities.
            startup_data_string: string, optional - a python format data array suitable for 
                input into set_startup_state, all on a single line.

            params_to_site_data_name: string, optional - the name of the data array that
                contains a list of how the input params list maps to site indices.
            params_to_site_data_string: list of integers, optional - the site indices, 
                listed separated by spaces, defining the site index corresponding to 
                each optimisation param, in order.

            vom: float, default 0 - variable operating and maintenance cost, in $/MWh, same for all sites

            capital_cost: float, default 0 - cost in $M per MW for new capacity.
            install_cost: float, default 0 - cost in $M per site, when site has an
                installation from this generator for the first time.

            decommissioning_cost: float, optional (default 0) - cost in $M per MW for 
                decommissioning.
            lifetime_yrs: float, default 20 - the time in years that new capacity lasts
        """
        return txmultigeneratorbase.TxMultiGeneratorBase.get_config_spec(self) + [
            ('variable_cost_mult', float, 1.0),
            ('time_scale_up_mult', float, 1.0),
            ('carbon_price_m', float, 0.0),
            ('startup_data_name', None, ''),
            ('startup_data_string', mureilbuilder.python_eval, 'None'),
            ('params_to_site_data_name', None, ''),
            ('params_to_site_data_string', mureilbuilder.make_int_list, ''),
            ('decommissioning_cost', float, 0),
            ('vom', float, 0),
            ('capital_cost', float, 0),
            ('install_cost', float, 0),
            ('time_period_yrs', float, None),
            ('lifetime_yrs', float, 20),
            ('size', float, 1.0),
            ('start_min_param', int, 1e20),
            ('start_max_param', int, 1e20),
            ('timestep_hrs', float, None)
            ]


    def complete_configuration_pre_expand(self):
        """Complete the configuration prior to expanding the
        period configs. 
        
        This implementation checks that the lifetime_yrs is a multiple
        of time_period_yrs, and sets the startup state and params_to_site from the
        configuration strings.
        """
        
        time_period_yrs = self.config['time_period_yrs']
        lifetime_yrs = self.config['lifetime_yrs']
        error = None
        if isinstance(lifetime_yrs, dict):
            for value in lifetime_yrs.itervalues():
                div = value / time_period_yrs
                if not (float(int(div)) == div):
                    error = value
        else:
            div = lifetime_yrs / time_period_yrs
            if not (float(int(div)) == div):
                error = lifetime_yrs
        
        if error is not None:
            msg = ('In section ' + self.config['section'] + ', lifetime_yrs = ' +
                str(error) + ' which is required to be a multiple of time_period_yrs of ' +
                str(time_period_yrs))
            raise mureilexception.ConfigException(msg, {})

        # Set the startup state and the params to site from the configuration strings.
        if self.config['startup_data_string'] is not None:
            self.set_startup_state(self.config['startup_data_string'])
        
        if len(self.config['params_to_site_data_string']) > 0:
            self.params_to_site = self.config['params_to_site_data_string']
                

    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        data_types = []
        
        if len(self.config['startup_data_name']) > 0:
            data_types.append(self.config['startup_data_name'])

        if len(self.config['params_to_site_data_name']) > 0:
            data_types.append(self.config['params_to_site_data_name'])
        
        return data_types
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.

        This implementation looks for the data types:
            self.config['startup_data_name']: Interpets this into
                the startup state, using the set_startup_state function.

            self.config['params_to_site_data_name']: Sets self.params_to_site
                to this.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        startup_data_name = self.config['startup_data_name']
        if (len(startup_data_name) > 0) and (startup_data_name in data):
            self.set_startup_state(data[startup_data_name])

        params_to_site_name = self.config['params_to_site_data_name']
        if (len(params_to_site_name) > 0) and (params_to_site_name in data):
            self.params_to_site = data[params_to_site_name]

        
    def set_startup_state(self, startup_data):
        """Set the startup state from the data provided. Sets 
        self.startup_state from this.
        
        Inputs:
            startup_data: An array of generators * 4:
                [[site_index, capacity, build_date, decommissioning_period],
                ...]
        """

        # Check if the startup data is empty. If so, just return.
        if len(startup_data) == 0:
            return

        # Find out which build periods are covered.
        startup_data = numpy.array(startup_data)
        if not (len(startup_data.shape) == 2):
            raise mureilexception.ConfigException('startup data array for module ' +
                self.config['section'] + ' is not rectangular.', {})
                
        if not (startup_data.shape[1] == 4):
            raise mureilexception.ConfigException('startup data array for module ' +
                self.config['section'] + ' shape ' + str(startup_data.shape) + 
                ' but (n, 4) is required.', {})

        self.extra_periods = map(int, 
            (list(set(startup_data[:,2].tolist() + self.extra_periods))))
        self.extra_periods.sort()

        # And insert each existing generator into the starting state.
        cap_list = self.startup_state['capacity']
        hist_list = self.startup_state['history']

        for i in range(startup_data.shape[0]):
            site_index = int(startup_data[i, 0])
            new_cap = startup_data[i, 1]
            period = int(startup_data[i, 2])
            decomm_date = int(startup_data[i, 3])

            new_entry = (new_cap, period, decomm_date)
            if decomm_date < self.run_periods[0]:
                logger.warning('Model in section ' + self.config['section'] +
                    ' adds startup capacity decommissioned at end of ' + decomm_date +
                    ' but the first run period is ' + self.run_periods[0] + 
                    ' so it has been removed from the startup state.')
                if site_index not in hist_list:
                    hist_list[site_index] = []
                hist_list[site_index].append(new_entry)
            else:
                new_entry = (new_cap, period, decomm_date)

                if site_index not in cap_list:
                    cap_list[site_index] = []
                cap_list[site_index].append(new_entry)


    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised, per time period.
        
        Outputs:
            param_count: non-negative integer - the number of
                parameters required per time period.
        """

        return len(self.params_to_site)
        
    
    def get_param_starts(self):
        """Return two nested lists - one for min, one max, for starting values for the
        params. Must be either [[]] or [len(run_periods),param_count].
        
        Outputs:
            min_start_list: list of param integers, or [[]]
            max_start_list: list of param integers, or [[]]
        """
    
        param_count = self.get_param_count()
        period_count = len(self.run_periods)
      
        if param_count > 0:
            if (self.config['start_min_param'] == 1e20):
                start_mins = [[]]
            else:
                start_mins = (numpy.ones((period_count, param_count)) * self.config['start_min_param']).tolist() 

            if (self.config['start_max_param'] == 1e20):
                start_maxs = [[]]
            else:
                start_maxs = (numpy.ones((period_count, param_count)) * self.config['start_max_param']).tolist() 
        else:
            start_mins = [[]]
            start_maxs = [[]]
            
        return start_mins, start_maxs
        
        
    def update_state_new_period_list(self, state_handle, period, new_capacity):
        """Implements update_state_new_period_list as defined in txmultigeneratorbase,
        for the state_handle format for this multi-site implementation.
        """

        state_handle['curr_period'] = period

        cap_list = state_handle['capacity']        

        for site_index, new_cap, decomm_date in new_capacity:
            site_index = int(site_index)
            
            new_entry = (new_cap, period, int(decomm_date))

            if site_index not in cap_list:
                cap_list[site_index] = []

            cap_list[site_index].append(new_entry)

        return None


    def update_state_new_period_params(self, state_handle, period, new_params):
        """Implements update_state_new_period_params as defined in txmultigeneratorbase,
        for the state_handle format for this multi-site implementation.
        
        Filters any negative new_params values to 0.
        """
            
        state_handle['curr_period'] = period
        curr_conf = self.period_configs[period]
        decomm_date = int(curr_conf['lifetime_yrs'] - curr_conf['time_period_yrs'] + period)
        
        cap_list = state_handle['capacity']        

        new_cap = numpy.array(new_params).clip(0) * curr_conf['size']

        for i in (numpy.nonzero(new_cap)[0]):
            site_index = self.params_to_site[i]
            new_entry = (new_cap[i], period, decomm_date)

            if site_index not in cap_list:
                cap_list[site_index] = []

            cap_list[site_index].append(new_entry)

        return None
 
    
    def calculate_update_decommission(self, state_handle):
        """Implements update_decommission as defined in txmultigeneratorbase,
        for the state_handle format for this multi-site implementation.
        """
        period = state_handle['curr_period']
        cap_list = state_handle['capacity']
        hist_list = state_handle['history']
    
        total_cost = 0.0
        sites = []
        cost = []
        decommissioned = []
        fully_decommissioned = []
    
        decomm_cost = self.period_configs[period]['decommissioning_cost']

        for site, site_caps in cap_list.iteritems():
            
            decomm = [tup for tup in site_caps if (tup[2] == period)]

            if len(decomm) > 0:
                sites.append(site)
                decom_cap = sum([tup[0] for tup in decomm])
                decommissioned.append(decom_cap)
                this_cost = decom_cap * decomm_cost
                cost.append(this_cost)
                total_cost += this_cost

                # add the decommissioned capacity to the 'history' list
                if not site in hist_list:
                    hist_list[site] = []
                hist_list[site] += decomm
                
                # and rebuild the list of what's left
                # note that the expression in here is the complement of that to compute
                # decomm above.
                new_list = [tup for tup in site_caps if not (tup[2] == period)]
                
                # if all capacity is gone from this site
                if len(new_list) == 0:
                    fully_decommissioned.append(site)
                else:
                    cap_list[site] = new_list
                
        for site in fully_decommissioned:
            del cap_list[site]
    
        return total_cost, zip(sites, decommissioned, cost)
 
 
    def calculate_new_capacity_cost(self, state_handle):
        """Implements calculate_new_capacity_cost as defined in TxMultiGeneratorBase,
        for the state_handle format for this multi-site implementation. Calculates
        the cost as a simple multiple of the new capacity size.
        """
        
        period = state_handle['curr_period']
        cap_list = state_handle['capacity']
        hist_list = state_handle['history']
    
        total_cost = 0.0
        sites = []
        cost = []
        new_capacity = []
        
        for site, value in cap_list.iteritems():
            try:
                hist = hist_list[site]
            except KeyError:
                hist = []

            this_cost, new_cap = self.calculate_capital_cost_site(
                (value, hist), period, site)

            if new_cap > 0:
                sites.append(site)
                new_capacity.append(new_cap)
                cost.append(this_cost)
                total_cost += this_cost
    
        return total_cost, zip(sites, new_capacity, cost)

 
    def calculate_capital_cost_site(self, site_data, period, site):
        """"Calculate the incremental capital cost incurred in this 
        period by the new capacity, for this site.
        
        This is a useful function for generators to override to implement
        cost functions that depend on the existing installed capacity. 

        This function charges a per-MW cost plus an install figure if all
        the current capacity is new, and the site has not been used before
        for this type of generator.
        
        Inputs: 
            site_data: a pair of lists - (current_capacity, history), each 
                a list of tuples of (capacity, build, decom) from the
                state_handle.
            period: the current period, an integer
            site: the site index
                
        Outputs:
            cost: the cost in $M of this new capacity
            new_capacity: the total new capacity installed at this site
        """
        
        new_cap_list = [tup[0] for tup in site_data[0] if (tup[1] == period)] 
        new_cap = sum(new_cap_list)

        capacity_cost = self.period_configs[period]['capital_cost']
        this_cost = new_cap * capacity_cost

        install_cost = self.period_configs[period]['install_cost']
        if install_cost > 0:
            # check if all the current capacity is new
            if len(new_cap_list) == len(site_data[0]):
                # and check if the site has been used before, ever
                if len(site_data[1]) == 0:
                    # the site is new, so charge the 'install' as well
                    this_cost += install_cost
    
        return this_cost, new_cap        
            
    
    def get_capacity(self, state_handle):
        """Implement the get_capacity function as defined in TxMultiGeneratorBase, for this
        multi-site implementation.
        """

        index_list = self.get_site_indices(state_handle)
        cap_list = state_handle['capacity']
        
        capacity = []

        for site in index_list:
            capacity.append(sum([tup[0] for tup in cap_list[site]]))
        
        return capacity

    
    def get_site_indices(self, state_handle):
        """Implement the get_site_indices function as defined in TxMultiGeneratorBase, for this
        multi-site implementation.
        """
        
        site_indices = state_handle['capacity'].keys()
        site_indices.sort()
        
        return site_indices


    def calculate_time_period_simple(self, state_handle, period, new_params, 
        supply_request, full_results=False):
        """Implement calculate_time_period_simple as defined in TxMultiGeneratorBase for
        the multi-site generator model.
        """
    
        curr_config = self.period_configs[period]

        # Update the state and get the calculations for each site
        self.update_state_new_period_params(state_handle, period, new_params)
        site_indices = self.get_site_indices(state_handle)
        capital_cost, new_capacity = self.calculate_new_capacity_cost(state_handle)
        supply_list, variable_cost_list, carbon_emissions_list, other_list = ( 
            self.calculate_outputs_and_costs(state_handle, supply_request))

        if full_results:
            capacity = self.get_capacity(state_handle)

        # Compute the total supply
        supply = numpy.sum(supply_list, axis=0)
        
        # Compute the total variable costs, including carbon cost, for the timeseries, scaled up
        cost = ((numpy.sum(variable_cost_list, axis=0) + 
            (numpy.sum(carbon_emissions_list, axis=0) * curr_config['carbon_price_m'])) * (
            curr_config['variable_cost_mult']))
                
        # Do the decommissioning
        decomm_cost, decommissioned = self.calculate_update_decommission(state_handle)

        # Add the capital and decommissioning costs
        cost += decomm_cost
        cost += capital_cost

        if not full_results:
            return site_indices, cost, supply

        if full_results:
            results = {}
            results['site_indices'] = site_indices
            results['cost'] = cost
            results['aggregate_supply'] = supply
            results['capacity'] = capacity
            results['decommissioned'] = decommissioned
            results['new_capacity'] = new_capacity
            results['supply'] = supply_list
            results['variable_cost_period'] = variable_cost_list * curr_config['variable_cost_mult']
            results['carbon_emissions_period'] = (carbon_emissions_list * 
                curr_config['time_scale_up_mult'])
            results['total_supply_period'] = (curr_config['time_scale_up_mult'] * numpy.sum(supply) *
                curr_config['timestep_hrs'])
            results['other'] = other_list
            results['desc_string'] = self.get_simple_desc_string(results, state_handle)

        return site_indices, cost, supply, results
    

    def calculate_time_period_full(self, state_handle, period, new_params, supply_request, 
        max_supply=[], price=[], make_string=False, do_decommissioning=True):
        """Implement calculate_time_period_full as defined in TxMultiGeneratorBase for
        the multi-site generator model.
        """
        
        results = {}
        self.update_state_new_period_params(state_handle, period, new_params)
        results['site_indices'] = self.get_site_indices(state_handle)
        results['capacity'] = self.get_capacity(state_handle)
        dummy, results['new_capacity'] = self.calculate_new_capacity_cost(state_handle)
        results['supply'], results['variable_cost_ts'], results['carbon_emissions_ts'], results['other'] = (
            self.calculate_outputs_and_costs(state_handle, supply_request, max_supply, price))
        if do_decommissioning:
            dummy, results['decommissioned'] = (
                self.calculate_update_decommissioning(state_handle))
        else:
            results['decommissioned'] = []

        if make_string:
            results['desc_string'] = self.get_full_desc_string(results, state_handle)
        
        return results


    def recalculate_time_period_full(self, state_handle, results, supply_request, max_supply=[], price=[], make_string=False):
        """Implement recalculate_time_period_full as defined in TxMultiGeneratorBase for
        the multi-site generator model.
        """

        results['supply'], results['variable_cost_ts'], results['carbon_emissions_ts'], results['other'] = (
            self.calculate_outputs_and_costs(state_handle, supply_request, max_supply, price))

        if make_string:
            results['desc_string'] = self.get_full_desc_string(results, state_handle)
            return results
        else:
            return results        


    def calculate_costs_from_schedule_and_finalise(self, state_handle, schedule, make_string=False): 
        """Calculate the costs, given the schedule from the dispatcher.
        Finalise the decommissioning for that period.
        This assumes that update_state_new_period_params has been called previously,
        and the offer quantities have been determined for the active sites.
        
        Inputs:
            state_handle: 
                as for calculate_time_period_full in txmultigeneratorbase.py
            schedule: a set of timeseries for each active site, as previously
                listed in the call to get_offers_* 
        
        Outputs:
                as for calculate_time_period_full in txmultigeneratorbase.py
        """
        results = {}
        site_indices = self.get_site_indices(state_handle)
        results['site_indices'] = site_indices
        results['capacity'] = self.get_capacity(state_handle)
        results['new_capacity_total_cost'], results['new_capacity'] = self.calculate_new_capacity_cost(state_handle)
        results['supply'] = schedule
        results['variable_cost_ts'], results['carbon_emissions_ts'], results['other'] = (
            self.calculate_variable_costs(state_handle, site_indices, schedule))
        results['decomm_total_cost'], results['decommissioned'] = (
            self.calculate_update_decommission(state_handle))

        if make_string:
            results['desc_string'] = self.get_full_desc_string(results, state_handle)
        
        return results
        