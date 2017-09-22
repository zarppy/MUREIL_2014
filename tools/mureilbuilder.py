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
"""mureilbuilder.py collects functions that build a MUREIL simulation.

The intended use from the top-level is to call build_master with the command-line flags,
which will process any configuration files (identified as -f file), and any command-line
overrides, as listed in the read_flags function.
"""

import sys, os
import ConfigParser
import argparse
from tools import mureilbase, mureilexception
import importlib
import logging
import string
import copy
import types
import ast
import numpy

logger = logging.getLogger(__name__)


def build_master(raw_flags, extra_data = None):
    """Build the simulation master, using the flags from the command line or
    elsewhere. Intended to be called from runmureil.py or other simple function.
    An exception of base type MureilException will be raised in case of error.
    
    Inputs:
        raw_flags: flags from command line sys.argv[1:], or a list of strings
            such as ['-f', 'config.txt']
        extra_data: arbitrary extra data, if required.
        
    Outputs:
        master: a completely configured simulation master, ready to run.
    """
    files, conf_list = read_flags(raw_flags)
    full_config = accum_config_files(files)
    master = create_master_instance(full_config, conf_list, extra_data)
            
    return master


def read_config_file(filename):
    """Take in a filename and parse the file sections to a nested dict object.

    Keyword arguments:
    filename -- a string for the filename to read
    
    Returns:
    config -- a nested dict containing the sections (identified by []) in the configuration file, with
    each section dict containing its parameters.
    """

    parsed_config = ConfigParser.RawConfigParser()
    read_file = parsed_config.read(filename)

    # ConfigParser.read_file returns a list of filenames read
    if read_file == []:
        msg = 'Configuration file ' + filename + ' not opened.'
        logger.critical(msg)
        raise mureilexception.ConfigException(msg, {})

    config = {}

    for section in parsed_config.sections():
        this_list = {}
        for item in parsed_config.items(section):
            this_list[item[0]] = item[1]

        config[section] = this_list
    
    return config


def read_flags(flags, alt_args_list=None):
    """Process the command-line flags. 
    
    This:
    1) collects a list of configuration file names
    2) processes the logging flags, and initialises the logger
    3) collects the remaining flags which modify the simulation configuration

    Inputs:
        flags: a list of strings, for example ['-f', 'config.txt'], as would
            come from sys.argv[1:] as command-line arguments. Further
            details below.
        alt_args_list: optional. A dict specifying parameters that modify
            the configuration extracted from the files. A default is provided.
            Further details below.
            
    Outputs:
        files: a list of configuration filenames
        conf_list: a list of tuples of format ((section, param_name), param_value)
            as extracted from the flags using the args list.

    Details on flags:
        -f filename or --file filename: filename of a configuration file. Any number
            of these can be specified and will be applied in order of listing.

        Logging: see do_logger_setup below for more details.
        -l filename or --logfile filename: filename of the logfile.
        -d level or --debuglevel level: set the debuglevel. 
        --logmodulenames: if set (no value needed), log extra information.
        
        Default extra arguments:
        --iterations number: Set the number of iterations
        --seed number: Set the random seed for the simulation.
        --pop_size number: Set the population size, if a genetic algorithm.
        --processes number: Number of processes to spawn for parallel processing
        --output_file filename: Name of file to write output to
        --do_plots {True|False}: Draw pretty pictures when done
        --run_periods periods: Set the periods to run in a multi-period sim. Surround
             the list of periods in double-quotes e.g. --run_periods "2010 2020".
    
    Details on alt_args_list format:
        args_list is a dict.
         The key is the command line argument. At the command line, type
         --name value, e.g. --iterations 10
         The value is a tuple identifying where in the configuration to find the
         parameter to be modified, format (object, param_name).
         object is 'Master' for the master, or the name in the first position in
         the corresponding tuple in the master's get_config_spec for the others, 
         for example 'algorithm' (note not 'Algorithm'). 
         The param_name is the name of the parameter to modify as listed in the 
         object's get_config_spec function.
    """

    if alt_args_list:
        args_list = alt_args_list
    else:
        # See notes in docstring for function about args_list format
        args_list = {'iterations': ('Master', 'iterations'), 
                     'seed': ('algorithm', 'seed'),
                     'pop_size': ('algorithm', 'pop_size'),
                     'optim_type': ('Master', 'optim_type'),
                     'processes': ('algorithm', 'processes'),
                     'output_file' : ('Master', 'output_file'),
                     'do_plots' : ('Master', 'do_plots'),
                     'run_periods': ('Master', 'run_periods')}
                 
    parser = argparse.ArgumentParser()
    
    for arg in args_list:
        parser.add_argument('--' + arg)
  
    parser.add_argument('-f', '--file', action='append')
  
    parser.add_argument('-l', '--logfile')
    parser.add_argument('-d', '--debuglevel')
    parser.add_argument('--logmodulenames', action='store_true', default=False)
  
    args = parser.parse_args(flags)

    dict_args = vars(args)
    
    logger_config = {}
    for arg in ['logfile', 'debuglevel', 'logmodulenames']:
        logger_config[arg] = dict_args.pop(arg)

    do_logger_setup(logger_config)

    files = dict_args.pop('file')
    
    conf_list = []
    
    # Build up a list of ((section, param_name), value) tuples to 
    # describe the modifications to the configuration.
    for item in dict_args.keys():
        val = dict_args[item]
        if val is not None:
            conf_tup = (args_list[item], val)
            conf_list.append(conf_tup)
    
    return files, conf_list


def do_logger_setup(logger_config):
    """Set up the simulation logger.
    
    Inputs:
        logger_config: a dict with members (all optional) of:
            debuglevel: the Python logging level - defaults to INFO. One of
                DEBUG, INFO, WARNING, ERROR, CRITICAL.
            logmodulenames: if True, log the name of the module that the log
                message is sourced from.
            logfile: the full path of the log file.
            
    Outputs:
        None
    """

    for arg in ['debuglevel', 'logmodulenames', 'logfile']:
        if arg not in logger_config:
            logger_config[arg] = None

    # First, remove any existing handlers
    root = logging.getLogger()
    if root.handlers:
        handlers = copy.copy(root.handlers)
        for handler in handlers:
            root.removeHandler(handler)
 
    if logger_config['debuglevel'] is None:
        debuglevel = 'INFO'
    else:
        debuglevel = logger_config['debuglevel']

    numeric_level = getattr(logging, debuglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid debug level: %s' % debuglevel)

    # Now create the new handler

    if logger_config['logmodulenames']:
        format_string = '%(levelname)-8s : %(name)s : %(message)s'
    else:
        format_string = '%(levelname)-8s : %(message)s'

    formatter = logging.Formatter(format_string)

    if logger_config['logfile'] is not None:
        handler = logging.FileHandler(logger_config['logfile'], mode='w')
    else:
        handler = logging.StreamHandler()
 
    handler.setFormatter(formatter)
    root.addHandler(handler) 
    root.setLevel(numeric_level)


def accum_config_files(files):
    """Build a configuration structure from the list of files provided.

    Inputs:
        files: a list of string filenames, which are applied in turn, with the
            later files overwriting parameters already present.
        
    Outputs:
        config: a nested dict, with each section, identified by the [section_name]
            in the file, and each section a dict of parameter : value, where
            each value is a string.
    
    File format example (shortened - see each module's documentation and
        get_config_spec function for details of parameters):

    [Master]
    model: master.simplemureilmaster.SimpleMureilMaster
    iterations: 1000
    algorithm: Algorithm
    
    [Algorithm]
    model: algorithm.geneticalgorithm.Engine
    base_mute: 0.01
    processes: 0
    seed: 12345
    
    and the resulting output:
    config = {'Master': {'model': 'master.simplemureilmaster.SimpleMureilMaster',
        'iterations': '1000', 'algorithm': 'Algorithm'}, 'Algorithm': {'model':
        'algorithm.geneticalgorithm.Engine', 'base_mute': '0.01', 'processes': '0',
        'seed': '12345'}}
    """
    
    config = {}
    for conf_file in files:
        next_conf = read_config_file(conf_file)
        for section in next_conf.items():
            if section[0] in config:
                config[section[0]].update(section[1])
            else:
                config[section[0]] = section[1]

    return config
    

def apply_flags(full_config, flags):
    """Apply the modifiers are defined in the flags to the specified parameters within
    the full_config structure.
    
    Inputs:
        full_config: a nested dict - see accum_config_files above.
        flags: the conf_list output of read_flags above. Format is list of
            ((section, param_name), value)
            
    Outputs:
        None. full_config is modified in-place.
    """
    
    for flag in flags:
        pair, value = flag
        section, param = pair
        
        if (section == 'Master'):
            if param in full_config['Master']:
                full_config['Master'][param] = value
            else:
                msg = ('Flag ' + flag + ' alters parameter ' + param + 
                    ' in Master, but this parameter does not exist') 
                logging.error(msg)
                raise mureilexception.ConfigException(msg, {})
        else:
            if section in full_config['Master']:
                sect_name = full_config['Master'][section]
                if param in full_config[sect_name]:
                    full_config[sect_name][param] = value
                else:
                    msg = ('Flag ' + str(flag) + ' alters parameter ' + 
                        str(param) + ' in ' + str(section) + 
                        ', but this parameter does not exist')
                    logging.error(msg)
                    raise mureilexception.ConfigException(msg, {})
            else:
                msg = ('Flag ' + str(flag) + ' alters parameter ' +
                    str(param) + ' in ' + str(section) + 
                    ', but this section does not exist')
                logging.error(msg)
                raise mureilexception.ConfigException(msg, {})

    
def check_subclass(class_instance, baseclass):
    """Check if the class instance provided is a subclass of the 
    base class provided. 
    
    Inputs:
        class_instance: a constructed class object
        baseclass: a class object

    Ouputs:
        None. Raises ClassTypeException if it fails.
    """

    if not issubclass(class_instance.__class__, baseclass):
        msg = ('in ' + mureilexception.find_caller(1) + ' ' + 
            class_instance.__class__.__name__ + 
            ' does not implement ' + baseclass.__name__)
        logging.critical(msg)
        raise(mureilexception.ClassTypeException(msg,  
            class_instance.__class__.__name__, baseclass.__name__, {}))


def create_instance(full_config, global_config, section_name, baseclass,
    run_periods=None):
    """Create an instance of a model object, using section_name in the 
    full_config. Check that it is a subclass of the specified baseclass.
    Set the configuration of the object.
    
    Inputs:
        full_config: the configuration structure - a nested dict as
            {section_name: {param: value, ...}, ...}
        global_config: a dict of {param: value, ...} to be applied as global
            parameter variables.
        section_name: a string naming the section describing the object to 
            create. section_name must exist in full_config.
        baseclass: the class object of a required baseclass, e.g.
            mureilbase.ConfigurableInterface

    Outputs:
        class_instance: the constructed and configured model object
        
    Exceptions:
        the mureilexception.ConfigException will be raised if any problem,
            with the full stack-dump to the logfile.
    """
    check_section_exists(full_config, section_name)
    config = full_config[section_name]

    # Split the model name into module and class
    model_name = config['model']
    parts = model_name.split('.')
    module_name = string.join(parts[0:-1], '.')
    class_name = parts[-1]

    try:
        # Instantiate the model
        module = importlib.import_module(module_name)
        class_instance = getattr(module, class_name)()
    except TypeError as me:
        msg = ('Object (' + module_name + ', ' + class_name + 
            '), requested in section ' + section_name + 
            ' does not fully implement its subclasses')
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, {})
    except (ImportError, AttributeError, NameError) as me:
        msg = ('Object (' + module_name + ', ' + class_name + 
            '), requested in section ' + section_name + 
            ' could not be loaded.')
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, {})

    check_subclass(class_instance, baseclass)

    # Initialise the model
    config['section'] = section_name
    class_instance.set_config(config, global_config, run_periods)

    return class_instance
    
    
def create_master_instance(full_config, flags, extra_data):
    """Create an instance of the simulation master object.
    Set the configuration of the object.
    
    Inputs:
        full_config: the configuration structure - a nested dict as
            {section_name: {param: value, ...}, ...}
        flags: the conf_list output of read_flags above. Format is list of
            ((section, param_name), value)
        extra_data: arbitrary extra data to pass through to master's set_config(),
            if required

    Outputs:
        class_instance: the constructed and configured master object
        
    Exceptions:
        the mureilexception.ConfigException will be raised if any problem,
            with the full stack-dump to the logfile.
    """

    # Split the model name into module and class
    model_name = full_config['Master']['model']
    parts = model_name.split('.')
    module_name = string.join(parts[0:-1], '.')
    class_name = parts[-1]
    
    try:
        # Instantiate the model
        module = importlib.import_module(module_name)
        class_instance = getattr(module, class_name)()
    except TypeError as me:
        msg = ('Requested Master of module: ' + module_name + ', class: ' + 
            class_name + ' does not fully implement its subclasses')
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, {})
    except (ImportError, AttributeError, NameError) as me:
        msg = ('Requested Master of module: ' + module_name + ', class: ' + 
            class_name + ' could not be loaded.')
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, {})
        
    # The master is required to conform to mureilbase.MasterInterface
    check_subclass(class_instance, mureilbase.MasterInterface)

    # Now apply the flags
    
    # Apply defaults and then new config values in the full_config, so that
    # all the flags will have somewhere to map to. (Main consideration here
    # is that the 'algorithm' parameter is optional, defaulting to 'Algorithm').
    config_spec = class_instance.get_config_spec()
    new_config = collect_defaults(config_spec)
    new_config.update(full_config['Master'])
    new_config['section'] = 'Master'
    full_config['Master'] = new_config
    apply_flags(full_config, flags)
    
    # Now intialise the master
    class_instance.set_config(full_config, extra_data)
    
    return class_instance


def remove_config_spec(config_spec, param_name):
    """Remove the tuple with named 'param_name' from the
    config_spec, in-place.
    
    Inputs: 
        config_spec: list of tuples of format (param_name, conversion_function, default)
        param_name: string - name of parameter to remove
    """
    loc = 0
    for i in range(len(config_spec)):
        if (config_spec[i][0] == param_name):
            loc = i
    del config_spec[loc]
        

def collect_defaults(config_spec):
    """Extract the default values from config_spec as a dict of param_name:value.

    Inputs:
        config_spec: list of tuples of format (param_name, conversion_function, default),
            where default = None means no default.
        
    Outputs:
        defaults: dict of param_name:default_value, only where a default was specified.
    """

    defaults = {}
    for config_tup in filter(lambda t: t[2] is not None, config_spec):
        defaults[config_tup[0]] = config_tup[2]
    return defaults
    

def apply_conversions(config, config_spec):
    """Apply the conversion functions listed in config_spec to the config dict, in-place.
    If the value is a string, check if it starts with {, and if so, interpret it as
    a period-by-period value - e.g. {2010:400, 2030:450}.
    
    Inputs:
        config: dict of param_name:value, where value may be a string.
        config_spec: list of tuples of format (param_name, conversion_function, default),
            where conversion_function is any function taking one parameter, including
            type-conversion functions.
        
    Outputs:
        None. config is modified in-place.
    """
    
    # Now convert, first checking for curly brackets to indicate multiple time periods
    
    for (conf_name, conv_fn, default) in config_spec:
        if conf_name in config:
            curr_val = config[conf_name]

            if isinstance(curr_val, str):
                # Multiple time periods is specified by {}, and separated by commas
                curr_val = curr_val.strip()
                if (len(curr_val) > 0) and (curr_val[0] == '{'):
                    if not (curr_val[-1] == '}'):
                        raise mureilexception.ConfigException(
                            'When parsing configuration, found string ' + curr_val +
                            ' which begins with { but does not end with }', {})
                            
                    parse_str = curr_val[1:-1]
                    config[conf_name] = new_val = {}
                    vals = parse_str.split(',')
                    for val in vals:
                        try:
                            (period, value) = val.split(':')
                        except ValueError:
                            raise mureilexception.ConfigException(
                                'When parsing configuration, found string ' + curr_val +
                                ' which includes an entry that is not period:value', {})
                        if conv_fn is None:
                            new_val[int(period)] = value.strip()
                        else:
                            new_val[int(period)] = conv_fn(value)
                else:
                    if conv_fn is not None:
                        config[conf_name] = conv_fn(curr_val)
            elif isinstance(curr_val, dict):
                # This is already a dict - just re-apply the type conversions to be sure
                for key, value in curr_val.iteritems():
                    if conv_fn is not None:
                        curr_val[key] = conv_fn(curr_val[key])
            else:
                # It's not a string - just make sure it's what we want
                if conv_fn is not None:
                    config[conf_name] = conv_fn(curr_val)


def check_required_params(config, config_spec):
    """Check that all of the parameters listed in config_spec are provided in config.
    
    Inputs:
        config: dict of param_name:value, where value may be a string.
        config_spec: list of tuples of format (param_name, conversion_function, default),

    Outputs:
        None, but raises as ConfigException if a problem is found.
    """
    
    for config_tup in config_spec:
        if config_tup[0] not in config:
            msg = (config['model'] + ' requires parameter ' + config_tup[0] + 
                ' but it is not provided in section ' + config['section'])
            logging.critical(msg)
            raise mureilexception.ConfigException(msg, {})


def check_for_extras(config, config_spec):
    """Check that there aren't any extra parameters, not listed in config_spec,
    in config.
    
    Inputs:
        config: dict of param_name:value, where value may be a string.
        config_spec: list of tuples of format (param_name, conversion_function, default),

    Outputs:
        None, but raises as ConfigException if a problem is found.
    """
    for config_item in config:
        if config_item not in ['model', 'section']:
            if filter(lambda t: t[0] == config_item, config_spec) == []:
                logging.warning(config['model'] + ' not expecting parameter ' + 
                    config_item + ' in section ' + config['section'])


def check_section_exists(full_config, section):
    """Check that section exists in full_config, and raise an exception if not.
    
    Inputs:
        full_config: the configuration structure - a nested dict as
            {section_name: {param: value, ...}, ...}
        section: the string section name
        
    Outputs:
        None, but raises ConfigException if a problem.
    """

    if section not in full_config:
        msg = ('Section ' + section + ' required in config, as specified in Master')
        logger.critical(msg)
        raise mureilexception.ConfigException(msg, {})

            
def update_with_globals(new_config, global_conf, config_spec):
    """Update the new_config with parameters in config_spec that are found in
    global_conf. Overwrites existing parameter values in new_config.
    
    Inputs:
        new_config: a dict of {param_name:value, ...}, may be empty.
        global_conf: a dict of {param_name:value, ...}, may be empty.
        config_spec: list of tuples of format (param_name, conversion_function, default)
        
    Outputs:
        None. new_config is modified in-place.
    """
    for tup in config_spec:
        if tup[0] in global_conf:
            new_config[tup[0]] = global_conf[tup[0]]


def make_string_list(val):
    """Check if the item is a string, and if so, apply str.split() to make a list of
    strings. If it's a list of strings, return as is. 
    
    Used as a conversion function for apply_conversions above.
    
    Inputs:
        val: value, either string or list of strings
        
    Outputs:
        list of strings

    This allows configuration parameters such as dispatch_order to be initialised 
    from a string or from a config pickle.
    """
    if isinstance(val, str):
        return str.split(val)
    else:
        return val


def make_int_list(val):
    """Check if the item is a string, and if so, apply str.split() to make a list of
    ints. If it's a list of ints, return as is. 
    
    Used as a conversion function for apply_conversions above.

    Inputs:
        val: value, either string or list of ints
        
    Outputs:
        list of ints

    This allows configuration parameters such as dispatch_order to be initialised from 
    a string or from a config pickle.
    """
    if isinstance(val, str):
        return map(int, str.split(val))
    else:
        return val


def make_float_list(val):
    """Check if the item is a string, and if so, apply str.split() to make a list of
    floats. If it's a list of floats, return as is. 
    
    Used as a conversion function for apply_conversions above.

    Inputs:
        val: value, either string or list of floats
        
    Outputs:
        list of floats

    This allows configuration parameters such as dispatch_order to be initialised from 
    a string or from a config pickle.
    """
    if isinstance(val, str):
        return map(float, str.split(val))
    else:
        return val


def string_to_bool(val):
    """Convert 'False' to False and 'True' to True and everything else to 'False'
    
    Used as a conversion function for apply_conversions above.
    
    Inputs:
        val: either 'True' or 'False', or a boolean
        
    Outputs:
        boolean
    """
    if type(val) == types.BooleanType:
        return val
    else:
        return (val.strip() == 'True')


def python_eval(val):
    """If val is a string, evaluate using python to get a python object.
    If not a string, leave untouched.
    
    Inputs:
        val: a string representing a python expression, or other type which will be ignored
        
    Outputs:
        val, if the input val was not a string, or a python object.
    """
    if isinstance(val, str):
        return ast.literal_eval(val)
    else:
        return val
    
    
def supply_single_pass_data(gen, data, gen_type):
    """Make the call to set_data for gen, extracting the relevant series from data.
    
    Inputs:
        gen: an object subclassed from SinglePassGeneratorBase
        data: an object subclassed from DataSinglePassBase
        gen_type: the name the calling Master uses to refer to the generator, for
            the exception message.
              
    Outputs:
        None. Raises a ConfigException if a generator requests a series that is not
        provided.
    """
    
    data_req = gen.get_data_types()
    this_data_dict = {}
    for key in data_req:
        try:
            this_data_dict[key] = data.get_timeseries(key)
        except mureilexception.ConfigException:
            msg = 'Data series ' + str(key) + ' requested by ' + gen_type + ', but is not provided.'
            raise mureilexception.ConfigException(msg, {})

    gen.set_data(this_data_dict)


def add_param_starts(this_starts, params_req, global_conf, run_period_len, start_values_min, start_values_max):
    """Process the param starts information taken from the generator, and add it to
    the array being constructed.
    
    Inputs:
        this_starts: a tuple with (starts_min, starts_max), the output from a generator's
            get_param_starts() function.
        params_req: integer, the number of parameters this generator requires
        global_conf: a dict including 'min_param_val' and 'max_param_val'
        run_period_len: the number of periods to run for
        start_values_min: the array to append the min start values to
        start_values_max: the array to append the max start values to

    Outputs:
        start_values_min, start_values_max, updated versions (not necessarily in-place)
    """
    (starts_min, starts_max) = this_starts
    starts_min = numpy.array(starts_min)
    starts_max = numpy.array(starts_max)

    if starts_min.size == 0:
        start_values_min = numpy.hstack((start_values_min, (
            (numpy.ones((run_period_len, params_req)) * 
            global_conf['min_param_val']).tolist())))
    else:
        start_values_min = numpy.hstack((start_values_min, starts_min))

    if starts_max.size == 0:
        start_values_max = numpy.hstack((start_values_max, (
            (numpy.ones((run_period_len, params_req)) * 
            global_conf['max_param_val']).tolist())))
    else:
        start_values_max = numpy.hstack((start_values_max, starts_max))

    return start_values_min, start_values_max

