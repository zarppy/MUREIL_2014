#!/usr/bin/env python
print "Content-Type: text/json"
print
import rungedemo
from collections import defaultdict
import argparse
import json;
import cgi

flags = ['-f', 'GEconfig.txt', '-l', 'GEConfig.log']

form = cgi.FieldStorage()
input_data = form['sysdata'].value

all_years_out = rungedemo.rungedemo(flags, input_data)

print json.dumps(all_years_out);