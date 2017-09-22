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
import abc

class InterfaceDispatcher(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
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
        pass


class InterfaceSemiScheduledDispatch(InterfaceDispatcher):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def get_offers_semischeduled(self, state_handle, ts_length):
        """Calculate the offer quantity for each timestep. Calculate the offer price
        applicable to all timesteps.
        
        Inputs:
            state_handle
                as for calculate_time_period_full in txmultigeneratorbase.py
            ts_length: the data series length
        
        Outputs:
            site_indices: the identifying indices of each site with active capacity. All lists of
                    sites below will correspond with this list.
            offer_price: the offer price, one per site (interpreted as same for all timesteps)
            quantity: the offer quantity, one timeseries per site, in MW.
        """
        pass


class InterfaceInstantDispatch(InterfaceDispatcher):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def get_offers_instant(self, state_handle):
        """Calculate the offer quantity applicable to all timesteps. Calculate the offer price
        applicable to all timesteps.
        
        Inputs:
            state_handle
                as for calculate_time_period_full in txmultigeneratorbase.py
        
        Outputs:
            site_indices: the identifying indices of each site with active capacity. All lists of
                    sites below will correspond with this list.
            offer_price: the offer price, one per site (interpreted as same for all timesteps)
            quantity: the offer quantity, one value per site, in MW (interpreted as same for all timestamps).
                This is typically the capacity.
        """
        pass


class InterfaceRampDispatch(InterfaceDispatcher):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def get_offers_ramp(self, state_handle):
        """Calculate the offer quantity minimum and maximum and the ramp rate. Calculate the offer price
        applicable to all timesteps.
        
        Inputs:
            state_handle
                as for calculate_time_period_full in txmultigeneratorbase.py
        
        Outputs:
            site_indices: the identifying indices of each site with active capacity. All lists of
                    sites below will correspond with this list.
            offer_price: the offer price, one per site (interpreted as same for all timesteps)
            min_quantity: the minimum offer quantity, one value per site, in MW.
            max_quantity: the maximum offer quantity, one value per site, in MW.
            ramp_rate_up: the ramp rate when increasing output, one value per site, in MW/timestep.
            ramp_rate_down: the ramp rate when decreasing output, one value per site, in MW/timestep
        """
        pass


class InterfaceTransmission(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
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
        pass
        

    @abc.abstractmethod
    def get_site_to_node_map(self):
        """Return a dict mapping site index to node name.
        ## TODO ## complete the doc
        """
        pass


    @abc.abstractmethod
    def get_grid(self, period):
        """Return the grid object, for the given period.
        ## TODO ## complete the doc
        """
        pass

