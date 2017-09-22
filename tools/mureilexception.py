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
"""Defines exception classes for mureil operations.
"""

import inspect

class MureilException(Exception):
    def __str__(self):
        return self.msg


class ProgramException(MureilException):
    """Exception raised for errors that are due to programming, not
    configuration.

    Attributes:
        msg  -- explanation of the error
        data -- a dict of any useful information to understand the error
    """

    def __init__(self, msg, data):
        self.msg = msg
        self.data = data
    

class AlgorithmException(MureilException):
    """Exception raised for errors found while running the algorithm.

    Attributes:
        msg  -- explanation of the error
        data -- a dict of any useful information to understand the error
    """

    def __init__(self, msg, data):
        self.msg = msg
        self.data = data


class ConfigException(MureilException):
    """Exception raised for problems in building and configuring.
    
    Attributes:
        msg -- explanation of the error
        data -- a dict of any useful information to understand the error
    """
    
    def __init__(self, msg, data):
        self.msg = msg
        self.data = data
 
 
class SolverException(MureilException):
    """Exception raised for issues solving a transmission or other 
    optimisation, e.g. an LP that is dual feasible.

    Attributes:
        msg -- explanation of the error
        data -- a dict of any useful information to understand the error
    """
    
    def __init__(self, msg, data):
        self.msg = msg
        self.data = data


class ClassTypeException(MureilException):
    """Exception raised when selected class does not implement required
    sub-class.
    
    Attributes:
        msg -- explanation of the error
        class_name -- the name of the class instantiated
        subclass_name -- the name of the class it should have implemented
        data -- a dict of any useful information to understand the error
    """
    
    def __init__(self, msg, class_name, subclass_name, data):
        self.msg = msg
        self.class_name = class_name
        self.subclass_name = subclass_name
        self.data = data
        

class ArrayDataTypeException(MureilException):   
    """Exception raised when array tested is not of the required type.
    
    Attributes:
        msg -- explanation of the error
        data -- a dict of any useful information to understand the error
    """
    
    def __init__(self, msg, data):
        self.msg = msg
        self.data = data


def find_caller(level):
    """Return a string with the caller of the function that called
    find_caller, and the line number of the call. Intended for use
    with exception calls.
    
    Inputs: level - integer - if 0, the caller of find_caller, 
        if 1, the caller above that
    """
    stack_tup = inspect.stack()[level + 1][1:3]
    return '{:s}:{:d}'.format(stack_tup[0], stack_tup[1])
