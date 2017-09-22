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
"""Implements the BasicPumpedHydro class for with a TxMultiGeneratorMultiSite base.
"""

import numpy
import logging

from tools import mureilexception, mureilbuilder
from generator import txmultigeneratormultisite

logger = logging.getLogger(__name__)

class TxMultiBasicPumpedHydroOptimisable(txmultigeneratormultisite.TxMultiGeneratorMultiSite):
    """Class models a simple pumped hydro system that always pumps up when extra supply is available,
    and always releases when excess demand exists. The generator/pump electrical capacity is
    optimisable.
    """

    def complete_configuration_pre_expand(self):
        """Complete the configuration, and pre-calculate some values for improved performance.
        This simple model does not handle a changing pump round trip, water factor, etc,
        nor does it enforce consistency of water level between periods.
        """

        txmultigeneratormultisite.TxMultiGeneratorMultiSite.complete_configuration_pre_expand(self)

        self.params_to_site = numpy.array([self.config['site_index']])

        for param_name in ['pump_round_trip', 'starting_level', 'water_factor', 'dam_capacity']:
            if isinstance(self.config[param_name], dict):
                raise mureilexception.ConfigException('Model ' + self.config['model'] + 
                    ' does not support different values for parameter ' + param_name +
                    ' across different time periods.', {})
        
        # Check the pump_round_trip is <= 1
        if self.config['pump_round_trip'] > 1:
            msg = ('BasicPumpedHydro requires pump_round_trip to be less than 1. ' +
                ' Value = {:.3f}'.format(self.config['pump_round_trip']))
            logger.critical(msg) 
            raise mureilexception.ConfigException(msg, {})

        # Pre-calculate these for improved speed
        # Instead of calculating explicitly the water that's pumped up, calculate
        # the amount of electricity that's stored.
        # Adjust here for the timestep - elec_res is in units of MW-timesteps.
        # so 1 MWh = (60/timestep) MW-timesteps
        self.elec_res = (1 / self.config['timestep_hrs']) * (
            float(self.config['starting_level']) / float(self.config['water_factor']))
        self.elec_cap = (1 / self.config['timestep_hrs']) * (
            float(self.config['dam_capacity']) / float(self.config['water_factor']))
        self.pump_round_trip_recip = 1 / self.config['pump_round_trip']
        self.is_configured = True


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration: as for TxMultiGeneratorMultiSite, plus:
            tech_type: string - the generic technology type, to report in get_details() as technology.
            detail_type: string - a specific name, e.g. 'onshore_wind_vic', for printing in an output string
            site_index: integer - the index of the site where this pumped hydro is located
            ### TODO - should these be GL water? what are the units?
            dam_capacity: dam capacity in ML
            starting_level: starting level in ML
            water_factor: translation of MWh to ML - 1 MWh requires water_factor ML water
            pump_round_trip: efficiency of pump up / draw down operation, a proportion
            timestep_hrs: float - the system timestep in hours
        """
        return txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_config_spec(self) + [
            ('tech_type', None, 'hydro'),
            ('detail_type', None, 'pumped_hydro'),
            ('site_index', int, 0),
            ('dam_capacity', float, None),
            ('starting_level', float, None),
            ('water_factor', float, None),
            ('pump_round_trip', float, 0.8),
            ('timestep_hrs', float, None)
            ]
            

    def get_param_count(self):
        """Ask for 1 parameter to specify the electrical capacity to build.
        """
        return 1


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
                self.config['model'] + ' model handles only one site.', {})

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
            supply[j,:] = self.compute_pumped_hydro_ts(supply_request, capacity)

        return supply, vble_cost, carbon, {}


    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined by TxMultiGeneratorBase.
        """
        if len(results['capacity']) == 0:
            cap = 0
        else:
            cap = results['capacity'][0]

        return ('Basic Pumped Hydro, type ' + self.config['detail_type'] + 
            ', optimisable, capacity (MW) {:.2f}'.format(cap))

        
    def get_full_desc_string(self, results, state_handle):
        """Implement get_full_desc_string as defined by TxMultiGeneratorBase.
        """
        return self.get_simple_desc_string(results, state_handle)
   

    def compute_pumped_hydro_ts(self, rem_demand, max_gen):
        """Compute the timeseries for the pumped hydro operation.
        
        Inputs:
            rem_demand: timeseries of demand in MW remaining to be met, or surplus if negative
            max_gen: maximum electrical generation capacity
        
        Output:
            output: timeseries in MW of output of generator
        """
        
        output = numpy.zeros(len(rem_demand))
        elec_res_temp = self.elec_res
        gen = max_gen
        elec_cap = self.elec_cap
        pump_round_trip = self.config['pump_round_trip']
        pump_round_trip_recip = self.pump_round_trip_recip
        
        for i in range(len(rem_demand)):
            elec_diff = rem_demand[i]
            if elec_diff > 0:
                elec_to_release = elec_diff
                if elec_to_release > gen:
                    elec_to_release = gen
                if elec_to_release > elec_res_temp:
                    elec_to_release = elec_res_temp
                    elec_res_temp = 0
                else:
                    elec_res_temp -= elec_to_release
                output[i] = elec_to_release
            else:
                elec_to_store = -elec_diff
                if elec_to_store > gen:
                    elec_to_store = gen
                elec_to_store *= pump_round_trip
                if elec_to_store > elec_cap - elec_res_temp:
                    elec_to_store = elec_cap - elec_res_temp
                    elec_res_temp = elec_cap
                else:
                    elec_res_temp += elec_to_store
                elec_used = elec_to_store * pump_round_trip_recip
                output[i] = -elec_used

        return output
        

class TxMultiBasicPumpedHydroFixed(TxMultiBasicPumpedHydroOptimisable):
    """Class models a simple pumped hydro system that always pumps up when extra supply is available,
    and always releases when excess demand exists. The generator/pump electrical capacity is not
    optimisable by a param so must be set with a startup value.
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

        return ('Basic Pumped Hydro, type ' + self.config['detail_type'] + 
            ', fixed, capacity (MW) {:.2f}'.format(cap))

