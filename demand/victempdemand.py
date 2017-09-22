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
"""

from generator import singlepassgenerator
import numpy as np

class VicTempDemand(singlepassgenerator.SinglePassGeneratorBase):
    """The base class for generic generators that calculate the
    output and cost based on the full timeseries in one pass. 
    """
    
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
            
        """        
        
        return [
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
            ("year", None, "2010")
            ]

        
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        This function is required to be thread-safe (when save_result is False) to allow 
        multiprocessing.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation.
            output: numpy.array - a time series of the power output in MW
                from this generator.
        """
        
        # merge together the different factors into 4 different overall effects
        # this need to be refined to be more realistic (one day)
        total_efficiency = self.config['residential_efficiency'] + \
                           self.config['commercial_efficiency'] + \
                           self.config['grid_efficiency'] + \
                           self.config['grid_house_design_efficiency'] + \
                           self.config['grid_new_appliance_use']

        total_d_reduction = self.config['residential_intelligence_transmission'] + \
                            self.config['residential_micro_grids'] + \
                            self.config['residential_medium_scale_distributed'] + \
                            self.config['commercial_cogen_trigen'] + \
                            self.config['grid_small_scale_solar_pv'] + \
                            self.config['commercial_cogen_trigen']

        total_design = self.config['commercial_building_design'] + \
                       self.config['grid_house_design_efficiency']

        total_dsm = self.config['residential_demand_management'] + \
                    self.config['residential_storage'] + \
                    self.config['commercial_storage']  + \
                    self.config['commercial_peak_curtailment'] + \
                    self.config['grid_demand_management'] + \
                    self.config['grid_storage']

        # scale the totals to be out of 1
        total_efficiency =  total_efficiency/500.0
        total_d_reduction = total_d_reduction/600.0
        total_design = total_design/200.0
        total_dsm = total_dsm/600.0

        weatherfac = self.config['weatherfac'] * (1 - total_design)
        
        model, error = self.bottom_up(weatherfac)

        industry    = model['industry']
        residential = model['residential']
        commercial  = model['commercial']

        # DEMAND SHAPING
        shapediff = self.demandshape(model, 20*total_dsm)
        # EFFICIENCY
        industry   = industry   - 1.0 * total_efficiency
        commercial = commercial - 1.0 * total_efficiency
        # DEMAND REDUCTION
        model_pred = industry + residential + commercial - \
                     shapediff - 1.0*total_d_reduction
        
        # Convert from GW to MW
        model_pred *= 1000
        
        output = -model_pred
        cost = 0
        
        if (save_result):
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = max(model_pred)
            self.saved['other'] = {'ts_demand': -1 * output}
        
        return cost, output


    def bottom_up(self, weatherfac):

        #increases in demand in 2010,2020,2030,2040,2050
        runyear_fac = {'2010':1.0,'2020':1.2,'2030':1.4,'2040':1.6,'2050':1.8}
        timestep = self.config['timestep_hrs']
        
        # the calculations below are based on a half-hourly timestep.
        # use this to adjust the slope factors
        timestep_adj = timestep / 0.5

        error       = 0.0
        t_step      = int(24/timestep)
        industry    = [2.94 for i in self.ts_demand_in]
        industry    = np.array(industry)

        awake = np.zeros(t_step)
        for i in range(t_step):
            if i < self.config['wakeup']:
                awake[i] = 0.1
            elif i < (self.config['wakeup'] + (3/timestep)):
                awake[i] = 0.1 + (i-self.config['wakeup'])*(0.15 * timestep_adj)
            elif i < self.config['sleep']:
                awake[i] = 1.0
            else:
                awake[i] = 1.0 - (i-self.config['sleep'])*(0.075 * timestep_adj)

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

        tdiff        = self.config['ambient'] - self.ts_temperature
        teffect      = (abs(tdiff)/10)**(self.config['weatherpow'])

        commercial   = (self.config['background']/2 + 
                        business_rep * self.config['businessfac'] + 
                        teffect * weatherfac/2)
                        
        residential  = (self.config['background']/2 + 
                        awake_rep * self.config['resifac'] + 
                        teffect * weatherfac/2)

        industry     = industry    * runyear_fac[self.config['year']]
        residential  = residential * runyear_fac[self.config['year']]
        commercial   = commercial  * runyear_fac[self.config['year']]

        model        = {'industry':industry,'residential':residential,\
                        'commercial': commercial}
        model_pred   = industry + residential + commercial

        error = error + sum(abs(self.ts_demand_in/1000.0 - model_pred))\
            + abs(5000 - 5000*sum(commercial)/sum(residential))

        return model, error


    def demandshape(self, model, target):

        demand = model['industry'] + model['residential'] + model['commercial']
        shapediff = np.zeros(self.ts_time.shape)
        t_step    = int(24/self.config['timestep_hrs'])
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

    
    def interpret_to_string(self):
        """Return a string that describes the generator type and the
        current capacity, following a call to calculate_cost_and_output
        with set_current set.
        """
        return "Victorian temperature demand model"
        
        
    