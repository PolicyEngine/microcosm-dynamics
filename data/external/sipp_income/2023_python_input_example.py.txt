'''
The following code is an example of reading the pipe-delimited Survey of Income and Program Participation (SIPP) 
   data into an Pandas dataframe. Specifically, this code loads in both the primary data file 
   and the calendar-year replicate weights file (as opposed to the longitudinal replicate weights). These files are 
   separate downloads on the SIPP website.
SIPP data are in person-month format, meaning each record represents one month for a specific person.
   Unique persons are identified using SSUID+PNUM. Unique households are identified using SSUID+ERESIDENCEID. For 
   additional guidance on using SIPP data, please see the SIPP Users' Guide at <https://www.census.gov/programs-surveys/sipp/guidance/users-guide.html>
This code was written in Python 3, and requires version 0.24 or higher of the Pandas module. 
Note the use of 'usecols' in the first pd.read_csv statement. Most machines do not have enough memory to read
   the entire SIPP file into memory. Use 'usecols' to read in only the columns you are interested in. If you
   still encounter an out-of-memory error, either select less columns, or consider using the Dask module.
Run this code in the same directory as the extracted data.
Please contact the SIPP Coordination and Outreach Staff at census.sipp@census.gov if you have any questions.
'''

#Import the pandas module. This code requires version 0.24 or higher
#	in order to use the Int64 and Float64 data types, which allow for
#	missing values
import pandas as pd

#Read in the primary data file schema to get data-type information for
#	each variable.
rd_schema = pd.read_json('pu2023_schema.json')

#Read in the replicate weight data file schema to get data-type information 
#	for each variable.
rw_schema = pd.read_json('rw2023_schema.json')

#Define Pandas data types based on the schema data-type information for both schema dataframes
rd_schema['dtype'] = ['Int64' if x == 'integer' \
			else 'object' if x == 'string' \
			else 'Float64' if x == 'float' \
			else 'ERROR' \
			for x in rd_schema['dtype']]

rw_schema['dtype'] = ['Int64' if x == 'integer' \
			else 'object' if x == 'string' \
			else 'Float64' if x == 'float' \
			else 'ERROR' \
			for x in rw_schema['dtype']]

#Read in the primary data
df_data = pd.read_csv("pu2023.csv",\
		names=rd_schema['name'],\
		#dtype expects a dictionary of key:values
		dtype = dict([(i,v) for i,v in zip(rd_schema['name'], rd_schema['dtype'])]),\
		#files are pipe-delimited
		sep='|',\
		header=0,\
		#Add variables for analysis here. If you receive an out-of-memory error,
		#	either select less columns, or consider using the Dask module
		usecols = [
		#Common record-identification variables
		'SSUID','PNUM','MONTHCODE','ERESIDENCEID','ERELRPE','SPANEL','SWAVE',\
		#The base weight and monthly in-survey-universe indicator
		'WPFINWGT','RIN_UNIV',\
		#Common demographics variables, including age at time of interview (TAGE)
		#	and monthly age during the reference period (TAGE_EHC)
		'ESEX','TAGE','TAGE_EHC','ERACE','EORIGIN','EEDUC',\
		#Additional variables for analysis
		'TPTOTINC','RTANF_MNYN'\
			]
		)
#preview the data		
print(df_data.head())

#check some unweighted means against the validation xls file to help ensure that the data
#	were read in correctly. Note that the validation xls files do not include all variables
print('TPTOTINC mean:' + str(df_data.TPTOTINC.mean()))

#Read in the replicate-weight data. This dataset is small enough that most machines
#	can read the whole file into memory
df_rw = pd.read_csv("rw2023.csv",\
		dtype = dict([(i,v) for i,v in zip(rw_schema['name'], rw_schema['dtype'])]),\
		sep='|',\
		header=0,\
		names=rw_schema['name'],\
		)
#preview the data
print(df_rw.head())

#check some unweighted means against the validation xls file to help ensure that the data
#	were read in correctly. Note that the validation xls files do not include all variables
print('REPWT100 mean:' + str(df_rw.REPWGT100.mean()))

#Merge data and replicate weights on SSUID, PNUM, MONTHCODE
df = df_data.merge(df_rw, left_on=['SSUID','PNUM','MONTHCODE'], right_on=['SSUID','PNUM','MONTHCODE'])

#preview the merged data
print(df.head())

#Example of using the replicate weights to estimate the standard error of a weighted mean
#Requires the NumPy package
import numpy as np
df_est = df.loc[df.TPTOTINC.isna() != True]
point_estimate = np.nansum(df_est.TPTOTINC*df_est['WPFINWGT'])/np.nansum(df_est['WPFINWGT'])
rep_means = [np.nansum(df_est.TPTOTINC*df_est['REPWGT'+str(i)])/np.nansum(df_est['REPWGT'+str(i)]) for i in range(1,241)]
rep_means = np.asarray(rep_means)
variance = (1/(240*.5**2))*sum((rep_means - point_estimate)**2)
print("Point estimate:{:.2f} , Standard error:{:.2f}".format(point_estimate,variance**.5))