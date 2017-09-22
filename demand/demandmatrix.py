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

"""Implements a simple wrapper to hold demand data for multiple nodes. For
multi-period simulations, applies a simple scaling factor as configured.
"""

from tools import mureilexception
from tools import configurablebase

import numpy
import copy

class DemandMatrix(configurablebase.ConfigurableMultiBase):
    """Hold a matrix of demand timeseries for a set of nodes. Apply a simple
    scaling factor for multi-period simulations.
    """

    def __init__(self):
        configurablebase.ConfigurableMultiBase.__init__(self)


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            data_name: The name of the data series that represents the set of demand timeseries.
            node_list_name: The name of the data series that contains the list of node names
                corresponding to the timeseries. If read from a CSV using the ncdata class,
                this will be 'data_name'_hdr.
            bid_price: The bid price for the demand, here a single figure in $/MWh, one per
                decade if desired.
            scale: float, default 1 in all periods. A multiplier on the timeseries value to 
                represent increase or decrease in demand in a future time period.
        """
        return [
            ('data_name', None, None),
            ('node_list_name', None, None),
            ('bid_price', float, None),
            ('scale', float, 1.0)
            ]


    def get_data_types(self):
        """Return a list of keys for each type of data required. Here, return
        the site_to_distance_map_name.
        """

        return [self.config['data_name'], self.config['node_list_name']] 


    def set_data(self, data):
        """Save the data and the node list.
        """
        
        self.data = data[self.config['data_name']]
        self.node_list = data[self.config['node_list_name']]


    def get_node_names(self):
        """Return the list of node names where demand data is provided.
        """
        
        return self.node_list
        
    
    def get_data(self, period):
        """Return the data matrix corresponding to the node names, for the
        given period. Multiply the configured data matrix by the scale
        value for the given period.
        
        ### TODO ### This should be precalculated.
        """
        
        scale_f = self.period_configs[period]['scale']
        
        if scale_f == 1:
            return self.data
        else:
            return self.data * scale_f
        
    
    def get_bid_prices(self, period):
        """Return the bid price for the given period.
        This version just returns the same price for all nodes.
        The bid prices are output in the same order as the nodes in
        get_node_names().
        """
        
        return numpy.ones(len(self.node_list)) * self.period_configs[period]['bid_price']
        
            
