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
import runmureil
import pickle

# Example script that generates a batch of
# config files, to run with asst5_config.txt, and
# then runs them.

solar_cost_list = [1, 2, 3]

# Create the config files
for solar_cost in solar_cost_list:
    filename = 'solar_{:d}_config.txt'.format(solar_cost)
    f = open(filename, 'w')
    f.write('[Solar]\n')
    f.write('capex: {:d}\n'.format(solar_cost))
    f.write('[Master]\n')
    f.write('output_file: solar_{:d}.pkl\n'.format(solar_cost))
    f.close()

# Run the sims
for solar_cost in solar_cost_list:
    filename = 'solar_{:d}_config.txt'.format(solar_cost)
    logname = 'solar_{:d}.log'.format(solar_cost)
    runmureil.runmureil(['-f', 'asst5_config.txt', '-f', filename, '-l', logname,
        '--iterations', '100'])

# Collect the results
for solar_cost in solar_cost_list:
    pkl_name = 'solar_{:d}.pkl'.format(solar_cost)
    p = pickle.load(open(pkl_name, 'rb'))
    costs = p['best_results']['cost']
    total_cost = sum([pair[1] for pair in costs])
    capacities = p['best_results']['capacity']
    
    print '=========================================='
    print 'Solar Capex = {:d}'.format(solar_cost)
    print 'Total Cost $M = {:.2f}'.format(total_cost)
    print 'Capacities:'
    print capacities
    
