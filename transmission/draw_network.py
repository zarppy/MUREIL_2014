import numpy as np
from transmission import PFM_v24

def draw_simon_network_wrapper(nodes, lines, injections, flows):
    # convert data to what Simon's code requires
    simon_pf = PFM_v24.PowerFlow()

    simon_pf.node_dictonary = node_dictonary(nodes)
    simon_pf.line_dictionary = line_dictionary(nodes, lines)
    filename = 'network_and_flows'

    simon_pf.draw_network(flows, np.array(injections.T), filename)

def node_dictonary(nodes):
    node_dictonary = {}
    for j, node in enumerate(nodes):
        node_dictonary[j] = {'name': node['name'],
                             'state': node['region'],
                             'x_loc': node['longitude'],
                             'y_loc': node['latitude']}
    return node_dictonary

def line_dictionary(nodes, lines):
    line_dictionary = {}
    for j, line in enumerate(lines):
        origin = index_of(line['node from'], nodes)
        destination = index_of(line['node to'], nodes)
        line_dictionary[j] = {'Y': 0.0,
                             'capacity_ag': -1.*line['min_flow'], # 'capacity_ag' is +ve, 'min_flow' -ve
                             'capacity_in': line['max_flow'],
                             'origin': origin,
                             'destination': destination}
    return line_dictionary

def index_of(node_name, nodes):
    return [n['name'] for n in nodes].index(node_name)

