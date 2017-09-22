#!/usr/bin/env python
print "Content-Type: text/json"
print
import rungedemo
from collections import defaultdict
import argparse
import json;

flags = ['-f', 'GEconfig.txt', '-l', 'GEConfig.log']

# file_path = 'new_values_to_model.js'
# 
# with open(file_path) as f:
#     input_data = f.read()

import cgi
form = cgi.FieldStorage()
input_data = form['sysdata'].value

# Note that the format of the results are as follows:
# 'cost' - per generation type, total for that decade, in $M
# 'output' - per generation type, MWh per year
# 'reliability' - the percentage of hours where demand was not met
# 'co2_tonnes' - in tonnes, total for that decade
# 'period_cost' - total of all 'cost' values, for that decade, in $M,
#      without discounting.
# 'discounted_cumulative_cost' - total of all 'period_cost' values including
#      the current decade, with discounting at the configured discount rate,
#      assuming all costs incurred at the start of the decade.
all_years_out = rungedemo.rungedemo(flags, input_data)

print json.dumps(all_years_out);