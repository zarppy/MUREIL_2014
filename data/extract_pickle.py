import cPickle 
import numpy as np
import pupynere as nc

dir = '/home/STUDENT/rhuva/GA-working-copy/'
file = 'asympt_config_full_III'

f = open(dir+file+'.pkl', 'r')
p = cPickle.Unpickler(f)
data = p.load()

ts_demand = data['ts_demand']

best_results = data['best_results']

capacity = best_results['capacity']
wind_capacity = capacity['wind']
solar_capacity = capacity['solar']

output = best_results['output']
wind_out = output['wind']
solar_out = output['solar']
hydro_out = output['hydro']
gas_out = output['fossil']

nstations_w = len(wind_capacity)
nstations_s = len(solar_capacity)
nsteps = len(wind_out)

#Write to netcdf file:

o = nc.netcdf_file(file+'.nc', 'w')

o.createDimension('nstations_wind', nstations_w)
o.createDimension('nstations_solar', nstations_s)
o.createDimension('nsteps', nsteps)

wind_output = o.createVariable("ts_wind", 'f', ('nsteps',))
solar_output = o.createVariable("ts_solar", 'f', ('nsteps',))
hydro_output = o.createVariable("ts_hydro", 'f', ('nsteps',))
gas_output = o.createVariable("ts_gas", 'f', ('nsteps',))
demand_output = o.createVariable("ts_demand", 'f', ('nsteps',))

wind_cap = o.createVariable("wind_cap", 'f', ('nstations_wind',))
solar_cap = o.createVariable("solar_cap", 'f', ('nstations_solar',))

wind_output[:] = wind_out
solar_output[:] = solar_out
hydro_output[:] = hydro_out
gas_output[:] = gas_out
demand_output[:] = ts_demand

wind_cap[:] = wind_capacity
solar_cap[:] = solar_capacity

o.close()







