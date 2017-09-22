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
import abc
import copy

class ConfigurableInterface(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def __init__(self):
        pass
        
    @abc.abstractmethod
    def set_config(self, config, global_config=None):
        pass
    
    @abc.abstractmethod
    def get_config(self):
        pass
    
    @abc.abstractmethod
    def get_config_spec(self):
        pass


class MasterInterface(ConfigurableInterface):

    @abc.abstractmethod
    def set_config(self, full_config, extra_data=None):
        pass

    @abc.abstractmethod
    def run(self, extra_data=None):
        pass

    @abc.abstractmethod
    def finalise(self):
        pass
        
    @abc.abstractmethod
    def get_full_config(self):
        pass
        

class DataSinglePassInterface(ConfigurableInterface):

    @abc.abstractmethod
    def get_timeseries(self, ts_name):
        pass

    @abc.abstractmethod
    def get_ts_length(self):
        pass

