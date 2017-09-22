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
import numpy
import time
import logging
import copy
from os import path
import json

from tools import mureilbuilder, mureilexception, mureiloutput, mureiltypes, globalconfig
from tools import mureilbase, configurablebase

from generator import txmultigeneratorbase

logger = logging.getLogger(__name__)

class GeTxMultiMaster(mureilbase.MasterInterface, configurablebase.ConfigurableMultiBase):
    def get_full_config(self):
        if not self.is_configured:
            return None
        
        # Will return configs collected from all objects, assembled into full_config.
        full_conf = {}
        full_conf['Master'] = self.config
        full_conf[self.config['data']] = self.data.get_config()
        full_conf[self.config['global']] = self.global_config

        for gen_type in self.dispatch_order:
            full_conf[self.config[gen_type]] = self.gen_list[gen_type].get_config()

        return full_conf

     
    def set_config(self, full_config, extra_data):
    
        # Master explicitly does not copy in the global variables. It is too confusing
        # to combine those with flags, defaults and values defined in the config files.
        self.load_initial_config(full_config['Master'])
        
        # Get the global variables
        mureilbuilder.check_section_exists(full_config, self.config['global'])
        if 'model' not in full_config[self.config['global']]:
            full_config[self.config['global']]['model'] = 'tools.globalconfig.GlobalBase'
        self.global_calc = mureilbuilder.create_instance(full_config, None, self.config['global'], 
            mureilbase.ConfigurableInterface)    
        self.global_config = self.global_calc.get_config()

        # Now check the dispatch_order, to get a list of the generators
        for gen in self.config['dispatch_order']:
            self.config_spec += [(gen, None, None)]

        self.update_from_config_spec()
        self.check_config()
        
        self.dispatch_order = self.config['dispatch_order']
        
        # Set up the data class and get the data, and compute the global parameters
        self.data = mureilbuilder.create_instance(full_config, self.global_config, self.config['data'], 
            mureilbase.DataSinglePassInterface)
        self.global_calc.update_config({'data_ts_length': self.data.get_ts_length()})
        self.global_calc.post_data_global_calcs()
        self.global_config = self.global_calc.get_config()

        # Instantiate the transmission model
        if self.config['transmission'] in full_config:
            self.transmission = mureilbuilder.create_instance(full_config, self.global_config, 
                self.config['transmission'], configurablebase.ConfigurableMultiBase,
                self.config['run_periods'])
            mureilbuilder.supply_single_pass_data(self.transmission,
                self.data, self.config['transmission'])
        else:
            self.transmission = None
        
        # Instantiate the generator objects, set their data
        self.gen_list = {}
        
        for i in range(len(self.dispatch_order)):
            gen_type = self.dispatch_order[i]

            # Build the generator instances
            gen = mureilbuilder.create_instance(full_config, self.global_config, 
                self.config[gen_type], txmultigeneratorbase.TxMultiGeneratorBase,
                self.config['run_periods'])
            self.gen_list[gen_type] = gen

            # Supply data as requested by the generator
            mureilbuilder.supply_single_pass_data(gen, self.data, gen_type)
    
        # Check that run_periods increases by time_period_yrs
        self.run_periods = self.config['run_periods']
        if len(self.run_periods) > 1:
            run_period_diffs = numpy.diff(self.run_periods)
            if (not (min(run_period_diffs) == self.global_config['time_period_yrs']) or
                not (max(run_period_diffs) == self.global_config['time_period_yrs'])):
                raise mureilexception.ConfigException('run_periods must be separated by time_period_yrs', {})

        self.period_count = len(self.run_periods)
        self.is_configured = True
    
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            data: The name of the configuration file section specifying the data class to use and its
                configuration parameters. Defaults to 'Data'.
            transmission: The name of the configuration file section specifying the transmission model class
                to use and its configuration parameters. Defaults to 'Transmission', and if the 'Transmission'
                section is not provided, no transmission model will be used.
            global: The name of the configuration file section specifying the global configuration parameters.
                Defaults to 'Global'.

            dispatch_order: a list of strings specifying the names of the generator models to dispatch, in order,
                to meet the demand. All of these models then require a parameter defining the configuration file 
                section where they are configured. e.g. dispatch_order: solar wind gas. This requires additional
                parameters, for example solar: Solar, wind: Wind and gas: Instant_Gas to be defined, and corresponding
                sections Solar, Wind and Instant_Gas to configure those models.

            run_periods: A list of integers specifying the years defining each period in the multi-period
                simulation. Defaults to 2010. e.g. run_periods: 2010 2020 2030 2040 2050
            discount_rate: The discount rate in percent.

            output_file: The filename to write the final output data to. Defaults to 'mureil.pkl'.
            do_plots: Defaults to False. If True, output plots every output_frequency and at the end
                of the run.
        """
        return [
            ('data', None, 'Data'),
            ('transmission', None, 'Transmission'),
            ('global', None, 'Global'),
            ('output_file', None, 'ge.pkl'),
            ('dispatch_order', mureilbuilder.make_string_list, None),
            ('do_plots', mureilbuilder.string_to_bool, False),
            ('run_periods', mureilbuilder.make_int_list, [2010]),
            ('discount_rate', float, 0.0)
            ]


    def run(self, extra_data=None):
        start_time = time.time()
        logger.critical('Run started at %s', time.ctime())

        if (not self.is_configured):
            msg = 'run requested, but GeTxMultiMaster is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, {})
    
        # Read in the json data for generator capacity
        period_lists, startup_lists, demand_settings = self.load_js(extra_data)
        
        # Build up the results expected by the GE demo web code from the
        # results.
        all_years_out = {}

        # Compute an annual total for generation
        output_multiplier = (self.global_config['variable_cost_mult'] /
            float(self.global_config['time_period_yrs']))

        cuml_cost = 0.0

        results = self.calc_list_cost(period_lists, startup_lists, demand_settings)

        for i in range(len(self.run_periods)):
            period = self.run_periods[i]
           
            all_years_out[str(period)] = period_out = {}

            this_res = results['periods'][period]
            
            # Output, in MWh
            period_out['output'] = output_section = {}
            
            # Cost, in $M
            period_out['cost'] = cost_section = {}
            
            # Total carbon emissions
            period_out['co2_tonnes'] = 0.0
            
            ts_demand = this_res['generators']['demand']['other']['ts_demand']

            period_out['demand'] = '{:.2f}'.format(
                abs(sum(ts_demand)) * self.global_config['timestep_hrs'] *
                output_multiplier)
       
            this_period_cost = 0.0
            this_period_carbon = 0.0
            
            for gen_type in this_res['generators']:
                this_data = this_res['generators'][gen_type]

                # Total output, in MWh per annum
                output_section[gen_type] = '{:.2f}'.format(
                    this_data['total_supply_period'] / self.global_config['time_period_yrs'])
    
                # Total cost, per decade
                cost_section[gen_type] = this_data['cost']
                this_period_cost += this_data['cost']
                # or as a string:
                #                cost_section[gen_type] = '{:.2f}'.format(this_data['cost'])

                # Total carbon, per decade
                this_period_carbon += sum(this_data['carbon_emissions_period'])        

            # Total cumulative cost, with discounting
            # This assumes the costs are all incurred at the beginning of
            # each period (a simplification)
            period_out['period_cost'] = this_period_cost
            cuml_cost += this_period_cost / ((1 + (self.config['discount_rate'] / 100)) **
                (float(self.global_config['time_period_yrs']) * i))
            period_out['discounted_cumulative_cost'] = cuml_cost
    
            period_out['reliability'] = this_res['generators']['missed_supply']['other']['reliability']
            period_out['co2_tonnes'] = this_period_carbon

        return all_years_out
    

    def load_js(self, json_data):
        """ Input: JSON data structure with info on generators and demand management
                   at different time periods.
            Output: 
                period_lists: a nested dict {period: {gen_type: [new capacity]}}, where
                    the new_capacity list is suitable for input into TxMultiGeneratorBase
                    update_state_new_period_list.
                startup_lists: a dict {gen_type: [startup capacity]}, where the startup_capacity
                    list is suitable for input into TxMultiGeneratorMultiSite 
                    set_startup_state.
                demand_settings: a dict {period: [demand settings]}, where the demand
                    settings are suitable for updating the config of the demand source model.
            Reads in the data and builds list of new capacity by generator and period.
        """
        
        generators = json.loads(json_data)['selections']['generators']

        ## Only coal, gas, wind and solar are handled
        ## hydro is awaiting a rainfall-based model.

        gen_type_list = ['coal', 'gas', 'wind', 'solar']

        period_lists = {}
        for period in self.run_periods:
            period_lists[period] = {}
            for gen_type in gen_type_list:
                period_lists[period][gen_type] = []

        startup_lists = {}
        for gen_type in gen_type_list:
            startup_lists[gen_type] = []

        # Fill in the lists of new capacity
        for gen in generators:
            gen_type = gen['type']
            if gen_type not in gen_type_list:
                msg = 'Generator ' + str(gen_type) + ' ignored'
                logger.warning(msg)
            else:
                site_index = self.find_site_index(gen)
                build_date = int(gen['decade'])
                decommission_period = int(gen['decomission'])
                new_cap = float(gen['capacity'])

                if build_date in self.run_periods:
                    period_lists[build_date][gen_type].append(
                        (site_index, new_cap, decommission_period))
                else:
                    startup_lists[gen_type].append(
                        [site_index, new_cap, build_date, decommission_period])
    
        demand_settings_in = json.loads(json_data)['selections']['demand']
        demand_settings = {}
        for key in demand_settings_in:
            demand_settings[int(key)] = demand_settings_in[key]
    
        return period_lists, startup_lists, demand_settings
    

    def finalise(self):
        pass
        
         
    def calc_list_cost(self, period_lists, startup_lists, demand_settings):
        """Calculate the total system cost for this set of generators.
        Note that this is NOT thread-safe as it updates the self.period_configs
        with the demand settings. It may be safely called sequentially without
        reconfiguring the simulation, but not by multiple processes at once.
        """

        # First, set any starting states
        for gen_type in startup_lists:
            self.gen_list[gen_type].set_startup_state(startup_lists[gen_type])

        # And collect the state handles
        gen_state_handles = {}
        for gen_type in self.dispatch_order:
            gen_state_handles[gen_type] = (
                self.gen_list[gen_type].get_startup_state_handle())        

        if self.transmission is not None:
            tx_state_handle = self.transmission.get_startup_state_handle()

        cost = 0

        results = {'totals': {}, 'periods': {}, 'terminal': {}}
        total_carbon = 0.0

        for period in self.run_periods:
            self.gen_list['demand'].update_config_multi(
                demand_settings[period], period)

            period_carbon = 0.0
            results['periods'][period] = period_results = {'generators': {}, 'totals': {}}
            results['terminal'] = {'totals': {}, 'generators': {}}

            # supply_request is the running total, modified here
            if 'demand' in self.dispatch_order:
                supply_request = numpy.zeros(self.data.get_ts_length(), dtype=float)
            else:
                supply_request = numpy.array(self.data.get_timeseries('ts_demand'), dtype=float)

            period_cost = 0
            period_sites = []

            for gen_type in self.dispatch_order:
                gen = self.gen_list[gen_type]

                # Update the generators with the new capacity
                if gen_type in period_lists[period]:
                    gen.update_state_new_period_list(gen_state_handles[gen_type],
                        period, period_lists[period][gen_type])
                
                (this_sites, this_cost, this_supply, 
                    period_results['generators'][gen_type]) = gen.calculate_time_period_simple( 
                    gen_state_handles[gen_type], period, [], 
                    supply_request, full_results=True)
                    
                period_carbon += numpy.sum(
                    period_results['generators'][gen_type]['carbon_emissions_period'])

                period_sites += this_sites
                period_cost += this_cost
                supply_request -= this_supply

            if self.transmission is not None:
                tx_cost = self.transmission.calculate_cost(tx_state_handle, period, period_sites)
                period_cost += tx_cost
                ## and store tx_cost somewhere useful in period_results

            period_results['totals']['cost'] = period_cost
            period_results['totals']['carbon'] = period_carbon
            total_carbon += period_carbon
            
            cost += period_cost

        # calculate the terminal value at the end of the last period
        total_terminal_value = 0.0

        final_period = self.run_periods[-1]
        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            terminal_value, site_terminal_value = gen.get_terminal_value(final_period, 
                gen_state_handles[gen_type])

            results['terminal']['generators'][gen_type] = {'total_value': terminal_value, 
                'site_value': site_terminal_value}
            total_terminal_value += terminal_value
            
        cost -= total_terminal_value

        results['totals']['cost'] = cost
        results['totals']['carbon'] = total_carbon
        results['totals']['terminal_value'] = total_terminal_value

        return results


    def find_site_index(self, gen):
        """Use the location data in the generator info to choose which
        site index to use.
        """
        
        return 0
