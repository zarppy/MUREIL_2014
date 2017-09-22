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

"""Holds data on the transmission grid for the dispatcher engine. Also calculates
the cost of connecting the generation sites to the nodes in the transmission grid.
This model does not allow the transmission grid to change. ### TODO ### the model
does not remember previous site-node connection state for multi-period sim.
"""

from tools import mureilexception
from tools import configurablebase

from transmission import grid_data_loader
from tools import mureilbuilder

from master import interfacesflowmaster

import numpy
import copy

class TxGrid(configurablebase.ConfigurableMultiBase, interfacesflowmaster.InterfaceTransmission):
    """Hold data on the transmission grid for the dispatcher. Calculate the cost of
    connecting generation sites to transmission nodes.
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
            site_filename: The name of the CSV file with format site_index, node_name, connection_cost
                as the header, with site_index matching the site_index values for the generators, 
                node_name matching the node names in the grid, and connection cost in $/kW for connection
                of site to node.  ## TODO ## this could be done as a data object instead
            grid_input_dir: The directory to find the grid filenames in, relative to where the sim is run from
            grid_filenames: The set of names of csv files, 4 strings - e.g. 'nodes.csv', 'lines.csv',
                'shift_factors.csv', 'admittance.csv', in that order. (These are the default)
            grid_remove_slack_nodes: Boolean, default False
        """
        return [
            ('site_filename', None, None),
            ('grid_input_dir', None, './'),
            ('grid_filenames', mureilbuilder.make_string_list, 'nodes.csv lines.csv shift_factors.csv admittance.csv'),
            ('grid_remove_slack_nodes', mureilbuilder.string_to_bool, 'False')
            ]


    def get_startup_state_handle(self):
        """Return a copy of the startup state, for use as the state_handle.
        """

        return copy.deepcopy(self.startup_state)


    def calculate_connection_cost(self, state_handle, site_indices, site_capacity, 
        site_new_capacity):
        """Calculate the cost of adding new transmission connections to the network,
        from the list of active sites provided.
        
        Inputs:
            state_handle: The state_handle, as returned by get_startup_state.
            site_indices: A list of sites requiring transmission connections, 
                which may include duplicates.
            site_capacity: A list of installed capacity in MW at each site, corresponding to
                site_indices.
            site_new_capacity: A list of new installed capacity, a list of tuples
                of (site_index, new_capacity, cost)  (cost is ignored)

        Outputs:
            cost: The cost in $M for building the new transmission.
        """
    
        # This is a very simple calculation that charges for the connection
        # as the site_connection_cost * new_capacity at the site. 
        cost = 0.0
        
        # site_connection_cost is $M/MW
        # new_capacity is in MW
        # output is in $M
        
        for (site_index, new_capacity, dummy) in site_new_capacity: 
            cost += (self.site_connection_cost[site_index] *
                new_capacity)

        return cost
        

    def get_data_types(self):
        """Return a list of keys for each type of data required.
        TODO - currently done as csv hard-code)
        """

        return [] 


    def set_data(self, data):
        """Save the data (TODO - currently done as csv hard-code)
        """
    
    def get_site_to_node_map(self):
        """Return a dict mapping site index to node name.
        """
        return self.site_to_node
    
    
    def get_grid(self, period):
        """Return the grid object, for the given period.
        ### TODO - multi-period unimplemented
        """
        return self.grid
    
    
    def complete_configuration_post_expand(self):
        """Read in the grid information and site->node information.
        """
        
        self.grid = grid_data_loader.Grid()
        self.grid.load(self.config['grid_input_dir'],
            self.config['grid_filenames'], self.config['grid_remove_slack_nodes'])

        self.nodes = []
        for node in self.grid.nodes:
            self.nodes.append(node['name'])    

        # and the site->node map - just a simple CSV read - would be neater
        # to integrate this into the data system as it refers to generator indices.
        
        import csv
        # both site_to_node and site_connection_cost are dicts on site_index
        self.site_to_node = {}
        self.site_connection_cost = {}
        
        with open(self.config['site_filename'], 'rU') as n:
            reader = csv.reader(n)
            for row in reader:
                if reader.line_num == 1:
                    continue
                else:
                    site_index = int(row[0])
                    node_name = row[1]                   
                    if node_name not in self.nodes:
                        msg = ('When reading in transmission configuration, node ' + node_name +
                            ' is mapped to a site index, but is not in grid.')
                        raise mureilexception.ConfigException(msg, {})

                    self.site_to_node[site_index] = node_name
                    self.site_connection_cost[site_index] = float(row[2])

       
        
        
        

        
