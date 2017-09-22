# -*- coding: utf-8 -*-
"""
MAIN FILE

File wrote to make test calculations with the PowerFlow model.

A folder with csv files representing the network and supply must exist in
the same directory.

@author: simonhollnaicher
"""
import time
import PFM_v24
import numpy as np
import csv

# change here to either "random/" or "NEM_test" in order to switch between one 
# period or 8760 periods with randomized supply, both contain the same network
folder = "NEM_test/"


# Read in input values from csv files
supply = np.genfromtxt(folder+"Supply.csv", dtype=float, delimiter=',', 
                            skip_header=0)
a_matrix = np.genfromtxt(folder+"A-matrix.csv", dtype=float, delimiter=',', 
                            skip_header=0)
y_bus = np.genfromtxt(folder+"Y-Bus_matrix.csv", dtype=float, delimiter=',',
                         skip_header=0)
capacity_matrix = np.genfromtxt(folder+"Cap_matrix.csv", dtype=float, delimiter=',',
                         skip_header=0)
             

# Create instance of PowerFlow class
PF_run1 = PFM_v24.PowerFlow()

# Create a node_dictionary from the csv file, only used for the drawing function
reader = csv.reader( open(folder+"node_list.txt"), delimiter=',')
for idx,row in enumerate(reader):
    data = row[0].split("\t")
    PF_run1.node_dictonary[int(data[0])] = {"name": data[1], 
                                    "state": data[2], "x_loc": float(data[3]),
                                    "y_loc": float(data[4])}                                          

print "\nstart of power flow calculation..."
start = time.time()
PF_run1.create_transmission_network(y_bus, a_matrix, capacity_matrix)
mid = time.time()
PF_run1.calculate_flow(supply)
end = time.time()
PF_run1.analyse_network()
end2 = time.time()
PF_run1.draw_network(PF_run1.flow_series[0], supply, 'flow1')
end3 = time.time()

print 'total_unresolved_flow: %i' % PF_run1.total_unresolved_flow
print "Time consumed creating network: %.3f sec" % (mid - start)
print "Time consumed calculating flow: %.3f sec" % (end - mid)
print "Time per timestep: %.7f sec" % ((end - mid)/len(supply))
print "Time consumed analysing network: %.3f sec" % (end2 - end)
print "Time consumed drawing network: %.3f sec" % (end3 - end2)

#increase Melbourne_laTrobe
cost_update = PF_run1.update_transmission_network(0,1,3000,3000,0.3)
print '\nUpdated capacity on MEL-LAT line with 2000MW, costs: M$ %d ' % cost_update
end4 = time.time()
PF_run1.calculate_flow(supply)
PF_run1.draw_network(PF_run1.flow_series[0], supply, 'flow_after_update')
print "Time consumed updating network: %.3f sec" % (end4 - end3)
