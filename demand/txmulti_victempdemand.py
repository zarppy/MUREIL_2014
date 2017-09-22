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

"""Module implementing bottom-up temperature-based demand model for Victoria.
Module for demand model using the TxMultiGeneratorBase base class.
"""


from generator import txmultigeneratorbase
import numpy as np

class VicTempDemand(txmultigeneratorbase.TxMultiGeneratorBase):
    """Module implementing bottom-up temperature-based demand model for Victoria.
    Module for demand model using the TxMultiGeneratorBase base class.
    """

    def get_details(self):
        """Return a list of flags indicating the properties of the generator,
        as defined in TxMultiGeneratorBase.
        """
        flags = txmultigeneratorbase.TxMultiGeneratorBase.get_details(self)
        flags['model_type'] = 'demand_source'

        return flags


    def get_site_indices(self, state_handle):
        """Implement get_site_indices as defined in TxMultiGeneratorBase. 
        
        Here a dummy 'site' of -1 is returned as the demand modelled here
        doesn't have a site.
        """
        return [self.config['site_index']] 

    
    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        return ['ts_temperature', 'ts_demand_in', 'ts_dow', 'ts_time']
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        self.ts_temperature = data['ts_temperature']
        self.ts_demand_in = data['ts_demand_in']
        self.ts_dow = data['ts_dow']
        self.ts_time = data['ts_time']
        

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            as for txmultigenerator.TxMultiGeneratorBase, plus:


        Configuration:
        ** RJD to add details of what these parameters actually mean.
            
        """        
        
        spec = txmultigeneratorbase.TxMultiGeneratorBase.get_config_spec(self) + [
            ("residential_efficiency", float, 0),
            ("residential_intelligence_transmission", float, 0),
            ("residential_micro_grids", float, 0),
            ("residential_medium_scale_distributed", float, 0),
            ("residential_demand_management", float, 0),
            ("residential_storage", float, 0),
            ("commercial_efficiency", float, 0),
            ("commercial_building_design", float, 0),
            ("commercial_process_design", float, 0),
            ("commercial_cogen_trigen", float, 0),
            ("commercial_demand_management", float, 0),
            ("commercial_storage", float, 0),
            ("commercial_peak_curtailment", float, 0),
            ("grid_efficiency", float, 0),
            ("grid_house_design_efficiency", float, 0),
            ("grid_new_appliance_use", float, 0),
            ("grid_small_scale_solar_pv", float, 0),
            ("grid_demand_management", float, 0),
            ("grid_storage", float, 0),
            ("grid_smart_meters", float, 0),
            ("ambient", float, 17.25),
            ("weatherpow", float, 1.5),
            ("wakeup", float, 10),
            ("sleep", float, 41),
            ("background", float, 1.5),
            ("businessfac", float, 1.125),
            ("weatherfac", float, 0.8),
            ("resifac", float, 0.875),
            ("timestep_hrs", float, None),
            ("site_index", int, None),
            ("demand_growth",float,'{2010:1.0, 2020:1.2, 2030: 1.4, 2040: 1.6, 2050: 1.8}'),
            ("variable_cost_mult", float, None),
            ("time_scale_up_mult", float, None)
            ]

        return spec

        
    def calculate_outputs_and_costs(self, state_handle, supply_request, max_supply=[], price=[]):
        """Implement calculate_outputs_and_costs as defined in TxMultiGeneratorBase.
        
        This model charges a fixed price per mwh of missed supply, which is any positive values
        in supply_request.
        """

        this_conf = self.period_configs[state_handle['curr_period']]

        
        # merge together the different factors into 4 different overall effects
        # this need to be refined to be more realistic (one day)
        total_efficiency = this_conf['residential_efficiency'] + \
                           this_conf['commercial_efficiency'] + \
                           this_conf['grid_efficiency'] + \
                           this_conf['grid_house_design_efficiency'] + \
                           this_conf['grid_new_appliance_use']

        total_d_reduction = this_conf['residential_intelligence_transmission'] + \
                            this_conf['residential_micro_grids'] + \
                            this_conf['residential_medium_scale_distributed'] + \
                            this_conf['commercial_cogen_trigen'] + \
                            this_conf['grid_small_scale_solar_pv'] + \
                            this_conf['commercial_cogen_trigen']

        total_design = this_conf['commercial_building_design'] + \
                       this_conf['grid_house_design_efficiency']

        total_dsm = this_conf['residential_demand_management'] + \
                    this_conf['residential_storage'] + \
                    this_conf['commercial_storage']  + \
                    this_conf['commercial_peak_curtailment'] + \
                    this_conf['grid_demand_management'] + \
                    this_conf['grid_storage']

        # scale the totals to be out of 1
        total_efficiency =  total_efficiency/500.0
        total_d_reduction = total_d_reduction/600.0
        total_design = total_design/200.0
        total_dsm = total_dsm/600.0

        ### TODO - does this weatherfac feed into the formula somewhere?
        weatherfac = this_conf['weatherfac'] * (1 - total_design)
        
        model, error = self.bottom_up(this_conf,weatherfac)

        industry    = model['industry']
        residential = model['residential']
        commercial  = model['commercial']

        # DEMAND SHAPING
        shapediff = self.demandshape(model,this_conf, 20*total_dsm)
        # EFFICIENCY
        industry   = industry   - 1.0 * total_efficiency
        commercial = commercial - 1.0 * total_efficiency
        # DEMAND REDUCTION
        model_pred = industry + residential + commercial - \
                     shapediff - 1.0*total_d_reduction
        
        # Convert from GW to MW
        model_pred *= 1000
        
        site_indices = self.get_site_indices(state_handle)
        num_sites = len(site_indices) 
        supply = np.zeros((num_sites, len(supply_request)))
        vble_cost = np.zeros(num_sites)
        carbon = np.zeros(num_sites)

        # The demand model implemented here only makes sense as a single 'site'.
        site = site_indices[0]
        supply[0,:] = -model_pred 
        vble_cost[0] = 0

        return supply, vble_cost, carbon, {'ts_demand': model_pred}


    def bottom_up(self,this_conf,weatherfac):

        timestep = this_conf['timestep_hrs']
        
        # the calculations below are based on a half-hourly timestep.
        # use this to adjust the slope factors
        timestep_adj = timestep / 0.5

        error       = 0.0
        t_step      = int(24/timestep)
        industry    = [2.94 for i in self.ts_demand_in]
        industry    = np.array(industry)

        awake = np.zeros(t_step)
        for i in range(t_step):
            if i < this_conf['wakeup']:
                awake[i] = 0.1
            elif i < (this_conf['wakeup'] + (3/timestep)):
                awake[i] = 0.1 + (i-this_conf['wakeup'])*(0.15 * timestep_adj)
            elif i < this_conf['sleep']:
                awake[i] = 1.0
            else:
                awake[i] = 1.0 - (i-this_conf['sleep'])*(0.075 * timestep_adj)

        if awake[-1] > 0.1:     # continue ramp down into the next morning
            ### TODO - is this calculation, and others, correct?
            isteps = ((awake[-1]-0.1)/0.075) / timestep_adj
            isteps = int(isteps)
            for i in range(isteps+1): awake[i] = awake[i-1]-(0.075 * timestep_adj)

        business = np.zeros(t_step)
        b_open   = int(8/timestep)
        b_close  = int(16/timestep)
        for i in range(t_step):
            if i < b_open:
                business[i] = 0.1
            elif i < (b_open+(3/timestep)):
                business[i] = 0.1 + (i-b_open)*(0.15 * timestep_adj)
            elif i < b_close:
                business[i] = 1.0
            elif i < (b_close+(3/timestep)):
                business[i] = 1.0 - (i-b_close)*(0.15 * timestep_adj)
            else:
                business[i] = 0.1

        ndays        = int(len(self.ts_demand_in)/t_step)
        awake_rep    = np.array([i for n in range(ndays) for i in awake])
        business_rep = np.array([i for n in range(ndays) for i in business])
        # dow == 0 represents "E"
        business_rep = np.where(self.ts_dow == 0, 
            np.ones(len(business_rep))*0.1, business_rep)

        tdiff        = this_conf['ambient'] - self.ts_temperature
        teffect      = (abs(tdiff)/10)**(this_conf['weatherpow'])

        commercial   = (this_conf['background']/2 + 
                        business_rep * this_conf['businessfac'] + 
                        teffect * weatherfac/2)
                        
        residential  = (this_conf['background']/2 + 
                        awake_rep * this_conf['resifac'] + 
                        teffect * weatherfac/2)

        industry     = industry    * this_conf['demand_growth']
        residential  = residential * this_conf['demand_growth'] 
        commercial   = commercial  * this_conf['demand_growth']

        model        = {'industry':industry,'residential':residential,\
                        'commercial': commercial}
        model_pred   = industry + residential + commercial

        error = error + sum(abs(self.ts_demand_in/1000.0 - model_pred))\
            + abs(5000 - 5000*sum(commercial)/sum(residential))

        return model, error


    def demandshape(self, model,this_conf, target):

        demand = model['industry'] + model['residential'] + model['commercial']
        shapediff = np.zeros(self.ts_time.shape)
        t_step    = int(24/this_conf['timestep_hrs'])
        ndays     = len(demand)/t_step

        for id in range(ndays):
            daydemand = demand[id*t_step:id*t_step+t_step].copy()

            # check the maximum available for load shaping

            demandmean  = sum(daydemand)/float(t_step)
            mean_filter = daydemand > demandmean
            totavail    = sum(daydemand[mean_filter] - demandmean)
            newtarget   = min(target, totavail)
            newdemand   = daydemand.copy()
            peak        = max(daydemand)
            mini        = min(daydemand)

            GWhsaved    = 0.0
            counter     = 1
            while GWhsaved <= newtarget:
                yval                  = peak - 0.1*counter
                GWh_filter            = daydemand > yval
                GWhsaved              = sum(daydemand[GWh_filter] - yval)
                newdemand[GWh_filter] = yval
                counter += 1

            counter   = 1
            GWhearned = 0.0
            while GWhearned <= GWhsaved:
                yval                  = mini + 0.1*counter
                GWh_filter            = daydemand < yval
                GWhearned             = sum(yval - daydemand[GWh_filter])
                newdemand[GWh_filter] = yval
                counter += 1

            shapediff[id*t_step:id*t_step+t_step] = daydemand-newdemand

        return shapediff

    
    def calculate_time_period_simple(self, state_handle, period, new_params,
        supply_request, full_results=False):
        """Implement calculate_time_period_simple as defined in TxMultiGeneratorBase for
        the Victorian demand model.
        
        This demand model does not handle any concept of capacity or site so returns
        empty lists for most things.
        """

        curr_config = self.period_configs[period]
        state_handle['curr_period'] = period

        # Update the state and get the calculations for each site
        site_indices = self.get_site_indices(state_handle)
        supply_list, variable_cost_list, dummy, other_list = (
            self.calculate_outputs_and_costs(state_handle, supply_request))
        supply = supply_list[0,:]

        # Compute the total variable costs - carbon emissions are zero for demand 
        cost = 0

        if not full_results:
            return site_indices, cost, supply

        if full_results:
            results = {}
            results['site_indices'] = site_indices 
            results['cost'] = cost
            results['aggregate_supply'] = supply
            results['capacity'] = [0]
            results['decommissioned'] = []
            results['new_capacity'] = []
            results['supply'] = supply_list
            results['variable_cost_period'] = variable_cost_list * curr_config['variable_cost_mult']
            results['carbon_emissions_period'] = np.array([0])
            results['total_supply_period'] = (curr_config['time_scale_up_mult'] * np.sum(supply) *
                curr_config['timestep_hrs'])
            results['other'] = other_list
            results['desc_string'] = self.get_simple_desc_string(results, state_handle)

        return site_indices, cost, supply, results


    def calculate_time_period_full(self, state_handle, period, new_params, supply_request,
        max_supply=[], price=[], make_string=False, do_decommissioning=True):
        """Implement calculate_time_period_full as defined in TxMultiGeneratorBase for
        the missed_supply model.
        
        This demand model does not handle any concept of capacity or site so returns
        empty lists for most things.
        """

        state_handle['curr_period'] = period
        results = {}

        results['supply'], results['variable_cost_ts'], results['carbon_emissions_ts'], results['other'] = (
            self.calculate_outputs_and_costs(state_handle, supply_request, max_supply, price))

        results['decommissioned'] = []
        results['site_indices'] = self.get_site_indices(state_handle) 
        results['capacity'] = [0]
        results['new_capacity'] = []

        if make_string:
            results['desc_string'] = self.get_full_desc_string(results, state_handle)
            return results


    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined in TxMultiGeneratorBase.
        """
        return "Victorian demand model"


    def get_full_desc_string(self, results, state_handle):
        """Implement get_full_desc_string as defined in TxMultiGeneratorBase.
        """
        return self.get_simple_desc_string(results, state_handle)
        
    
