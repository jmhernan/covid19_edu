# Tools for ETL dev

# Initial step
# dowload google drive dataset
# function to work with the google api 
# you will need to enable your api and generate a key
# `GoogleAuth` will look for a "client_secrets.json" in the base directory
# You need to get the google drive file directory ID see analysis script for examples

# Other data needs:
# Common Core of Data
# 1. Demographics 
# 2. District IDs (LEA by state unique identifier)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import geojson
import json
import requests
from pathlib import Path
import geopandas as gpd
import re
import warnings


this_file_path = os.path.abspath(__file__)
project_root = os.path.split(this_file_path)[0]

# use creds to create a client to interact with the Google Drive 
class DownloadData:
	def __init__(self, project_root):
		self.scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
		self.creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(project_root, 'creds.json'), self.scope)
		self.client = gspread.authorize(self.creds)	
		self.data_path = os.path.join(project_root, 'data/')

	def get_gsdata(self, db_name=None, data_file=None):
		data = self.client.open(db_name)
		if data_file is None:
			print('Select the worksheet you want to download and pass as "data_file" var', data.worksheets())
		else:
			updated_data = data.worksheet(data_file)
			list_of_hashes = updated_data.get_all_records()
			headers = list_of_hashes.pop(0)
			df = pd.DataFrame(list_of_hashes, columns=headers)
		return df

	def get_geodata(self, location=None, subset_ids=None):
		if subset_ids is None:
			full_district = gpd.read_file(location)
			return full_district
		else:
			full_district = gpd.read_file(location)
			subset_ids = [x for x in subset_ids if isinstance(x, int)]
			subset_ids = ["%07d" %i for i in subset_ids] 
			sub_df = full_district[full_district['GEOID'].isin(subset_ids)] 
			return sub_df
	
	def get_locdata(self, file_name=None, raw=True, vars_get=None, subset_ids=None):
		file_type = re.search(r'(\..*$)', file_name)
		assert (file_type.group(0) == '.dta' or file_type.group(0) == '.csv'), "Only '.dta' and '.csv' files currently supported"
		
		if file_type.group(0) == '.dta':
			df = pd.read_stata(os.path.join(data_path, file_name))
		elif file_type.group(0) == '.csv':
			df = pd.read_csv(os.path.join(data_path, file_name))

		if raw == True:
			print(df.columns)
			return df	
		else:
			df_sub = df[vars_get]
			max_yr = df_sub['year'].max()
			df_sub = df_sub[df_sub.year == max_yr]
			df_sub['leaid'] = df_sub['leaid'].astype('int').astype('str')
			df_sub['leaid'] = df_sub['leaid'] = df_sub['leaid'].apply(lambda x: '{0:0>7}'.format(x))
			
			if subset_ids is not None:
				df_sub = df_sub[df_sub['leaid'].isin(subset_ids)]

		return df_sub
