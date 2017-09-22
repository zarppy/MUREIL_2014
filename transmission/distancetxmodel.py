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

"""Implements a very simple transmission model that calculates a transmission
cost based on the distance to the nearest trunk line.
"""

from tools import mureilexception
from tools import configurablebase

import numpy
import copy

class DistanceTxModel(configurablebase.ConfigurableMultiBase):
    """Model a transmission system by simply adding up the cost of
    connecting the active generation sites to the nearest trunk line.
    """

    def __init__(self):
        """Initialise the starting state of the transmission model to empty.
        TODO this needs a starting state function
        """
        configurablebase.ConfigurableMultiBase.__init__(self)

        self.startup_state = {}
 

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            site_to_distance_map_name: The name of the data series that represents the
                map between the site index and the distance in km. The data series is a
                n by 2 array [[site_index, distance]]
            cost_per_km: The cost in $M per km of distance to nearest trunk line.
        """
        return [
            ('site_to_distance_map_name', None, None),
            ('cost_per_km', float, None)
            ]


    def get_startup_state_handle(self):
        """Return a copy of the startup state, for use as the state_handle.
        """

        return copy.deepcopy(self.startup_state)


    def calculate_cost(self, state_handle, period, site_indices):
        """Calculate the cost of adding new transmission connections to the network,
        from the list of active sites provided.
        
        Inputs:
            state_handle: The state_handle, as returned by get_startup_state.
            site_indices: A list of sites requiring transmission connections, 
                which may include duplicates.

        Outputs:
            cost: The cost in $M for building the new transmission.
        """
        curr_conf = self.period_configs[period]

        uniq_sites = list(set(site_indices))

        cost = 0.0
        for site in uniq_sites:
            try:
                cost += self.dist_map[site] * curr_conf['cost_per_km']
            except KeyError:
                raise mureilexception.ConfigException(
                    'Site ' + str(site) + ' is not in transmission map.', {})

        return cost


    def get_data_types(self):
        """Return a list of keys for each type of data required. Here, return
        the site_to_distance_map_name.
        """

        return [self.config['site_to_distance_map_name']] 


    def set_data(self, data):
        """Save the site to distance map.
        """

        dist_map = data[self.config['site_to_distance_map_name']]

        self.dist_map = {}
        for i in range(dist_map.shape[0]):
            self.dist_map[dist_map[i, 0]] = dist_map[i, 1]

        ### These are set as defaults by some sites. The -1 is from the missed supply.
        if 0 not in self.dist_map:
            self.dist_map[0] = 0

        if -1 not in self.dist_map:
            self.dist_map[-1] = 0



        
