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
"""Functions for use in testbench operation.
"""

import os
from tools import mureilbuilder
import numpy

def unittest_path_setup(self, thisfile):
    """Set up all the paths to run the unit tests. Required when using
    unittest discover.
    
    Determines the directory the test itself is in, and the
    directory it is being called from. Changes into the test directory
    to run the test. Sets the cwd variable in self to the working directory.
    
    Also resets the logger functionality, sending output to stdout.
    
    Inputs:
        self: the unittest.TestCase object calling this function
            (specific object type is irrelevant - just needs to be an object)
        thisfile: the __file__ value for the test module
    
    Outputs:
        None
    """
    
    test_dir = os.path.dirname(os.path.realpath(thisfile)) 
    self.cwd = os.getcwd()
    os.chdir(test_dir)
    mureilbuilder.do_logger_setup({})


def make_sane_equality_array(array_type):
    """Returns a SaneEqArr constructed from the array_type.
    
    Inputs:
        array_type: an array-type object e.g. a list, that would
            be passed to numpy.array(array_type) typically.
    
    Outputs:
        sae: a SaneEqualityArray array, useful for equality comparison
            in unittests.
    """

    temp = numpy.array(array_type)
    return SaneEqArr(temp.shape, temp.dtype, temp)


class SaneEqArr(numpy.ndarray):
    """SaneEqArr (SaneEqualityArray) overrides the numpy.ndarray equality test so that
    it compares all values in arrays when doing a comparison. To use,
    make sure the object on the left site of the comparison has all its
    arrays defined like this.
    
    from:
    http://stackoverflow.com/questions/14246983/compare-assert-equality-of-two-complex-data-structures-containing-numpy-arrays
    
    e.g.
    
    sea = testutilities.make_sane_equality_array
    exp_result = {'list1': sea([1, 2, 3, 4])}
    self.assertTrue((exp_result == result))
    """
        
    def __eq__(self, other):
        return (isinstance(other, numpy.ndarray) and 
            self.shape == other.shape and 
            numpy.allclose(self, other))