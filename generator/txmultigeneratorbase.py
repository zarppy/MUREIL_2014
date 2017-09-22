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

"""Module with base class for generator objects that can work in a multi-timeperiod
system, and which fit in with a transmission model and economic model. 
"""

from tools import mureilexception
from tools import configurablebase
import copy

class TxMultiGeneratorBase(configurablebase.ConfigurableMultiBase):
    """An base class for generic generators 
    that work in a multi-timeperiod
    system and can work with a transmission model and economic model,
    with minimal implementation.
    """
    
    def __init__(self):
        """Intialise this model. Set an empty generic starting state.
        """
        configurablebase.ConfigurableMultiBase.__init__(self)
        self.startup_state = {
            'curr_period': None,
            'capacity': {},
            'history': {}
        }


    def get_details(self):
        """Return a list of flags indicating the properties of the generator.

        Outputs:
            flags: a dict with:
                dispatch: one of 'semischeduled', 'instant', 'ramp'
                technology: for use in aggregation later - what is the broad type
                    of generator - from e.g. 'wind', 'solar_pv', 'coal', 'gas' etc,
                    default 'generic'
                model_type: one of 'generator', 'demand_source',
                    'demand_management', 'missed_supply', default 'generator'
        """
        flags = {}
        flags['dispatch'] = 'instant'
        flags['technology'] = 'generic'
        flags['model_type'] = 'generator'
        
        return flags
        

    def get_startup_state_handle(self):
        """Return the starting state, in whatever form the model chooses, to be
        passed in at each iteration by the master. The deepcopy ensures it is 
        thread-safe as a separate copy is used for each master calculate call.
        
        Outputs:
            startup_state_handle: a new copy of the starting state of this model
        """
        return copy.deepcopy(self.startup_state)
    
    
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
        pass
            

    def set_startup_state(self, startup_data):
        """Setup the startup state from startup_data.
        
        Inputs:
            startup_data: whatever data type is implemented for this
                function by a subclass.
        """
        raise mureilexception.ProgramException(
            'Function set_startup_state called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')
        

    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised, per time period.
        
        Outputs:
            param_count: non-negative integer - the number of
                parameters required per time period.
        """
        return 0
        
    
    def get_param_starts(self):
        """Return two nested lists - one for min, one max, for starting values for the
        params. Must be either [[]] or the [len(run_periods), param_count]
        
        Outputs:
            min_start_list: list of param integers, or []
            max_start_list: list of param integers, or []
        """
        return [[]], [[]]
        
        
    def update_state_new_period_list(self, state_handle, period, new_capacity):
        """Update the 'state_handle' object, in place, with the new_capacity, which will
        list the new capacity built at that date, the location it is built, and the
        decommissioning date.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model before the current time period
            new_capacity: a list of tuples of (site_index, new_capacity, decommissioning_date)
            period: an integer identifying the period - e.g. 2010, 2020.
            
        Outputs:
            None, but the 'state_handle' input is modified in-place to now represent the state after this
            increment.
        """
        state_handle['curr_period'] = period


    def update_state_new_period_params(self, state_handle, period, new_params):
        """Update the 'state_handle' object, in place, with the new_params. Typically this would
        calculate the capacity (or other values) as dictated by the new_params, and
        add these to the state. 
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model before the current time period
            new_params: a numpy.array list of param numbers of length matching self.get_param_count
            period: an integer identifying the period - e.g. 2010, 2020.
            
        Outputs:
            None, but the 'state_handle' input is modified in-place to now represent the state after this
            increment.
        """
        state_handle['curr_period'] = period
 
    
    def calculate_update_decommission(self, state_handle):
        """Update the 'state_handle' object, in place, after decommissioning plants at the
        end of the current period. Calculate the cost of the decommissioning.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model after building new capacity in
                the current time period
            
        Outputs:
            total_cost: the total decommissioning cost across all sites.
            decommissioned: a list of tuples of (site_index, capacity, cost), describing the
                capacity decommissioned at the end of this period, and the cost of the 
                decommissioning.
            
            The 'state_handle' input is modified in-place to now represent the state after this
            increment.
        """
        return 0, []
        
 
    def calculate_new_capacity_cost(self, state_handle):
        """Calculate the capital cost of the infrastructure built in the latest period.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the current time period
                
        Outputs:
            total_cost: the sum of the new capacity costs across all sites
            new_capacity: a list of tuples of (site_index, new_capacity, cost), describing the
                capacity added at the start of this period.
        """
        return 0, []
 

    def calculate_capital_cost_site(self, site_data, period, site):
        """"Calculate the incremental capital cost incurred in this 
        period by the new capacity, for this site.
        
        This is a useful function for generators to override to implement
        cost functions that depend on the existing installed capacity. The
        implementation here simply multiplies by a capital cost per unit
        of new capacity.
        
        Inputs: 
            site_data: a single site's state from the state_handle.
            period: the current period, an integer
            site: the site index
                
        Outputs:
            cost: the cost in $M of this new capacity
            new_capacity: the total new capacity installed at this site
        """
        return 0, 0
        
        
    def calculate_dispatch_offer(self, period, param=None):
        """Calculate the dispatch offer (most simply, the SRMC) at this
        period for all sites in this model. 
        
        Inputs:
            period: the current period, an integer
            param: optional arbitrary parameters - for example may be used to
                   specify a level of current power to compute the SRMC.
                   
        Outputs:
            offer: the offer, in $/MWh
        """
        return 100000
        
        
    def get_capacity(self, state_handle):
        """Extracts from the 'state_handle' parameter the current total capacity at each active site.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            capacity: a list of the installed electrical capacity at each site for the active sites. This list will correspond
                to the list of site indices as returned by get_site_indices with the same state_handle.
        """
        return []

    
    def get_site_indices(self, state_handle):
        """Extracts from the 'state_handle' parameter the list of indices corresponding to sites
        with active capacity.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            site_indices: a list of identifying indices corresponding to sites with active capacity,
                in ascending order.
        """
        return []


    def calculate_variable_costs(self, state_handle, site_indices, schedule):
        """Calculate variable costs and carbon based on schedule.
        
        Inputs:
            state_handle
            site_indices
            schedule: The scheduled output, a set of timeseries
            
        Outputs:
            variable_cost, carbon, other
        """
        raise mureilexception.ProgramException(
            'Function calculate_variable_costs called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')


    def calculate_outputs(self, state_handle, ts_length):
        """Calculate the maximum outputs, before scheduling.
        
        Inputs:
            state_handle
            ts_length: an integer - the length of the timeseries
            
        Outputs:
            site_indices: the list of sites with active capacity
            output: a set of timeseries, corresponding to site_indices
        """
        raise mureilexception.ProgramException(
            'Function calculate_outputs called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')
        

    def calculate_outputs_and_costs(self, state_handle, supply_request, max_supply=[], price=[]):
        """Calculate the supply output of each site at each point in the timeseries. Return
        a set of timeseries of supply. Also calculate, for the length of time
        represented by the timeseries length, the variable cost (fuel, maintenance etc)
        for each site, and the carbon emissions.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the current time period
            supply_request: a timeseries indicating the total requested supply 
                for this generator
            max_supply: optional - a set of timeseries indicating any curtailing
                due to transmission restrictions.
            price: optional - a timeseries indicating the market price in $/MWh
            
        Outputs:
            All lists below will correspond to the list of site indices as returned by 
            get_site_indices with the same state_handle.
            
            supply: a set of timeseries, one per site, indicating output in MW at
                each timepoint in supply_request.
            variable_cost: a set of costs, one per site, in $M, for the timeseries length.
            carbon_emissions: a set of carbon emissions, one per site, in tonnes of CO2,
                for the timeseries length.
            other: an arbitrary dict, for extra information such as reliability.
        """
        raise mureilexception.ProgramException(
            'Function calculate_outputs_and_costs called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')
        
        
    def calculate_time_period_simple(self, state_handle, period, new_params, 
        supply_request, full_results=False):
        """Calculate, for this time period, the total supply of all sites in this model,
        and the total cost. This is for use in a simple dispatch model with copper-plated
        transmission.

        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model before the current time period
            period: an integer identifying the period - e.g. 2010, 2020.
            new_params: a list of param numbers of length matching self.get_param_count
            supply_request: a timeseries indicating the total requested supply 
                for this generator
            full_results: optional - if True, return a detailed results structure in addition

        Outputs:
            site_indices: the identifying indices of each site with active capacity. All lists of
                sites below will correspond with this list.
            cost: the total cost incurred in this period
            aggregate_supply: the total supply from all active sites in this model

            results: only returned if full_results is True. Returns a dict with items:
                site_indices: the identifying indices of each site with active capacity. All lists of
                    sites below will correspond with this list.
                cost: the total cost incurred in this period
                aggregate_supply: the total supply from all active sites in this model
                capacity: a list of the installed electrical capacity at each site.
                decommissioned: a list of tuples of (site_index, capacity, cost) - the capacity 
                    at each site that was decommissioned at the end of this period.
                new_capacity: a list of tuples of (site_index, capacity, cost) - the new capacity 
                    built at each site in this period.
                supply: a set of timeseries, one per site, indicating output in MW at
                    each timepoint in supply_request.
                variable_cost_period: a set of costs, one per site, in $M, for the period.
                carbon_emissions_period: a set of carbon emissions, one per site, in tonnes of CO2,
                    for the period, or empty list if none.
                total_supply_period: the total supply in MWh for the period from this generator
                other: an arbitrary dict, for extra information such as reliability.
                desc_string: a descriptive string on the current state and output
        """
        raise mureilexception.ProgramException(
            'Function calculate_time_period_simple called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')
    

    def get_simple_desc_string(self, results, state_handle):
        """Given the results dict as created by calculate_time_period_simple, prepare
        a descriptive string for printed output.
        
        Inputs:
            results: a results dict as output by calculate_time_period_simple.
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            desc_string: a descriptive string suitable for human reading.
        """
        return 'Generic generator'

 
    def calculate_time_period_full(self, state_handle, period, new_params, supply_request, 
        max_supply={}, price=[], make_string=False, do_decommissioning=True):
        """Calculate, for this time period, the supply from each site, the capacity at
        each site, the variable cost, capital cost and carbon emissions. Expose all of 
        the parameters and require the transmission and/or economic models to do the
        rest of the work.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model before the current time period
            period: an integer identifying the period - e.g. 2010, 2020.
            new_params: a list of param numbers of length matching self.get_param_count
            supply_request: a timeseries indicating the total requested supply 
                for this generator
            max_supply: optional - a set of timeseries indicating any curtailing
                due to transmission restrictions - as a dict of {site_index: timeseries}
            price: optional - a timeseries indicating the market price in $/MWh
            make_string: if True, return as the final output, a string describing the
                current state and outputs.
            do_decommissioning: if True, update to the state after decommissioning at the
                end of the period. Set to False if recalculate_time_period_full will be called.
            
        Outputs:
            results: a dict with all of the following values
                site_indices: the identifying indices of each site with active capacity. All lists of
                    sites below will correspond with this list.
                capacity: a list of the installed electrical capacity at each site.
                decommissioned: a list of tuples of (site_index, capacity, cost) - the capacity 
                    at each site that was decommissioned at the end of this period.
                new_capacity: a list of tuples of (site_index, capacity, cost) - the new capacity 
                    built at each site in this period.
                supply: a set of timeseries, one per site, indicating output in MW at
                    each timepoint in supply_request.
                variable_cost_ts: a set of costs, one per site, in $M, for the timeseries length.
                carbon_emissions_ts: a set of carbon emissions, one per site, in tonnes of CO2,
                    for the timeseries length, or empty list if none.
                other: an arbitrary dict, for extra information such as reliability.
                desc_string: a descriptive string on the current state and output, 
                    only returned if make_string in inputs is True.
        """
        raise mureilexception.ProgramException(
            'Function calculate_time_period_full called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')


    def recalculate_time_period_full(self, state_handle, results, supply_request, max_supply=[], price=[], make_string=False):
        """Recalculate as for calculate_time_period_full, but without updating the state first.
        Typically this would be used when iterating through a transmission model.

        calculate_time_period_full must be called first, with do_decommissioning set to False. Once the
        iterations are complete, calculate_update_decommissioning must be called to complete the 
        calculations for the period.

        This implementation below assumes that the decommissioning and capital costs are not dependent on
        supply_request, max_supply or price.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the current time period.
            results: the dict output from a run of calculate_time_period_full.
            supply_request, max_supply, price, make_string: as for calculate_time_period_full.
            
        Outputs:
            None - but the results input is updated in-place.
        """
        raise mureilexception.ProgramException(
            'Function recalculate_time_period_full called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')


    def calculate_costs_from_schedule_and_finalise(self, state_handle, schedule): 
        """Calculate the costs, given the schedule from the dispatcher.
        Finalise the decommissioning for that period.
        Inputs:
            state_handle: 
                as for calculate_time_period_full in txmultigeneratorbase.py
            schedule: a set of timeseries for each active site, as previously
                listed in the call to get_offers_* 
        
        Outputs:
                as for calculate_time_period_full in txmultigeneratorbase.py
        """
        raise mureilexception.ProgramException(
            'Function calculate_costs_from_schedule_and_finalise called by ' + self.__class__.name + 
            ', falling through to TxMultiGeneratorBase which does not provide an implementation.')


    def get_full_desc_string(self, results, state_handle):
        """Given the results dict as created by calculate_time_period_full, prepare
        a descriptive string for printed output.
        
        Inputs:
            results: a results dict as output by calculate_time_period_full.
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            desc_string: a descriptive string suitable for human reading.
        """
        return 'Generic generator'


    def get_terminal_value(self, period, state_handle):
        """Return the terminal value at each site, in $M, at the end of 'period',
        for the capacity in state_handle. Run this after decommissioning the last
        period of the run.
        
        Inputs:
            period: an integer identifying the period - e.g. 2010, 2020.
            state_handle: an arbitrary object, which initiated from self.get_startup_state_handle, 
                that describes the state of the generator model at the end of the time period of interest.

        Outputs:
            value: the total terminal value for these sites
            terminal_value: a list of tuples of (site_index, value) for sites with active capacity.
        """
        return 0, []
        