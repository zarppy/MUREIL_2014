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
import numpy
import time
import logging
import copy
from os import path

from tools import mureilbuilder, mureilexception, mureiloutput, mureiltypes, globalconfig
from tools import mureilbase, configurablebase

from generator import txmultigeneratorbase

from master import interfacesflowmaster

import cvxopt as cvx
from cvxopt import matrix

logger = logging.getLogger(__name__)

class TxMultiMasterFlow(mureilbase.MasterInterface, configurablebase.ConfigurableMultiBase):
    def get_full_config(self):
        if not self.is_configured:
            return None
        
        # Will return configs collected from all objects, assembled into full_config.
        full_conf = {}
        full_conf['Master'] = self.config
        full_conf[self.config['data']] = self.data.get_config()
        full_conf[self.config['algorithm']] = self.algorithm.get_config()
        full_conf[self.config['global']] = self.global_config
        full_conf[self.config['demand']] = self.demand.get_config()
        full_conf[self.config['transmission']] = self.transmission.get_config()

        for i, gen_type in enumerate(self.generators):
            full_conf[self.config[gen_type]] = self.gen_list[i].get_config()

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

        # Now check the list of the generators
        for gen in self.config['generators']:
            self.config_spec += [(gen, None, None)]

        self.update_from_config_spec()
        self.check_config()
        
        self.generators = self.config['generators']
        
        # Set up the data class and get the data, and compute the global parameters
        self.data = mureilbuilder.create_instance(full_config, self.global_config, self.config['data'], 
            mureilbase.DataSinglePassInterface)
        self.global_calc.update_config({'data_ts_length': self.data.get_ts_length()})
        self.global_calc.post_data_global_calcs()
        self.global_config = self.global_calc.get_config()

        ## The master here takes 'global' variables, if needed and available, to get at the carbon_price_m,
        ## variable_cost_mult and time_scale_up_mult values, which it then expands to all time periods,
        ## for use later.
        for param_name in ['carbon_price_m', 'variable_cost_mult', 'time_scale_up_mult']:
            if (param_name not in self.config) and (param_name in self.global_config):
                self.config[param_name] = self.global_config[param_name]
        self.config_spec += [('carbon_price_m', float, None), ('variable_cost_mult', float, None),
            ('time_scale_up_mult', float, None)]
        self.check_config()
        self.expand_config(self.config['run_periods'])

        # Now instantiate the demand model
        self.demand = mureilbuilder.create_instance(full_config, self.global_config, 
            self.config['demand'], configurablebase.ConfigurableMultiBase,
            self.config['run_periods'])

        # Supply data to the demand model
        mureilbuilder.supply_single_pass_data(self.demand, self.data, 'demand')

        # And instantiate the transmission model
        self.transmission = mureilbuilder.create_instance(full_config, self.global_config,
            self.config['transmission'], configurablebase.ConfigurableMultiBase,
            self.config['run_periods'])
        
        mureilbuilder.check_subclass(self.transmission, 
            interfacesflowmaster.InterfaceTransmission)

        # Instantiate the generator objects, set their data, determine their param requirements,
        # and separate by dispatch type.
        param_count = 0
        
        # gen_list, gen_params are indexed by position in self.generators
        self.gen_list = [None] * len(self.generators)
        self.gen_params = [None] * len(self.generators)
        
        self.semisch_list = []
        self.instant_list = []
        self.ramp_list = []
        
        run_period_len = len(self.config['run_periods'])
        start_values_min = numpy.array([[]]).reshape(run_period_len, 0)
        start_values_max = numpy.array([[]]).reshape(run_period_len, 0)

        for i in range(len(self.generators)):
            gen_type = self.generators[i]

            # Build the generator instances
            gen = mureilbuilder.create_instance(full_config, self.global_config, 
                self.config[gen_type], txmultigeneratorbase.TxMultiGeneratorBase,
                self.config['run_periods'])
                
            self.gen_list[i] = gen

            gen_details = gen.get_details()
            gen_dispatch = gen_details['dispatch']
            
            if (gen_dispatch == 'semischeduled'):
                self.semisch_list.append(i)
                mureilbuilder.check_subclass(gen, interfacesflowmaster.InterfaceSemiScheduledDispatch)
            elif (gen_dispatch == 'instant'):
                self.instant_list.append(i)
                mureilbuilder.check_subclass(gen, interfacesflowmaster.InterfaceInstantDispatch)
            elif (gen_dispatch == 'ramp'):
                self.ramp_list.append(i)
                mureilbuilder.check_subclass(gen, interfacesflowmaster.InterfaceRampDispatch)
                msg = ("Generator " + gen_type + " has dispatch type ramp, which is not yet implemented")
                raise mureilexception.ConfigException(msg, {})            
            else:
                msg = ("Generator " + gen_type + " has dispatch type " + gen_dispatch + 
                    " which is not one of semischeduled, instant or ramp.")
                raise mureilexception.ConfigException(msg, {})
            
            # Supply data as requested by the generator
            mureilbuilder.supply_single_pass_data(gen, self.data, gen_type)
    
            # Determine how many parameters this generator requires and
            # allocate the slots in the params list
            params_req = gen.get_param_count()
            if (params_req == 0):
                self.gen_params[i] = (0, 0)
            else:
                self.gen_params[i] = (param_count, 
                    param_count + params_req)

                start_values_min, start_values_max = mureilbuilder.add_param_starts(
                    gen.get_param_starts(), params_req, self.global_config,
                    run_period_len, start_values_min, start_values_max)
                    
            param_count += params_req

        start_values_min = start_values_min.reshape(run_period_len * param_count)
        start_values_max = start_values_max.reshape(run_period_len * param_count)

        self.param_count = param_count
        # Check that run_periods increases by time_period_yrs
        self.run_periods = self.config['run_periods']
        if len(self.run_periods) > 1:
            run_period_diffs = numpy.diff(self.run_periods)
            if (not (min(run_period_diffs) == self.global_config['time_period_yrs']) or
                not (max(run_period_diffs) == self.global_config['time_period_yrs'])):
                raise mureilexception.ConfigException('run_periods must be separated by time_period_yrs', {})

        self.period_count = len(self.run_periods)
        self.total_param_count = param_count * self.period_count

        # Check if 'extra_data' has been provided, as a full gene to start at.
        # extra_data needs to be a dict with entry 'start_gene' that is a list
        # of integer values the same length as param_count.
        if extra_data is not None:
            if 'start_gene' in extra_data:
                if not (len(start_values_min) == self.total_param_count):
                    msg = ('extra_data of start_gene passed to txmultimasterflow. ' +
                        'Length expected = {:d}, found = {:d}'.format(self.total_param_count, 
                        len(start_values_min)))
                    raise mureilexception.ConfigException(msg, {})

                start_values_min = extra_data['start_gene']
                start_values_max = extra_data['start_gene']
       
        # Instantiate the market solver
        self.market_solver = mureilbuilder.create_instance(full_config, self.global_config, 
            self.config['market_solver'], configurablebase.ConfigurableMultiBase,
            self.config['run_periods'])

        # Instantiate the genetic algorithm
        mureilbuilder.check_section_exists(full_config, self.config['algorithm'])
        algorithm_config = full_config[self.config['algorithm']]
        algorithm_config['min_len'] = algorithm_config['max_len'] = self.total_param_count
        algorithm_config['start_values_min'] = start_values_min
        algorithm_config['start_values_max'] = start_values_max
        algorithm_config['gene_test_callback'] = self.gene_test
        self.algorithm = mureilbuilder.create_instance(full_config, self.global_config,
            self.config['algorithm'], mureilbase.ConfigurableInterface)

        self.is_configured = True
    
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            algorithm: The name of the configuration file section specifying the algorithm class to use and
                its configuration parameters. Defaults to 'Algorithm'.
            data: The name of the configuration file section specifying the data class to use and its
                configuration parameters. Defaults to 'Data'.
            demand: The name of the configuration file section specifying the demand model class
                to use and its configuration parameters. Defaults to 'Demand'.
            transmission: The name of the configuration file section specifying the transmission model class
                to use and its configuration parameters. Defaults to 'Transmission'.
            market_solver: The name of the configuration file section specifying the market solver class to
                use and its configuration parameters. Defaults to 'MarketSolver'.
            global: The name of the configuration file section specifying the global configuration parameters.
                Defaults to 'Global'.

            generators: a list of strings specifying the names of the generator models to use
                to meet the demand. All of these models then require a parameter defining the configuration file 
                section where they are configured. e.g. generators: solar wind gas. This requires additional
                parameters, for example solar: Solar, wind: Wind and gas: Instant_Gas to be defined, and corresponding
                sections Solar, Wind and Instant_Gas to configure those models.

            dispatch_fail_price: the cost, in $M, of a failed market optimisation. Default 1000000 ($1T). This aims
                to write off the solution.

            run_periods: A list of integers specifying the years defining each period in the multi-period
                simulation. Defaults to 2010. e.g. run_periods: 2010 2020 2030 2040 2050

            iterations: The number of iterations of the algorithm to execute. Defaults to 100.

            output_file: The filename to write the final output data to. Defaults to 'mureil.pkl'.
            output_frequency: Defaults to 500. After the first iteration and every output_frequency after
                that, report on the simulation status.
            do_plots: Defaults to False. If True, output plots every output_frequency and at the end
                of the run.
        """
        return [
            ('algorithm', None, 'Algorithm'),
            ('data', None, 'Data'),
            ('demand', None, 'Demand'),
            ('transmission', None, 'Transmission'),
            ('market_solver', None, 'MarketSolver'),
            ('global', None, 'Global'),
            ('iterations', int, 100),
            ('output_file', None, 'mureil.pkl'),
            ('generators', mureilbuilder.make_string_list, None),
            ('dispatch_fail_price', float, 1000000.0),
            ('do_plots', mureilbuilder.string_to_bool, False),
            ('output_frequency', int, 500),
            ('run_periods', mureilbuilder.make_int_list, [2010])
            ]


    def run(self, extra_data=None):
        start_time = time.time()
        logger.critical('Run started at %s', time.ctime())

        if (not self.is_configured):
            msg = 'run requested, but txmultimasterflow is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, {})
    
        try:
            self.algorithm.prepare_run()
            for i in range(self.config['iterations']):
                self.algorithm.do_iteration()
                if ((self.config['output_frequency'] > 0) and
                    ((i % self.config['output_frequency']) == 0)):
                    logger.info('Interim results at iteration %d', i)
                    self.output_results(iteration=i)
                    
        except mureilexception.AlgorithmException:
            # Insert here something special to do if debugging
            # such an exception is required.
            # self.finalise will be called by the caller
            raise
    
        logger.critical('Run time: %.2f seconds', (time.time() - start_time))

        results = self.output_results(iteration=self.config['iterations'], final=True)
        
        return results
    
    
    def output_results(self, final=False, iteration=0):
    
        (best_params, opt_data) = self.algorithm.get_final()

        if len(best_params) > 0:
            # Protect against an exception before there are any params
            results = self.evaluate_results(best_params)
            
            if 'dispatch_fail' in results:
                logger.info('======================================================')
                logger.info('Dispatch failed.')
                logger.info('======================================================')
            else:
                logger.info('======================================================')
                logger.info('Total cost ($M): {:.2f}, including carbon (MT): {:.2f}, terminal value ($M): {:.2f}'.format(
                    results['totals']['cost'], results['totals']['carbon'] * 1e-6, results['totals']['terminal_value']))
                logger.info('======================================================')

                ts_demand = {}

                # Now iterate across the periods, and then across the generators
                for period in self.run_periods:
                    period_results = results['periods'][period]
                    logger.info('------------------------------------------------------')
                    logger.info('PERIOD ' + str(period) + ':')
                    logger.info('------------------------------------------------------')
                    logger.info('Period cost ($M): {:.2f}, carbon (MT): {:.2f}'.format(
                        period_results['totals']['cost'], 
                        period_results['totals']['carbon'] * 1e-6))

                    for gen_type, value in period_results['generators'].iteritems():
                        gen_string = value['desc_string']
                        gen_cost = value['cost']
                        gen_supply = value['total_supply_period']
                        logger.info(gen_type + ' ($M {:.2f}, GWh {:.2f}) : '.format(
                            gen_cost, gen_supply / 1000) + gen_string)

                    logger.info('Total connection cost: $M {:.2f}'.format(
                        period_results['transmission']['connection_cost_total']))
                    logger.info('Total system demand: GWh {:.2f}'.format(
                        period_results['totals']['demand'] / 1000))
                    logger.info('Total unserved energy: GWh {:.2f}'.format(
                        period_results['demand']['unserved_energy_total'] / 1000))

                logger.info('======================================================')

            pickle_dict = {}
            pickle_dict['opt_data'] = opt_data
            pickle_dict['best_params'] = best_params

            full_conf = self.get_full_config()
            mureiloutput.clean_config_for_pickle(full_conf)
            pickle_dict['config'] = full_conf

            pickle_dict['best_results'] = results

            if self.config['do_plots']:
                if 'dispatch_fail' not in results:
                    for period in self.run_periods:
                        plot_data = {}
                        for gen_type, value in results['periods'][period]['generators'].iteritems():
                            plot_data[gen_type] = value['aggregate_supply']
            
                        ts_demand = results['periods'][period]['demand']['aggregate_ts']

                        this_final = final and (period == self.config['run_periods'][-1])
                        mureiloutput.plot_timeseries(plot_data, 
                            ts_demand, this_final, plot_title=(
                                str(period) + ' at iteration ' + str(iteration)))

            output_file = self.config['output_file']
            mureiloutput.pickle_out(pickle_dict, output_file)
        else:
            results = None

        return results
        

    def finalise(self):
        self.algorithm.finalise()

            
    def calc_cost(self, gene, full_results=False):
        """Calculate the total system cost for this gene. This function is called
        by the algorithm from a callback. The algorithm may set up multi-processing
        and so this calc_cost function (and all functions it calls) must be
        thread-safe. 
        This means that the function must not modify any of the 
        internal data of the objects.
        
        This implementation does a simple multi-period application of the market clearing.
        It uses the same offer price for all timesteps.
        """
        
        ts_len = self.data.get_ts_length()
        gen_count = len(self.generators)
        gen_active_sites = numpy.zeros(gen_count, dtype=numpy.int32)

        temp = numpy.array(gene)
        params_set = temp.reshape(self.period_count, self.param_count)

        gen_state_handles = [None] * gen_count
        for i in range(gen_count):
            gen_state_handles[i] = (
                self.gen_list[i].get_startup_state_handle())        

        cost = 0
        if full_results:
            results = {'totals': {}, 'periods': {}, 'terminal': {}}
            total_carbon = 0.0

        try:
            for i in range(len(self.run_periods)):
                period = self.run_periods[i]
                params = params_set[i]
                site_to_node_map = self.transmission.get_site_to_node_map()

                # Build the 'bids'
                bids = []
                demand_nodes = self.demand.get_node_names()
                bid_prices = self.demand.get_bid_prices(period)
                for j in range(0, len(demand_nodes)):
                    # Quantity is irrelevant as a multi-demand is used
                    bids.append({'node': demand_nodes[j],
                                 'price': bid_prices[j],
                                 'quantity': 0
                                })

                # Set up the 'multi_demand'
                multi_demand = matrix(self.demand.get_data(period)).T

                # Set up the 'offers' and 'multi_generation', ready for generator info
                offers = []
                multi_generation_build = [None] * gen_count          

                for j in range(gen_count):
                    gen = self.gen_list[j]
                    gen_ptr = self.gen_params[j]

                    # Set up the generator capacities
                    gen.update_state_new_period_params(gen_state_handles[j], period, 
                        params[gen_ptr[0]:gen_ptr[1]])    

                # offer_order is the list of indices into self.gen_list that reflect the order
                # that the offers are presented to the scheduler
                offer_order = []

                for j in self.ramp_list:
                    gen = self.gen_list[j]
                    site_indices, offer_price, min_quantity, max_quantity, ramp_rate_up, ramp_rate_down = (
                        gen.get_offers_ramp(gen_state_handles[j]))
                    if len(site_indices) > 0:
                        offer_order.append(j)
                        gen_active_sites[j] = len(site_indices)
                        for ind in site_indices:
                            offers.append({'node': site_to_node_map[ind],
                                           'price': offer_price,
                                           'quantity': 0,
                                           'ramp_up': ramp_rate_up,
                                           'ramp_down': ramp_rate_down
                                           })
                            multi_generation_build[j] = numpy.ones(ts_len) * max_quantity

                for j in self.instant_list:
                    gen = self.gen_list[j]
                    site_indices, offer_price, quantity = gen.get_offers_instant(gen_state_handles[j])
                    if len(site_indices) > 0:
                        offer_order.append(j)
                        gen_active_sites[j] = len(site_indices)
                        for ind in site_indices:
                            offers.append({'node': site_to_node_map[ind],
                                           'price': offer_price,
                                           'quantity': 0
                                           })
                            multi_generation_build[j] = numpy.ones(ts_len) * quantity

                for j in self.semisch_list:
                    gen = self.gen_list[j]
                    site_indices, offer_price, quantity = gen.get_offers_semischeduled(
                        gen_state_handles[j], ts_len)
                    if len(site_indices) > 0:
                        offer_order.append(j)
                        gen_active_sites[j] = len(site_indices)
                        for ind in site_indices:
                            offers.append({'node': site_to_node_map[ind],
                                           'price': offer_price,
                                           'quantity': 0
                                           })
                            multi_generation_build[j] = quantity

                multi_generation = matrix(0.0, (int(numpy.sum(gen_active_sites)), ts_len))

                ptr = 0
                for j in offer_order:
                    k = gen_active_sites[j]
                    multi_generation[ptr:ptr+k,:] = multi_generation_build[j]
                    ptr += k

                # Set up the market clearing engine
                market_solver = self.market_solver
                grid = self.transmission.get_grid(period)
                mke = market_solver.build_optimisation(bids, offers, grid)

                # Solve multiple steps - the SolverException will be thrown from here
                market_results, solutions = market_solver.solve_multiple_steps(mke, multi_demand, 
                    multi_generation)

                # Calculate costs
                period_cost = 0.0
                period_connection_cost = 0.0

                if full_results:
                    period_carbon = 0.0
                    results['periods'][period] = period_results = {'demand': {}, 'generators': {}, 'transmission': {}, 'totals': {}}
                    results['terminal'] = {'totals': {}, 'transmission': {}, 'generators': {}}
                    results['periods'][period]['transmission']['dispatch'] = dispatch_results = {}
                    results['periods'][period]['transmission']['connection_cost'] = {}
                    dispatch_results['bids'] = bids
                    dispatch_results['offers'] = offers
                    dispatch_results['bid_quantity'] = numpy.array(multi_demand)
                    dispatch_results['offer_quantity'] = numpy.array(multi_generation)
                    dispatch_results['scheduled_bids'] = numpy.array(market_results['scheduled_bids'])
                    dispatch_results['scheduled_offers'] = numpy.array(market_results['scheduled_offers'])
                    inj, ac_f, dc_f = market_solver.calculate_flows_from_solutions(mke, solutions)
                    dispatch_results['injections'] = numpy.array(inj)
                    dispatch_results['ac_flows'] = numpy.array(ac_f)
                    dispatch_results['dc_flows'] = numpy.array(dc_f)

                # Calculate unserved energy costs, where penalty is the bid at that node, as this is
                # what the optimisation optimised on.
                unserved_power = multi_demand - market_results['scheduled_bids']
                unserved_energy = (unserved_power * self.global_config['timestep_hrs'] *
                    self.global_config['time_scale_up_mult'])
                unserved_energy_cost = numpy.sum(matrix(bid_prices).T * unserved_energy)
                period_cost += unserved_energy_cost

                if full_results:
                    for i in range(len(bids)):
                        period_results['demand'][bids[i]['node']] = node_demand = {}
                        node_demand['bid_quantity_ts'] = numpy.array(multi_demand[i,:])
                        node_demand['total'] = numpy.sum(node_demand['bid_quantity_ts']) * self.global_config['time_scale_up_mult']
                        node_demand['unserved_energy'] = numpy.array((multi_demand[i,:] - market_results['scheduled_bids'][i,:]) *
                            self.global_config['time_scale_up_mult'])
                    period_results['demand']['unserved_energy_ts'] = numpy.sum(unserved_power, axis=1)
                    period_results['demand']['unserved_energy_total'] = numpy.sum(unserved_energy)
                    period_results['demand']['aggregate_ts'] = numpy.sum(multi_demand, axis=0)
                    period_results['totals']['demand'] = (numpy.sum(period_results['demand']['aggregate_ts']) *
                        self.global_config['time_scale_up_mult'])

                offer_ptr = 0
                sch_off = market_results['scheduled_offers']
                total_connection_cost = 0.0

                for j in offer_order:
                    gen = self.gen_list[j]
                    gen_type = self.generators[j]

                    # Calculate the costs, using the scheduled offers
                    gen_results = gen.calculate_costs_from_schedule_and_finalise(
                        gen_state_handles[j], sch_off[offer_ptr:(offer_ptr+gen_active_sites[j]),:],
                        full_results) 

                    gen_connection_cost = self.transmission.calculate_connection_cost(
                        None, gen_results['site_indices'], gen_results['capacity'],
                        gen_results['new_capacity'])
                    total_connection_cost += gen_connection_cost

                    if (full_results):
                        this_cost, period_results['generators'][gen_type] = self.complete_results_calc(
                            period, gen_results, full_results)
                        period_results['transmission']['connection_cost'][gen_type] = gen_connection_cost
                        period_carbon += period_results['generators'][gen_type]['total_carbon_emissions']
                    else:
                        this_cost = self.complete_results_calc(period, gen_results, full_results)

                    offer_ptr += gen_active_sites[j]
                    period_cost += this_cost

                period_cost += total_connection_cost

                if full_results:
                    period_results['transmission']['connection_cost_total'] = total_connection_cost
                    period_results['totals']['cost'] = period_cost
                    period_results['totals']['carbon'] = period_carbon
                    total_carbon += period_carbon

                cost += period_cost

            # calculate the terminal value at the end of the last period
            total_terminal_value = 0.0

            final_period = self.run_periods[-1]
            for i in range(gen_count):
                gen_type = self.generators[i]
                gen = self.gen_list[i]
                terminal_value, site_terminal_value = gen.get_terminal_value(final_period, 
                    gen_state_handles[i])

                if full_results:
                    results['terminal']['generators'][gen_type] = {'total_value': terminal_value, 
                        'site_value': site_terminal_value}

                total_terminal_value += terminal_value

            cost -= total_terminal_value

            if full_results:
                results['totals']['cost'] = cost
                results['totals']['carbon'] = total_carbon
                results['totals']['terminal_value'] = total_terminal_value

        except mureilexception.SolverException as me:
            if 'sol' in me.data:
                logger.debug('Solver fail: ' + me.data['sol']['status'])
            if 'prop' in me.data:
                logger.debug('Reject proportion: ' + str(me.data['prop']))
            cost = self.config['dispatch_fail_price']

            # and sum up all the gene values as an approximation to new capacity,
            # to direct towards a smaller system that might fit the grid
            # (assuming that massive oversupply is the problem with the solving)
            cost += numpy.sum(gene)
            
            if full_results:
                results['dispatch_fail'] = me.data

        if full_results:
            return cost, results
        else:
            return cost


    def complete_results_calc(self, period, gen_results, full_results=False):
        """Take the results from calculate_costs_from_schedule_and_finalise, and complete
        the calculation of the total cost for that generator, total supply, and 
        variable costs and carbon emissions across the period. The total cost includes
        the cost of the carbon emissions.
        
        This function could be overridden to use a more complex cost calculation method.
        
        Inputs:
            gen_results: dict, the output of a call to a generator's 
                calculate_costs_from_schedule_and_finalise function.
        
        Outputs:
            cost
            if full_results == True:
            results: dict, with fields:
                site_indices
                capacity
                new_capacity
                supply
                aggregate_supply
                variable_cost_period  (per site)
                carbon_emissions_period   (per site)
                other
                site_total_cost
                cost (total cost across all sites)
                total_carbon_emissions
                total_supply_period
                decommissioned
                desc_string
        """
        total_cost = 0.0
        
        curr_config = self.period_configs[period]
        variable_cost_mult = curr_config['variable_cost_mult']
        carbon_price_m = curr_config['carbon_price_m']
        time_scale_up_mult = curr_config['time_scale_up_mult']
        
        if full_results:
            results = {}
            results['site_indices'] = gen_results['site_indices']
            results['capacity'] = gen_results['capacity']
            results['new_capacity'] = gen_results['new_capacity']
            results['supply'] = numpy.array(gen_results['supply'])
            results['other'] = gen_results['other']
            results['decommissioned'] = gen_results['decommissioned']
            agg_supply = numpy.sum(results['supply'], axis=0)
            results['aggregate_supply'] = agg_supply
            results['total_supply_period'] = (numpy.sum(agg_supply) *
                time_scale_up_mult)
            results['desc_string'] = gen_results['desc_string']

        site_indices = gen_results['site_indices']
        site_total_cost = numpy.zeros(len(site_indices))

        # Add up the new capacity costs and decommissioning costs
        if full_results:
            for (site_index, dummy, site_cost) in gen_results['new_capacity']:
                site_total_cost[site_indices.index(site_index)] += site_cost
            for (site_index, dummy, site_cost) in gen_results['decommissioned']:
                site_total_cost[site_indices.index(site_index)] += site_cost
        else:
            total_cost += gen_results['new_capacity_total_cost']                
            total_cost += gen_results['decomm_total_cost']

        # Scale up the carbon emissions and the variable costs
        carbon_emissions_period_sites = (gen_results['carbon_emissions_ts'] * 
            time_scale_up_mult)
        variable_cost_period_sites = (gen_results['variable_cost_ts'] * 
            variable_cost_mult)
        
        # Sum up the total cost per site, including carbon pricing
        site_total_cost += variable_cost_period_sites
        site_total_cost += carbon_emissions_period_sites * carbon_price_m

        total_cost += numpy.sum(site_total_cost)
        
        if full_results:
            results['variable_cost_period'] = variable_cost_period_sites
            results['carbon_emissions_period'] = carbon_emissions_period_sites
            results['total_carbon_emissions'] = numpy.sum(carbon_emissions_period_sites)
            
        if full_results:
            results['cost'] = total_cost
            return total_cost, results
        else:
            return total_cost
        

    def evaluate_results(self, params):
        """Collect a dict that includes all the calculated results from a
        run with params.
        
        Inputs:
            params: list of numbers, typically the best output from a run.
            
        Outputs:
            results: a dict of gen_type: gen_results
            where gen_results is the output from calculate_time_period_simple in
            txmultigenerator.py (or subclass), with full_results = True.
        """
        
        cost, results = self.calc_cost(params, full_results=True)
        return results
        
        
    def gene_test(self, gene):
        """input: list
        output: float
        takes the gene.values, tests it and returns the genes score
        """
        score = -1 * self.calc_cost(gene)
        return score
