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
import json
from os import path

from tools import mureilbuilder, mureilexception, mureiloutput, globalconfig
from tools import configurablebase, mureilbase
from generator import singlepassgenerator

logger = logging.getLogger(__name__)

class GeMureilMaster(mureilbase.MasterInterface, configurablebase.ConfigurableBase):
    def get_full_config(self):
        if not self.is_configured:
            return None
        
        # Will return configs collected from all objects, assembled into full_config.
        full_conf = {}
        full_conf['Master'] = self.config
        full_conf[self.config['data']] = self.data.get_config()
        full_conf[self.config['global']] = self.global_config

        for gen_type in self.dispatch_order:
            gen = getattr(self, gen_type)
            full_conf[self.config[gen_type]] = gen.get_config()

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
        
        # Set up the data class and get the data
        self.data = mureilbuilder.create_instance(full_config, self.global_config, self.config['data'], 
            mureilbase.DataSinglePassInterface)
        self.global_calc.update_config({'data_ts_length': self.data.get_ts_length()})
        self.global_calc.post_data_global_calcs()
        self.global_config = self.global_calc.get_config()

        # Instantiate the generator objects, set their data, determine their param requirements
        param_count = 0
        self.gen_list = {}
        self.gen_params = {}

        for i in range(len(self.dispatch_order)):
            gen_type = self.dispatch_order[i]

            # Build the generator instances
            gen = mureilbuilder.create_instance(full_config, self.global_config, 
                self.config[gen_type], singlepassgenerator.SinglePassGeneratorBase)
            self.gen_list[gen_type] = gen

            # Supply data as requested by the generator
            mureilbuilder.supply_single_pass_data(gen, self.data, gen_type)

            # Determine how many parameters this generator requires and
            # allocate the slots in the params list
            params_req = gen.get_param_count()
            if (params_req == 0):
                self.gen_params[gen_type] = (0, 0)
            else:
                self.gen_params[gen_type] = (param_count, 
                    param_count + params_req)
            param_count += params_req
        
        self.param_count = param_count
        
        self.is_configured = True
    
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            data: The name of the configuration file section specifying the data class to use and its
                configuration parameters. Defaults to 'Data'.
            global: The name of the configuration file section specifying the global configuration parameters.
                Defaults to 'Global'.

            dispatch_order: a list of strings specifying the names of the generator models to dispatch, in order,
                to meet the demand. All of these models then require a parameter defining the configuration file 
                section where they are configured. e.g. dispatch_order: solar wind gas. This requires additional
                parameters, for example solar: Solar, wind: Wind and gas: Instant_Gas to be defined, and corresponding
                sections Solar, Wind and Instant_Gas to configure those models.

            iterations: The number of iterations of the algorithm to execute. Defaults to 100.

            output_file: The filename to write the final output data to. Defaults to 'ge.pkl'.
            do_plots: Defaults to False. If True, output plots at the end of the run.
            
            year_list: A list of years specifying the start year of the periods to run, e.g. 
                year_list: 2010 2020 2030 2040 2050
            carbon_price_list: A list of integer carbon prices, matching in length the year_list.
            discount_rate: The discount rate in percent.
        """
        return [
            ('data', None, 'Data'),
            ('global', None, 'Global'),
            ('output_file', None, 'ge.pkl'),
            ('dispatch_order', mureilbuilder.make_string_list, None),
            ('do_plots', mureilbuilder.string_to_bool, False),
            ('year_list', mureilbuilder.make_string_list, None),
            ('carbon_price_list', mureilbuilder.make_int_list, None),
            ('discount_rate', float, 0.0)
            ]


    def run(self, extra_data):
        if (not self.is_configured):
            msg = 'run requested, but GeMureilMaster is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, {})

        # Read in the json data for generator capacity
        self.load_js(extra_data)
        
        all_years_out = {}

        # Compute an annual total for generation
        output_multiplier = (self.global_config['variable_cost_mult'] /
            float(self.global_config['time_period_yrs']))

        cuml_cost = 0.0

        for year_index in range(len(self.config['year_list'])):
            
            ## MG - this is a hack. The config should be set with all
            ## of the values at the start, and then be passed the year,
            ## not have them updated each time. This is ok here as it's
            ## only evaluated once anyway.
           
            results = self.evaluate_results(year_index)

            year = self.config['year_list'][year_index]

            # print results['gen_desc']
            
            all_years_out[str(year)] = year_out = {}
            
            # Output, in MWh
            year_out['output'] = output_section = {}
            
            # Cost, in $M
            year_out['cost'] = cost_section = {}
            
            # Total carbon emissions
            year_out['co2_tonnes'] = 0.0
            
            # Total demand, in MWh per annum
            for generator_type, value in results['other'].iteritems():
                if value is not None:
                    if 'ts_demand' in value:
                        year_out['demand'] = '{:.2f}'.format(
                            abs(sum(value['ts_demand'])) * self.global_config['timestep_hrs'] *
                            output_multiplier)
       
            # Total output, in MWh per annum
            for gen_type, vals in results['output'].iteritems():
                output_section[gen_type] = '{:.2f}'.format(
                    sum(vals) * self.global_config['timestep_hrs'] *
                    output_multiplier)
    
            # Total cost, per decade
            this_period_cost = 0.0
            for gen_type, value in results['cost'].iteritems():
                cost_section[gen_type] = value
                this_period_cost += value
# or as a string:
#                cost_section[generator_type] = '{:.2f}'.format(value)

            # Total cumulative cost, with discounting
            # This assumes the costs are all incurred at the beginning of
            # each period (a simplification)
            year_out['period_cost'] = this_period_cost
            cuml_cost += this_period_cost / ((1 + (self.config['discount_rate'] / 100)) **
                (float(self.global_config['time_period_yrs']) * year_index))
            year_out['discounted_cumulative_cost'] = cuml_cost
    
            for gen_type, value in results['other'].iteritems():
                if value is not None:
                    if 'reliability' in value:
                        year_out['reliability'] = value['reliability']
                    if 'carbon' in value:
                        year_out['co2_tonnes'] += value['carbon']

            if 'reliability' not in year_out:
                year_out['reliability'] = 100

        return all_years_out
    
    
    def load_js(self, json_data):
        """ Input: JSON data structure with info on generators and demand management
                   at different time periods.
            Output: None
            Reads in the data and computes the params for each time period.
        """
        
        generators = json.loads(json_data)['selections']['generators']

        ## Only coal, gas, wind and solar are handled, and only one of each.
        ## hydro is awaiting a rainfall-based model.

        self.total_params = {}
        self.inc_params = {}

        gen_total_table = {}
        gen_inc_table = {}
        year_list = self.config['year_list']

        gen_type_list = ['coal', 'gas', 'wind', 'solar']
        gen_param_counts = {}

        # Initialise the tables of capacity
        for gen_type in gen_type_list:
            gen_param_counts[gen_type] = self.gen_list[gen_type].get_param_count()
            gen_total_table[gen_type] = numpy.zeros((len(self.config['year_list']),
                gen_param_counts[gen_type]))                
            gen_inc_table[gen_type] = numpy.zeros((len(self.config['year_list']),
                gen_param_counts[gen_type]))                

        # Fill in the tables of capacity
        for gen in generators:
            gen_type = gen['type']
            if gen_type not in gen_type_list:
                msg = 'Generator ' + str(gen_type) + ' ignored'
                logger.warning(msg)
            else:
                this_total_table = gen_total_table[gen_type]
                this_inc_table = gen_inc_table[gen_type]

                loc_index = self.find_loc_index(gen)
                if (loc_index >= gen_param_counts[gen_type]):
                    msg = ('Generator ' + gen['id'] + ' looked up index as ' + str(loc_index) +
                        ' but the ' + gen_type + ' has data for ' + str(gen_param_counts[gen_type]) +
                        ' sites.')
                    raise mureilexception.ConfigException(msg, {})

                # build date could be specified as earlier, so capex is not paid.
                build_index = numpy.where(numpy.array(year_list) == str(gen['decade']))
                if len(build_index[0] > 0):
                    build_index = build_index[0][0]
                else:
                    build_index = -1

                decommission_index = numpy.where(numpy.array(year_list) == str(gen['decomission']))
                if len(decommission_index[0] > 0):
                    decommission_index = decommission_index[0][0]
                else:
                    decommission_index = len(year_list) - 1

                # accumulate new capacity in the incremental list
                if build_index >= 0:
                    this_inc_table[build_index][loc_index] += gen['capacity']                    
                
                # and add the new capacity to the total across all years until decommissioning
                start_fill = build_index
                if (build_index == -1):
                    start_fill = 0
                for i in range(start_fill, decommission_index + 1):
                    this_total_table[i][loc_index] += gen['capacity']
                    
        # Convert the tables of capacity to params for the sim
        for i in range(0, len(year_list)):
            this_total_params = numpy.zeros(self.param_count)
            this_inc_params = numpy.zeros(self.param_count)
            
            for gen_type in ['coal', 'wind', 'solar', 'gas']:
                param_ptr = self.gen_params[gen_type]
                if (param_ptr[0] < param_ptr[1]) and (gen_type in gen_total_table):
                    this_total_params[param_ptr[0]:param_ptr[1]] = (
                        gen_total_table[gen_type][i])
                    this_inc_params[param_ptr[0]:param_ptr[1]] = (
                        gen_inc_table[gen_type][i])

            self.total_params[str(year_list[i])] = this_total_params
            self.inc_params[str(year_list[i])] = this_inc_params
    
        self.demand_settings = json.loads(json_data)['selections']['demand']

    
    def finalise(self):
        pass

 
            
    def calc_cost(self, ts_demand, total_params, inc_params, save_result=False):

        rem_demand = numpy.array(ts_demand, dtype=float)
        cost = 0

        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            gen_ptr = self.gen_params[gen_type]

            this_params = numpy.concatenate((total_params[gen_ptr[0]:gen_ptr[1]],
                inc_params[gen_ptr[0]:gen_ptr[1]]))

            (this_cost, this_ts) = gen.calculate_cost_and_output(
                this_params, rem_demand, save_result)

            cost += this_cost
            rem_demand -= this_ts
            
        return cost


    def evaluate_results(self, year_index):
        """Collect a dict that includes all the calculated results from a
        run for that year.
        
        Inputs:
            year: an index for the current year, indexing self.config['year_list']
            
        Outputs:
            results: a dict containing:
                gen_desc: dict of gen_type: desc 
                    desc are strings describing
                    the generator type and the capacity or other parameters.
                cost: dict of gen_type: cost
                output: dict of gen_type: output
                other: dict of gen_type: other saved data
        """
        
        year = self.config['year_list'][year_index]
        
        total_params = self.total_params[year]
        inc_params = self.inc_params[year]
        
        ts_demand = numpy.zeros(self.data.get_ts_length(), dtype=float)

        # Set the year-dependent values
        # TODO - this is a hack, and is not thread-safe. Remove once
        # there is a proper decade by decade system.
        self.gen_list['demand'].update_config({'year': year})
        self.gen_list['demand'].update_config(self.demand_settings[year])
        for gen_type in self.dispatch_order:
            self.gen_list[gen_type].update_config({'carbon_price': 
                self.config['carbon_price_list'][year_index]})

        self.calc_cost(ts_demand, total_params, inc_params, save_result=True)
        
        results = {}
        for res_type in ['gen_desc', 'cost', 'output', 'capacity', 'other']:
            results[res_type] = {}
        
        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            results['gen_desc'][gen_type] = gen.interpret_to_string()

            saved_result = gen.get_saved_result()
            for res_type in ['capacity', 'cost', 'output', 'other']:
                results[res_type][gen_type] = saved_result[res_type]

        return results
        

    def find_loc_index(self, gen):
        """Use the location data in the generator info to choose which dataset to
        apply. The result needs to be an index into the set of timeseries supplied for
        that generator type. Must be 0 for the coal & gas.
        """
        
        return 0
        