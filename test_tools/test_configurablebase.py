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
"""Test of ConfigurableBase and ConfigurableMultiBase.

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_configurablebase.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy

from tools import mureilexception, testutilities
from tools import mureilbuilder

from tools import configurablebase

class TestExpandConfig(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_expand(self):
        cmb = configurablebase.ConfigurableMultiBase()
        cmb.extra_periods = [1990, 2000]
        cmb.config = {
            'int': {2010: 35, 2020: 53},
            'str_list': {2000: ['abc', 'def', 'ghf'], 2010: ['bbg', 'ddf']},
            'string': {2000: 'This is a string', 2020: 'and another one'},
            'rubbish': 'rubbish stuff',
            'bool1': True,
            'int_list': {2010: [45, 66, 55, 33], 2030: [44, 33, 44, 33]},
            'bool2': {2000: False, 2040: True},
        }
        
        cmb.expand_config([2000, 2010, 2030, 2020])
        
        #import pprint
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(cmb.period_configs)

        exp_config = { 
            1990: {   'bool1': True,
                      'bool2': False,
                      'int': 35,
                      'int_list': [45, 66, 55, 33],
                      'rubbish': 'rubbish stuff',
                      'str_list': ['abc', 'def', 'ghf'],
                      'string': 'This is a string'},
            2000: {   'bool1': True,
                      'bool2': False,
                      'int': 35,
                      'int_list': [45, 66, 55, 33],
                      'rubbish': 'rubbish stuff',
                      'str_list': ['abc', 'def', 'ghf'],
                      'string': 'This is a string'},
            2010: {   'bool1': True,
                      'bool2': False,
                      'int': 35,
                      'int_list': [45, 66, 55, 33],
                      'rubbish': 'rubbish stuff',
                      'str_list': ['bbg', 'ddf'],
                      'string': 'This is a string'},
            2020: {   'bool1': True,
                      'bool2': False,
                      'int': 53,
                      'int_list': [45, 66, 55, 33],
                      'rubbish': 'rubbish stuff',
                      'str_list': ['bbg', 'ddf'],
                      'string': 'and another one'},
            2030: {   'bool1': True,
                      'bool2': False,
                      'int': 53,
                      'int_list': [44, 33, 44, 33],
                      'rubbish': 'rubbish stuff',
                      'str_list': ['bbg', 'ddf'],
                      'string': 'and another one'}}
    
        self.assertTrue((cmb.period_configs == exp_config))
        


if __name__ == '__main__':
    unittest.main()
    
