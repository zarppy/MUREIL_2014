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

""" Prints the docstring of the get_config_spec method from all python modules
    within the tree beneath the directory os.getcwd(). Prints to both stdout
    and to a file get_config_spec.txt
    EH, 14.01.2013
    
"""

import os
import inspect
import string
from tools import configurablebase
from generator import singlepassgenerator, txmultigeneratorbase


def list_modules(directory):
    mod_list = []
    top_dir_len = len(string.split(directory, "\\"))
    for dirpath, dirnames, filenames in os.walk(directory):
           path_list = string.split(dirpath, "\\")
           mod_pkg = string.join(path_list[top_dir_len:], ".")

           for file_name in filenames:
                  full_path = os.path.join(dirpath, file_name)
                  name, ext = os.path.splitext(full_path)
                  if ext == ".py":
                      x = len(file_name)-len(".py")
                      just_name = file_name[0:x]
                      if len(mod_pkg) > 0:
                          mod_full = mod_pkg + "." + just_name
                      else:
                          mod_full = just_name           

                      mod_list.append(mod_full)

    return mod_list


def my_import(name):
    """ Returns the module object from the string 'name'
    """   
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def print_docstring(module_list):
    """ Prints the docstring of the get_config_spec method from the modules
        within the list file_list"""
    out_file = os.path.join (cur_dir, "get_config_spec_help.txt");
    f = open(out_file, "w")
    for module_name in module_list:
        if string.find(module_name, ".")< 0:
            module = module_name
        else:
            module = my_import(module_name)       
        for name, obj in inspect.getmembers(module):          
                if inspect.isclass(obj):
                    if issubclass(obj, configurablebase.ConfigurableBase):
                        x = "------------------------------------------------------------------------------"
                        print x
                        f.write(x + '\n')
                        
                        x = "Module: " + module_name
                        print x
                        f.write(x + '\n')
                        
                        x = "Class:  " + name
                        print x
                        f.write(x + '\n')
                        
                        if issubclass(obj, singlepassgenerator.SinglePassGeneratorBase):
                            x = "Implements: SinglePassGeneratorBase"
                            print x
                            f.write(x + '\n')
                        
                        if issubclass(obj, txmultigeneratorbase.TxMultiGeneratorBase):
                            x = "Implements: TxMultiGeneratorBase"
                            print x
                            f.write(x + '\n')
                        
                        x = "------------------------------------------------------------------------------"
                        print x
                        f.write(x + '\n')
                        
                        x = str(obj.__doc__)
                        print x
                        f.write(x + '\n')

                        x = "---------------------"
                        print x
                        f.write(x + '\n')
                                                
                        x = str(obj.get_config_spec.__doc__)
                        print x
                        f.write(x + '\n')


    f.close


if __name__ == '__main__':    
    cur_dir = os.getcwd()
    mod_list= list_modules(cur_dir)
    print_docstring(mod_list)

