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

"""Defines the Grid class which reads in data files describing a transmission grid.
Grid defines self.nodes, self.lines, self.shift_factors, self.admittance.
"""

import numpy as np
from cvxopt import matrix

class Grid:
    def load(self, input_dir, input_filenames, remove_slack_node=True):
        self.nodes, self.lines, self.shift_factors, self.admittance = load_network(input_dir, input_filenames, remove_slack_node)
        self.ac_dc_lines()

    def ac_dc_lines(self):
        try:
            self.ac_lines = [l for l in self.lines if l['type'] == 'HVAC']
            self.dc_lines = [l for l in self.lines if l['type'] == 'HVDC']
        except KeyError:
            self.ac_lines = self.lines
            self.dc_lines = []


def load_network(input_dir, input_filenames, remove_slack_node=True):
    filenames = {'nodes': input_dir + input_filenames[0],
                 'lines': input_dir + input_filenames[1],
                 'shift_factors': input_dir + input_filenames[2],
                 'admittance': input_dir + input_filenames[3]}

    nodes = []
    import csv
    with open(filenames['nodes'], 'rU') as n:
        reader = csv.reader(n)
        for row in reader:
            if reader.line_num == 1:
                continue
            else:
                nodes.append({'name': row[1],
                              'region': row[2],
                              'longitude': float(row[3]),
                              'latitude': float(row[4])})
                if len(row) >= 7:
                    nodes[-1]['peak_demand_fraction_of_region'] = float(row[5])
                    nodes[-1]['off_peak_demand_fraction_of_region'] = float(row[6])
                else:
                    nodes[-1]['demand_fraction_of_region'] = float(row[5])

    lines = []
    with open(filenames['lines'], 'rU') as l:
        reader = csv.reader(l)
        for row in reader:
            if reader.line_num == 1:
                continue
            else:
                lines.append({'name': row[0],
                              'node from': row[1],
                              'node to': row[2],
                              'min_flow': float(row[3]),
                              'max_flow': float(row[4])})
                if len(row) >= 6: # HVDC or HVAC
                    try:
                        susceptance = float(row[5])
                    except ValueError:
                        susceptance = row[5]
                    lines[-1]['susceptance'] = susceptance
                    lines[-1]['type'] = row[6]
                    try:
                        lines[-1]['comment'] = row[7] # not all lines have comments
                    except:
                        pass
    ac_lines = [l for l in lines if l['type'] == 'HVAC']

    try:
        admittance = matrix(np.genfromtxt(filenames['admittance'], dtype=float,
                                          delimiter=',', skip_header=0))
        if remove_slack_node:
            admittance = -1. * admittance[1:, :]
        else:
            admittance = -1. * admittance
    except:
        admittance = None

    try:
        if remove_slack_node:
            nodes = nodes[1:]
            shift_factors = matrix(np.genfromtxt(filenames['shift_factors'], dtype=float,
                                      delimiter=',', skip_header=0))
        else:
            shift_factors = matrix(np.zeros((len(ac_lines), len(nodes))))

            shift_factors[:, 1:] = matrix(np.genfromtxt(filenames['shift_factors'], dtype=float,
                                              delimiter=',', skip_header=0))
    except:
        shift_factors = None

    return nodes, lines, shift_factors, admittance

