README - simple instructions on how to run MUREIL
Marcelle Gannon marcelle.gannon@gmail.com
9 March 2013

----------
This README.txt is superseded by the document in doc/mureil_software.pdf.
----------


----------
Pre-configured example
----------

At a command line outside python:

> python runmureil.py -f asst5_config.txt 

produces the following output:

CRITICAL : Run started at Thu Dec 20 10:42:48 2012
CRITICAL : Run time: 8.50 seconds
INFO     : best gene was: [854, 388, 83, 850, 1764, 2163]
INFO     : on loop 976, with score -189399.751200
INFO     : solar ($M 12420.00) : Solar_Thermal with capacities (MW): 8540.00  3880.00 
INFO     : wind ($M 97200.00) : Wind with capacities (MW): 830.00  8500.00  17640.00  21630.00 
INFO     : fossil ($M 79779.75) : Instant Fossil Thermal, max capacity (MW) 16723.80
INFO     : Total cost ($M): 189399.75

See the test_ directories for more comprehensive and up to date tests.

------------
Command line
------------

Options are:
-f config-file - you can have as many of these as you like. They will accumulate the configs
	with later files taking precedence. See 'batch files' below for an example of this.

--iterations count - set the number of iterations to do
--seed seed - set the random seed.
--pop_size size - the size of the gene population
--processes count - how many processes to spawn in multiprocessing
--output_file filename - the name of the pickle file to write output to
--do_plots {False,True} - either False or True to print plots at the end of run

-l filename - filename for a log file. If not set, will print to screen.
-d debuglevel - one of DEBUG, INFO, WARNING, ERROR, CRITICAL. INFO is recommended.

------------
Config file format
------------

See sample_config.txt for an example. Note that each section (in square brackets) in the file is
referenced in the [Master] section so the master knows where to look. Variables in the [Global]
section are passed to all other models for their use. These may be overwritten by locally set values.

The 'simplemureilmaster.py' master does the following calculations on the global values:
- creates timestep_mins from timestep_hrs and vice-versa
- computes 'time_scale_up_mult', to allow extrapolation from the data set length to the set
	'time_period_yrs'. This is recommended for use with carbon emission calculations.
- computes 'variable_cost_mult', at present just the same as time_scale_up_mult, but this could
	have discounting added later.

See the function 'get_config_spec' in each model's code to see the variables they expect.
You can run 
> python get_config_spec_help.py
to collect all the get_config_spec output into one place. It will be written to
get_config_spec_help.txt.


-------------
Data
-------------

Use of the data/ncdata.py model is recommended. This allows you to configure which data series
come from which NetCDF format file, checks they are all the right length, and removes
NaNs.

Note that the SinglePassVariableGenerator model assumes the data is read in as capacity factor fractions.

-------------
Batch script
-------------

See runmulti.py for an example of a batch processing script that creates a bunch
of extra config files for a series of values of a parameter, runs a simulation these
files in addition to the base config file, then collects the results. 

Note that you can update any of the 
configuration script values in this way - including 'model', and you can add extra
parameters such as 'install' as required - just put them in the extra config file.


--------------
Helper functions
--------------

The following scripts are in the mureil-ga directory. Run at command prompt:

----
python plotpickle.py pickle_filename

to draw plots of cumulative and separate power timeseries

----
python printpickle.py pickle_filename > output_filename

to dump the pickle file to a text file


------------
Testing
------------

The directories test_hydro and test_regression contain test scripts that use the
Python unittest framework. More tests can be added in a similar way. See the unittest
documentation in the Python documentation.

In test_hydro:
python test_basicpumpedhydro.py -v

In test_regression/mg_test1 and test_regression/rhuva_test1 run:
python test.py -v

and expect it to finish with 'ok'.

From the mureil-ga directory, run:
python -m unittest discover -v
and you should see all of the current tests run.

--------------
Profiling
--------------

Profiling will help identify which parts of the program are taking the longest to run.

See:
http://docs.python.org/2/library/profile.html#instant-user-s-manual

Run:

python -m cProfile runmureil.py -f sample_config.txt > sample_config.prof

and browse sample_config.prof to find where the time goes. It's the 'total_time'
column that's probably of most interest. With sample_config.txt you can see that
'total_time' for the calculate function is most of the run time of the sim. This
is not surprising as this is the only calculate function that has a looped
calculation in it - the others are all matrix maths which numpy does in a flash.

There are ways to sort and search this information - see the help file for details.
Basic rule is - don't spend time optimising your code until you know what's taking
all the time to run.


-------------------
SVN
-------------------

SVN is the version control system on google code. 

A list of useful commands here:
http://www.thegeekstuff.com/2011/04/svn-command-examples/

The checkout instructions are on google code -> source -> checkout.

Most users will use 'add', 'commit', 'update', 'status' and 'diff'. It's
good practice before doing a 'commit' to do 'status' and then do
'diff' on any files with an 'M' (for Modified) in front of them, to
be sure you know what you've changed.

If you do an 'update' and it says that the merge failed, the file will be in 
conflict. SVN tries to combine changes that someone else has checked in
with changes that you may have made locally. If you edit different parts of the
same file this is likely to work. If you have edited the same parts of the
file, then it will report a conflict.

See here for how to resolve it:
http://www.websanova.com/tutorials/svn/svn-conflicts

Don't whatever you do choose the (mc) mine-conflict option if 'update' offers
you that. What that will do
is ignore whatever you just updated and just use your new version - so you may
be throwing away someone else's edits. This is often hard to find out and makes
people very cross!  (p) postpone is the best option.


---------------------
SlowResponseThermal
---------------------

In the module thermal/slowresponsethermal.py there are two classes - SlowResponseThermal,
which takes an optimisable param for capacity in MW, and 
SlowResponseThermalFixed which takes an extra configuration parameter of
'fixed_capacity' for a fixed capacity in MW. There's an example config file
using both of these in slow_ramp_config.txt.

The current (21/12/12) implementation of both these classes just runs the
generator at full power regardless of demand. The calculate_cost_and_output
function is in need of filling in! 

A unittest test case for these is set up in test_slowresponsethermal. See the
notes above on testing, and look at test_basicpumpedhydro.py for a more
detailed unittest example. From the test_slowresponsethermal directory
just run 'python test_slowresponsethermal.py -v' and it will execute all
the tests you have define there. You can add print statements to see what's
going on. You will need to update the expected outputs when you update the
code to do something more interesting.

To instantiate the SlowResponseThermal class within a python session, you
can do what follows, from within the test_thermal.
If you run it like this within
Python you can then play with the cost and ts variables, and alter the
config parameters and rem_demand and ts_demand.

The script interactive_test_thermal.py in test_thermal sets up the paths so
they work and instantiates example config, ts_demand and rem_demand arrays.

Marcelle@eMachine-PC /c/Data/Marcelle_Uni/MUREIL/mureil-ga/test_thermal
$ python
Python 2.7.3 (default, Apr 10 2012, 23:31:26) [MSC v.1500 32 bit (Intel)] on win
32
Type "help", "copyright", "credits" or "license" for more information.
>>> from interactive_test_thermal import *
>>> print cost
1500.0225
>>> print ts
[ 500.  500.  500.]
>>> t.config['capex'] = 1.0
>>> new_cost, new_ts = t.calculate_cost_and_output([5], rem_demand)
>>> new_cost
500.02249999999998
>>> new_ts
array([ 500.,  500.,  500.])
>>> print t.config
{'carbon_price_mwh': 5.0, 'ramp_time_mins': 240.0, 'fuel_price_mwh': 10.0, 'cape
x': 1.0, 'type': 'bc', 'timestep_hrs': 1.0, 'variable_cost_mult': 1.0}
>>> print t.ts_demand
[1 2 3]

--------------------------
GE demo
--------------------------

The GE demo is run from model_web.py if you are a webserver, and
model_file.py if you want to test it locally. model_file.py sets up
a couple of parameters and then calls rungedemo.py. 

--------------------------
Initialising the Gene values
--------------------------

The initial gene values can be constrained within a smaller range
than the specified min/max by setting (in the singlepassvariablegenerator
models only) the 'start_min_param' and 'start_max_param' configuration
parameters. 

To initialise the whole population to identical gene values, read from
a file, see runmureil_gene.py. Run as follows:

> python runmureil_gene.py test.pkl

where test.pkl has been saved from a previous run (or you have created it),
so it contains a dict with 'best_gene' as a member.

HELP:

run python from the top directory
import module
help(module)

