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
"""Test of config-spec components of tools/mureilbuilder.py.

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_config_spec.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy

from tools import mureilexception, testutilities

from tools import mureilbuilder

class TestApplyConversions(unittest.TestCase):
    def setUp(self):
        testutilities.unittest_path_setup(self, __file__)
        self.config_spec = [
            ('int', int, None),
            ('int_list', mureilbuilder.make_int_list, None),
            ('str_list', mureilbuilder.make_string_list, None),
            ('bool1', mureilbuilder.string_to_bool, None),
            ('bool2', mureilbuilder.string_to_bool, None),
            ('string', None, None)
            ]

    def tearDown(self):
        os.chdir(self.cwd)

    def test_convert_single(self):
        config1 = {
            'int': '35',
            'str_list': 'abc def ghf',
            'string': 'This is a string',
            'rubbish': 'rubbish stuff',
            'bool1': 'True',
            'int_list': '45 66 55 33',
            'bool2': 'False'
        }
        
        exp_config1 = {
            'int': 35,
            'str_list': ['abc', 'def', 'ghf'],
            'string': 'This is a string',
            'rubbish': 'rubbish stuff',
            'bool1': True,
            'int_list': [45, 66, 55, 33],
            'bool2': False
        }
        
        # Apply conversions to the string inputs
        mureilbuilder.apply_conversions(config1, self.config_spec)
        self.assertTrue((config1 == exp_config1))
        
        # And apply to pre-converted values
        mureilbuilder.apply_conversions(config1, self.config_spec)
        self.assertTrue((config1 == exp_config1))


    def test_convert_multiple(self):
        config1 = {
            'int': '{2010:35, 2020: 53}',
            'str_list': '{2000:  abc def ghf , 2010: bbg ddf} ',
            'string': '{334: This is a string, 443: and another one } ',
            'rubbish': 'rubbish stuff',
            'bool1': 'True',
            'int_list': '{3040: 45 66 55 33, 4003: 44 33 44 33}  ',
            'bool2': '{300: False, 322: True}'
        }
        
        exp_config1 = {
            'int': {2010: 35, 2020: 53},
            'str_list': {2000: ['abc', 'def', 'ghf'], 2010: ['bbg', 'ddf']},
            'string': {334: 'This is a string', 443: 'and another one'},
            'rubbish': 'rubbish stuff',
            'bool1': True,
            'int_list': {3040: [45, 66, 55, 33], 4003: [44, 33, 44, 33]},
            'bool2': {300: False, 322: True}
        }
        
        # Apply conversions to the string inputs
        mureilbuilder.apply_conversions(config1, self.config_spec)
        self.assertTrue((config1 == exp_config1))
        
        # And apply to pre-converted values
        mureilbuilder.apply_conversions(config1, self.config_spec)
        self.assertTrue((config1 == exp_config1))


if __name__ == '__main__':
    unittest.main()
    
