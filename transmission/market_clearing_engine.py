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

"""Defines the MarketClearingEngine class which sets up a linear-program optimisation
of power flows based on bid and offer prices.
"""

import logging
import numpy as np
import cvxopt as cvx
from cvxopt import solvers

from tools import mureilexception, configurablebase, mureilbuilder

logger = logging.getLogger(__name__)

class MarketOptimisation:
    pass


class MarketClearingEngine(configurablebase.ConfigurableMultiBase):
    """Configure the engine that calculates the dispatch using an LP.
    """
    def complete_configuration_post_expand(self):
        """Configure the solver.
        """
        solvers.options['show_progress'] = self.config['show_progress']
        solvers.options['feastol'] = self.config['feastol']
        solvers.options['abstol'] = self.config['abstol']
        solvers.options['reltol'] = self.config['reltol']

        
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            show_progress: boolean, default False - print out the progress of the solver
            
            feastol: float, default 1e-8 - solver option
            abstol: float, default 1e-8 - solver option
            reltol: float, default 1e-8 - solver option
            
            demand_min: float, default 0 - the proportion of demand that is the 
                minimum in the constraints. This aims to reduce the size of the
                feasible region to reduce numerical issues seen when there is significant missed supply.
                ### TODO ### implement this
            reject_outright_proportion: float, default 2 - when a check is done before
                running the optimisation, the maximum allowable sum(demand_bids)/sum(supply_offers).
                This aims to reduce the range of the objective to reduce numerical issues, 
                and to weed out impossible problems quickly.
        """
        return [
            ('show_progress', mureilbuilder.string_to_bool, 'False'),
            ('feastol', float, 1e-8),
            ('abstol', float, 1e-8),
            ('reltol', float, 1e-8),
            ('demand_min', float, 0),
            ('reject_outright_proportion', float, 2.0)
            ]


    def build_optimisation(self, bids, offers, grid, simultaneous_steps=1):
        """Sets up the optimisation matrices, to relate bids (for demand),
        offers (of supply), and the grid (description of transmission network).
        
        Inputs:
            bids: list of {'nodes': node_name, 'price': bid_price, 'quantity': quantity demanded}
                where node_name is a string, bid_price is a float, and quantity is a float, where
                quantity is be arbitrary if a multi-step solve will be done.
            offers: list of {'nodes': node_name, 'price': offer price, 'quantity': quantity offered}
                where node_name is a string, offer_price is a float, and quantity is a float, where
                quantity is arbitrary is a multi-step solve will be done. 
            grid: description of the transmission grid, as created by grid_data_loader.py.
                ## TODO ### fill in what this means
            simultaneous_steps: integer, default 1 - specify how many timesteps to simultaneously
                solve. (Not implemented). 
                
        Outputs:
            market: an object of type MarketOptimisation that holds the configured objective and constraints.
        """
        
        market = MarketOptimisation()
        
        market.bids_template = bids
        market.offers_template = offers
        market.grid = grid
        dc_lines=grid.dc_lines

        market.objective = self.build_objective(bids, offers, dc_lines)
        count_opt_vars = len(bids) + len(offers) + 2*len(dc_lines)

        market.conservation_of_energy_lhs = cvx.matrix(np.hstack((-1. * np.ones(len(bids)),
                                                                np.ones(len(offers)),
                                                                np.zeros(2*len(dc_lines))))).T
        market.conservation_of_energy_rhs = cvx.matrix([0.])

        max_opt_vars_lhs = cvx.matrix(np.diag( 1. * np.ones(count_opt_vars)))
        max_opt_vars_rhs = cvx.matrix([f['quantity'] for f in (bids + offers)] +
                                      [0 for l in dc_lines] +  # flow_-
                                      [l['max_flow'] for l in dc_lines]) # flow_+

        min_opt_vars_lhs = -1. * max_opt_vars_lhs
        min_opt_vars_rhs = -1. * cvx.matrix(np.hstack((np.zeros(len(bids) + len(offers)),
                                            np.array([l['min_flow'] for l in dc_lines]),
                                            np.zeros(len(dc_lines)))))

        market.injections_from_schedule = self._injections_from_schedule(bids, offers, grid.nodes, dc_lines)

        ac_flows = grid.shift_factors * market.injections_from_schedule
        min_ac_flows_lhs = -1. * ac_flows
        min_ac_flows_rhs = -1. * cvx.matrix([l['min_flow'] for l in grid.ac_lines])

        max_ac_flows_lhs = ac_flows
        max_ac_flows_rhs = cvx.matrix([l['max_flow'] for l in grid.ac_lines])

        market.inequality_constraint_lhs = cvx.matrix([min_opt_vars_lhs, max_opt_vars_lhs, min_ac_flows_lhs, max_ac_flows_lhs])
        market.inequality_constraint_rhs = cvx.matrix([min_opt_vars_rhs, max_opt_vars_rhs, min_ac_flows_rhs, max_ac_flows_rhs])

        market.start_to_update_program = len(min_opt_vars_rhs)
        market.end_to_update_program = len(min_opt_vars_rhs) + len(max_opt_vars_rhs) - 2*len(dc_lines)

        return market


    def solve_single_step(self, market):
        """Solve the LP in the market object, as configured by build_optimisation
        """
        solution = self.solve(market)
        return solution


    def solve_multiple_steps(self, market, multi_demand, multi_generation):
        """Solve the LP in the market object, for quantity values in a matrix for
        demand and generation, which correspond to the bids and offer nodes when
        the market object was created by build_optimisation.
        
        Inputs:
            market: a market optimisation created by build_optimisation
            multi_demand: a matrix of quantities bid, corresponding to bid nodes
            multi_generation: a matrix of quantities offered, corresponding to offer nodes
            
        Outputs:
            results: if success == True, a dict containing the following, or None:
                scheduled_bids: a matrix of scheduled bids, corresponding to multi_demand
                scheduled_offers: a matrix of scheduled offers, corresponding to multi_generation
            solutions: The solutions object, for debug use.

        Exceptions:
            will raise SolverException if either the solver failed to reach an optimal
                solution, or the solver was not run due to rejection by the 
                reject_outright_proportion check on total demand and total supply.
        """
        solutions = []
        
        if multi_demand.size[1] != multi_generation.size[1]:
            msg = ('multi_demand.size[0] = ' + str(multi_demand.size[0]) + 
                ', multi_demand.size[1] = ' + str(multi_demand.size[1]) + 
                ', multi_generation.size[0] = ' + str(multi_generation.size[0]) + 
                ', multi_generation.size[1] = ' + str(multi_generation.size[1]))
            raise mureilexception.ConfigException(msg, {})

        for j in range(multi_generation.size[1]):
            # Check here that total demand isn't heaps more than total supply
            tot_d = np.sum(multi_demand[:,j])
            tot_g = np.sum(multi_generation[:,j])
            if (tot_d / tot_g) > self.config['reject_outright_proportion']:
                msg = 'Reject outright ' + str(tot_d / tot_g)
                raise mureilexception.SolverException(msg, {'prop': tot_d / tot_g})
            self.update_program(market, multi_demand[:,j], multi_generation[:,j])
            this_sol = self.solve(market)
            solutions.append(this_sol)
    
        results = {}
        schedules = cvx.matrix([s['x'].T for s in solutions]).T
        results['scheduled_bids'] = self.scheduled_bids(market, schedules)
        results['scheduled_offers'] = self.scheduled_offers(market, schedules)
        return results, solutions


    def build_objective(self, bids, offers, dc_lines):
        bid_prices = np.array([bid['price'] for bid in bids])
        offer_prices = np.array([offer['price'] for offer in offers])
        objective = cvx.matrix(np.hstack((-1. * bid_prices,
                                          +1. * offer_prices,
                                          -1e-2 * np.ones(len(dc_lines)), # negative dc line flow
                                          +1e-2 * np.ones(len(dc_lines))))) # positive dc line flow
        return objective


    def solve(self, market):
        """Solve the LP for a single step. Return a solution object and whether the optimisation
        was successful.
        
        Inputs: 
            market: a MarketOptimisation object, from build_optimisation
            
        Outputs:
            solution: a solution object from solvers.lp
            
        Exception:
            raises mureilexception.SolverException if the solver does not find an optimal solution
        """
        solution = solvers.lp(market.objective,
                          market.inequality_constraint_lhs, market.inequality_constraint_rhs,
                          market.conservation_of_energy_lhs, market.conservation_of_energy_rhs)

        if not (solution['status'] == 'optimal'):
            msg = 'Solver status ' + solution['status']
            raise mureilexception.SolverException(msg, {'sol': solution})
        return solution


    def update_program(self, market, new_bids, new_offers):
        start = market.start_to_update_program
        end = market.end_to_update_program
        market.inequality_constraint_rhs[start:end] = cvx.matrix([new_bids, new_offers])


    def injections(self, market, schedule):
        return market.injections_from_schedule * schedule


    def dc_flows(self, schedule, dc_lines):
        dc_flows_from_schedule = cvx.matrix(np.zeros((len(dc_lines), schedule.size[0])))
        dd = np.diag(np.ones(len(dc_lines)))
        dc_flows_from_schedule[:, -2*len(dc_lines):] = np.hstack((dd, dd))
        return dc_flows_from_schedule * schedule

    def scheduled_bids(self, market, schedule):
        return schedule[:len(market.bids_template),:]

    def scheduled_offers(self, market, schedule):
        return schedule[len(market.bids_template):len(market.bids_template) + len(market.offers_template),:]


    def calculate_flows_from_solutions(self, market, solutions):
        """Calculate a full set of flow results from the market and the solution. Use this to get full
        results for logging.
        """
        schedules = cvx.matrix([s['x'].T for s in solutions]).T
        injections = market.injections_from_schedule * schedules
        ac_flows = market.grid.shift_factors * injections
        dc_flows = self.dc_flows(schedules, market.grid.dc_lines)

        return injections, ac_flows, dc_flows


    def _injections_from_schedule(self, bids, offers, nodes, dc_lines):
        len_bids = len(bids)
        len_offers = len(offers)
        injections_from_schedule = np.zeros((len(nodes), len_bids + len_offers + 2*len(dc_lines)))
        for node_idx, node in enumerate(nodes):
            for bid_idx, bid in enumerate(bids):
                if bid['node'] == node['name']:
                    injections_from_schedule[node_idx, bid_idx] = -1.
            for offer_idx, offer in enumerate(offers):
                if offer['node'] == node['name']:
                    injections_from_schedule[node_idx, len_bids + offer_idx] = +1.
            if dc_lines:
                for neg_dc_line_idx, neg_dc_line in enumerate(dc_lines):
                    if neg_dc_line['node from'] == node['name']:
                        injections_from_schedule[node_idx, len_bids + len_offers + neg_dc_line_idx] = -1.
                    if neg_dc_line['node to'] == node['name']:
                        injections_from_schedule[node_idx, len_bids + len_offers + neg_dc_line_idx] = +1.

                for pos_dc_line_idx, pos_dc_line in enumerate(dc_lines):
                    if pos_dc_line['node from'] == node['name']:
                        injections_from_schedule[node_idx, len_bids + len_offers + len(dc_lines) + pos_dc_line_idx] = -1.
                    if pos_dc_line['node to'] == node['name']:
                        injections_from_schedule[node_idx, len_bids + len_offers + len(dc_lines) + pos_dc_line_idx] = +1.
        return cvx.matrix(injections_from_schedule)



