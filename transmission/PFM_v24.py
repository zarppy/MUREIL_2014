# -*- coding: utf-8 -*-
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
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import math

class PowerFlow():
    """The power flow class, which can serve as a transmission model for
    an energy system model. In the current version it can return the amount
    of failed transmission. It further will have the ability to be updated
    via a function, in order to introduce changeability.
    """

    def __init__(self):
        """Initiates a class member of the power flow class.
        """
        self.b_inverse_matrix = np.matrix(1)
        self.a_d_matrix = np.matrix(1)
        self.no_edges = 0
        self.total_unresolved_flow = 0
        self.flow_series = []
        self.line_dictionary = {}
        self.node_dictonary = {}
        
        # Maybe expendable, right no used for update method
        self.y_bus = []
        self.a_matrix = []
        self.capacity_matrix = []
        self.no_nodes = 0

    def calculate_flow(self, supply):
        """Calculates the power flow for the current supply set, which is 
        provided by the txmultigenerator. The method 
        create_transmission_network needs to be run before calculating the
        flow. No output is returned, but the total_unresolved_flow is changed.

        Inputs: 
            supply: a timeseries of supply vectors 
        Output:
            none

        """
        # Loop through full timeperiod
        t=0
        while t < len(supply):    
                        
            supply_vector = np.matrix(np.array(supply[t])[1:])        
            
            # Calculate the nodal phase angles
            phase_angle_vector =  self.b_inverse_matrix * supply_vector.T
    
            # Calculate the line flows    
            flow_vector = self.a_d_matrix * phase_angle_vector    

            # Save flow in timeseries for later evaluation
            self.flow_series.append(flow_vector)

            t += 1            


    def analyse_network(self):
        """Analysis of the network. Returns a maximum flows that were assigned
        to the lines and a capacity that would be sufficient to transport 90%
        of the flows. These values can be later used to see where capacity
        was exceded to recaculate the dispatch and eventually make network 
        updates.
        
        Input:
            None, uses self.flow_series as basis of calculation
        Output:
            line_maxLoad_in: maximum flow in timeseries in defined direction 
                            on line
            line_maxLoad_ag: maximum flow in timeseries against defined 
                            direction on line
            line_load90_in: 90% percentile flow in timeseries in defined 
                            direction on line
            line_load90_ag: 90% percentile flow in timeseries against defined 
                            direction on line
        """
        # Devide flow_array into one with the positive values and one with neg.        
        flow_array_pos = np.clip(np.array(self.flow_series),0,np.Infinity)
        flow_array_neg = -1*(np.clip(np.array(self.flow_series),-np.Infinity,0))
        
        # Calculate max load that occured on the transmission line in the timeseries        
        line_maxLoad_in= flow_array_pos.max(axis=0)
        line_maxLoad_ag= flow_array_pos.max(axis=0)
        
        # Calculate capacity that would be sufficient for 90% of the loads
        # on that line for the loads of that timeseries
        line_load90_in = np.percentile(flow_array_pos,90,axis=0)
        line_load90_ag = np.percentile(flow_array_neg,90,axis=0)
        
        return line_maxLoad_in, line_maxLoad_ag, line_load90_in, line_load90_ag


    def create_transmission_network(self, y_bus, a_matrix, capacity_matrix):
        """Prepares the transmission network for the flow calculation. Sets
        up the matrixes needed for the flow calculation, namely b_inverse_matrix
        and the a_d_matrix. Further creates a line_dictionary with information
        about origin node, destination node, capacity and admittance value for
        each line. 
        
        N: number of nodes
        M: number of lines
        
        Input:
            y_bus: (NxN) nodal attmittance matrix with 
                    y-bus(i,j) = -Y(i,j) for non-diagonal values and
                    y-bus(i,i) = Y(i,i) + sum(Y(i,j): for j:(1,N) & j != i) 
                    In this simple DC power flow model the resistance is 
                    neglected, therefore the admittance y = -j * b with b 
                    being the suspectance.
                    
            a_matrix: (MxN) node-arc incidence matrix, with 
                    a(m,n) = 1 if arc m has its starting point in node n
                    a(m,n) = -1 if arc m has its end point in node n#
                    a(m,n) = 0 otherwise
                    
            capacity_matrix: (NxN) matrix of the line capacities
                    capacity(i,j) = tranfer capacity between node i and node j
                    (note: capacity(i,j) can be different from capacity(j,i))
                    
        Output:
            none, but saves mentioned results in self. variables 
                    
        """
        self.no_edges = len(a_matrix)
        self.no_nodes = len(a_matrix[1])
        self.y_bus = y_bus
        self.a_matrix = a_matrix
        self.capacity_matrix = capacity_matrix
        
        # Calculate b_inverse_matrix
        # first calculate b_prime_matrix, which is the negative of the y-bus,
        # but the diagonal elements are replaced by the sum of the b-values
        # in the row of the respective element.
        # shape: (N-1) x (N-1)
        b_prime_matrix = -1 * y_bus[1:,1:] 
        for i, row in enumerate(b_prime_matrix):
            # replace diagonal elements with sum of all other elements of its row
            b_prime_matrix[i][i] = sum(y_bus[i+1]) - y_bus[i+1][i+1]
        self.b_inverse_matrix = np.linalg.inv(b_prime_matrix)        
        
        #Calculate D-matrix and capacity_vector and create line_dictionary
        d_matrix = np.zeros((self.no_edges,self.no_edges))
        i=0        
        while i < self.no_edges:
            row = list(a_matrix[i])
            orig_id = row.index(1)
            dest_id = row.index(-1)
            
            d_matrix[i][i] = y_bus[orig_id][dest_id]
            
            self.line_dictionary[i] = {'origin': orig_id, 'destination': dest_id,
                                    'capacity_in':capacity_matrix[orig_id][dest_id],
                                    'capacity_ag':capacity_matrix[dest_id][orig_id],
                                    'Y':y_bus[orig_id][dest_id] }   
            i=i+1
  
        # Calculate a_d_matrix
        # := transfer admittance matrix
        #  (M x N-1)
        #  with a_d(line i, node j) := -b(i) if j is end node of line
        #                               b(i) if j is start node of line
        self.a_d_matrix = np.matrix(d_matrix) * np.matrix(a_matrix)[:,1:]      
    
    
    
    
    def update_transmission_network(self, origin_id, dest_id, cap_incr_in, 
                                    cap_incr_ag, new_y):
        """Updates the capacity and y-bus of the transmission network
        according to the input values and returns a cost value.
        
        ### PRELIMINAR VERSION ###
        to do:
            -better cost calculation, based on different types of updates,
            maybe just 2 or 3 different options with a fixed capacity increase
            -...
        
            Inputs: 
               origin_id: id of starting node 
               dest_id:   id of end node
               cap_incr_in: capacity update in direction of line
               cap_incr_ag: capacity update against direction of line
               new_y:   new admittance value for y_bus
                
            Output:
                cost: investment cost for capacity increase
        """
        cost = 0   
        new_capacity_matrix = self.capacity_matrix
        new_y_bus = self.y_bus
        new_a_matrix = self.a_matrix
            
        # Check if nodes existed before
        if origin_id < self.no_nodes and dest_id < self.no_nodes:
            
            # Calculate distance for cost calculation with Haversine Formula
            lat1, lat2, lon1, lon2 = map(math.radians, 
                                    [self.node_dictonary[dest_id]['y_loc'],
                                    self.node_dictonary[origin_id]['y_loc'],
                                    self.node_dictonary[origin_id]['x_loc'],
                                    self.node_dictonary[dest_id]['x_loc']])
            dlon = abs(lon1 - lon2)
            dlat = abs(lat1 - lat2)
            a = (math.sin(dlat/2))**2 + math.cos(lat1) * math.cos(lat2)\
                    * (math.sin(dlon/2))**2     
            c = 2 * math.atan2( math.sqrt(a), math.sqrt(1-a) )
            distance = 6373 * c
            
            # Check further if connection existed before
            if self.capacity_matrix[origin_id][dest_id] != 0 or \
                self.capacity_matrix[dest_id][origin_id] != 0:
                # Simple case: increase capacity and update Y
                new_capacity_matrix[origin_id][dest_id] += cap_incr_in
                new_capacity_matrix[dest_id][origin_id] += cap_incr_ag
                new_y_bus[origin_id][dest_id] = new_y
                new_y_bus[dest_id][origin_id] = new_y
                
                cost =  1.4 * distance
               
            else:
                # New line, but existing nodes
                new_capacity_matrix[origin_id][dest_id] += cap_incr_in
                new_capacity_matrix[dest_id][origin_id] += cap_incr_ag
                new_y_bus[origin_id][dest_id] = new_y
                new_y_bus[dest_id][origin_id] = new_y
                
                cost = 1.4 *distance
                 
                # Update a_matrix
                a_row = [0]*self.no_nodes
                a_row[origin_id] = 1
                a_row[dest_id] = -1
                new_a_matrix.append(a_row)
                
                # Calculate costs
                cost = max(cap_incr_in, cap_incr_ag) * 1.5
        
        else:
            # New nodes must be added.
            # supply vector length must be adjusted
            cost = 1
            
        self.create_transmission_network(new_y_bus, new_a_matrix, new_capacity_matrix)
        return cost
    

    def draw_network(self, flow_vector, supply, filename):
        """Creates a plot of the network with the flows using Networkx.
        """
        g = nx.DiGraph()
        label1 = {}     # node label
        label_node2 = {}
        label2 = {}     # line label
        pos1 = {}
        line_attributes = {}    
        
        
        # Preparing the nodes        
        for node in self.node_dictonary:
            g.add_node(node)
            pos1[node] = (self.node_dictonary[node]["x_loc"], \
                                        self.node_dictonary[node]["y_loc"])
            label1[node] = self.node_dictonary[node]["name"][:3]
            node += 1 
         
        # Adjusting position to improve readability
        # if test as easy way to only adjust node positions if NEM network
        # is used, otherwise leave as they are
        if self.node_dictonary[0]['name'] == "MELBOURNE":
            pos1[1] = (pos1[1][0],pos1[1][1]-1)               #LATROBE
            pos1[2] = (pos1[2][0]-0.1,pos1[2][1]+0.4)         #CVIC    
            pos1[5] = (pos1[5][0]-1.3,pos1[5][1]-1)           #GEELONG
            pos1[6] = (pos1[6][0]-0.9,pos1[6][1]-0.4)         #SWVIC
            pos1[8] = (pos1[8][0]+0.7,pos1[8][1])             #SYDNEY
            pos1[10] = (pos1[10][0]-1,pos1[10][1]+0.3)        #DARPOINT
            pos1[11] = (pos1[11][0],pos1[11][1]+1)            #WAGGA
            pos1[12] = (pos1[12][0]+0.8,pos1[12][1])          #CANBERRA    
            pos1[13] = (pos1[13][0]-0.8,pos1[13][1]+0.2)      #MTPIPER    
            pos1[14] = (pos1[14][0]-0.7,pos1[14][1]+1.5)      #BAYSWATER
            pos1[15] = (pos1[15][0],pos1[15][1]+1.5)          #ARMIDALE
            pos1[16] = (pos1[16][0]+0.7,pos1[16][1]+1.3)      #ERARING  
            pos1[17] = (pos1[17][0]+0.6,pos1[17][1]+0.9)      #BRISBANE    
            pos1[18] = (pos1[18][0]-0.5,pos1[18][1]+0.3)      #TARONG    
            pos1[19] = (pos1[19][0]-0.8,pos1[19][1])          #ROMA    
            
        
        for node in self.node_dictonary:
            if supply[0][node] != 0:
                label_node2[node] = round(supply[0][node],1)   

        #Preparing the lines
        for line in self.line_dictionary:
            origin = self.line_dictionary[line]["origin"]
            dest = self.line_dictionary[line]["destination"]
            g.add_edge(origin,dest)
            line_tuppel = ((origin,dest))
            line_attributes[line_tuppel] = {}
            
            # Attributes
            # ---width
            if self.line_dictionary[line]['capacity_in'] > 10000:
                line_attributes[line_tuppel]['width']=20
            elif self.line_dictionary[line]['capacity_in'] > 6000:
                line_attributes[line_tuppel]['width']=15
            elif self.line_dictionary[line]['capacity_in'] > 2000:
                line_attributes[line_tuppel]['width']=11
            elif self.line_dictionary[line]['capacity_in'] > 500:
                line_attributes[line_tuppel]['width']=8
            else:
                line_attributes[line_tuppel]['width']=4
            # ---color&style
            if abs(flow_vector.item(line)) > 0.01:                
                if abs(flow_vector.item(line))/self.line_dictionary[line]['capacity_in'] > 1.0:
                    line_attributes[line_tuppel]['color']='red' 
                    line_attributes[line_tuppel]['style']='solid'             
                elif abs(flow_vector.item(line))/self.line_dictionary[line]['capacity_in'] > 0.8:
                    line_attributes[line_tuppel]['color']='orange'
                    line_attributes[line_tuppel]['style']='solid'
                else:
                    line_attributes[line_tuppel]['color']='green'
                    line_attributes[line_tuppel]['style']='solid'
            else:
                line_attributes[line_tuppel]['color']='black'
                line_attributes[line_tuppel]['style']='dotted'    
            
            #label with arrows for direction...
            if pos1[origin][0] < pos1[dest][0]:
                if flow_vector.item(line) > 0.001:
                    label2[(origin,dest)] =  \
                        str(abs(round(flow_vector.item(line),1))) + " >>" +\
                        "\n"+str(line)+":(" + str(self.line_dictionary[line]['capacity_in']) + \
                        ", " + str(self.line_dictionary[line]['Y'])+ ")"
                elif flow_vector.item(line) < -0.001:   
                    label2[(origin,dest)] = "<< " + \
                        str(abs(round(flow_vector.item(line),1))) +\
                        "\n"+str(line)+":(" + str(self.line_dictionary[line]['capacity_ag']) + \
                        ", " + str(self.line_dictionary[line]['Y'])+ ")"
                else:
                    label2[(origin,dest)] = str(abs(round(flow_vector.item(line),1))) +\
                        "\n"+str(line)+":(" + str(self.line_dictionary[line]['capacity_in']) + \
                        ", " + str(self.line_dictionary[line]['Y'])+ ")"
            else:
                if flow_vector.item(line) > 0.001:
                    label2[(origin,dest)] = "<< " + \
                        str(abs(round(flow_vector.item(line),1)))  +\
                        "\n"+str(line)+":(" + str(self.line_dictionary[line]['capacity_in']) + \
                        ", " + str(self.line_dictionary[line]['Y'])+ ")"
                elif flow_vector.item(line) < -0.001:   
                    label2[(origin,dest)] = \
                        str(abs(round(flow_vector.item(line),1))) + " >>" +\
                        "\n"+str(line)+":(" + str(self.line_dictionary[line]['capacity_ag']) + \
                        ", " + str(self.line_dictionary[line]['Y'])+ ")"
                else:
                    label2[(origin,dest)] = str(abs(round(flow_vector.item(line),1))) +\
                        "\n"+str(line)+":(" + str(self.line_dictionary[line]['capacity_in']) + \
                        ", " + str(self.line_dictionary[line]['Y'])+ ")"
            
        
        #draw graph
        plt.figure(1,figsize=(20,25))
            
        nx.draw_networkx_nodes(g, pos = pos1,
                               with_labels = False,
                               node_color=(0,0,0.4),
                               node_size = 1000) 
        nx.draw_networkx_labels(g, pos=pos1,
                                labels = label1,
                                font_size = 9,
                                font_color='white',
                                font_weight = 'bold')
                                
        # Supply values as box next to node             
        for node in label_node2:
            if label_node2[node]>0:
                plt.text(pos1[node][0]-0.5, pos1[node][1]+0.3,
                        str(label_node2[node]),
                        size=10, weight='bold', stretch='condensed',
                        color='black', bbox=dict(facecolor='lightblue')
                        )
            else:
                plt.text(pos1[node][0]-0.4, pos1[node][1]+0.3,
                        str(label_node2[node]),
                        size=10, weight='bold', stretch='condensed',
                        color='black', bbox=dict(facecolor='orange')
                        )
        
        
        for edge in g.edges():
            nx.draw_networkx_edges(g, edgelist=[edge],
                               pos=pos1, 
                               arrows = False,
                               width = line_attributes[edge]['width'], 
                               edge_color = line_attributes[edge]['color'],
                               style = line_attributes[edge]['style'])
        
        nx.draw_networkx_edge_labels(g, pos = pos1,
                                edge_labels = label2,
                                edge_text_pos = 0.5,
                                font_size=6,
                                font_weight = 'bold')
     
                                
        plt.savefig(filename + ".pdf")
        