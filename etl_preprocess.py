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

this_file_path = os.path.abspath(__file__)
project_root = os.path.split(this_file_path)[0]

# use creds to create a client to interact with the Google Drive 
class download_data:
	def __init__(self, project_root):
		self.scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
		self.creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(project_root, 'creds.json'), self.scope)
		self.client = gspread.authorize(self.creds)	

	def get_gdata(self, db_name=None, data_file=None):
		data = self.client.open(db_name)
		if data_file is None:
			print('Select the worksheet you want to download and pass as "data_file" var', data.worksheets())
		else:
			updated_data = data.worksheet(data_file)
			list_of_hashes = updated_data.get_all_records()
			headers = list_of_hashes.pop(0)
			df = pd.DataFrame(list_of_hashes, columns=headers)
		return df

	def get_geo_data(self, location=None, subset_ids=None):
		if subset_ids is None:
			full_district = gpd.read_file(location)
			return full_district
		else:
			full_district = gpd.read_file(location)
			subset_ids = [x for x in subset_ids if isinstance(x, int)]
			subset_ids = ["%07d" %i for i in subset_ids] 
			sub_df = full_district[full_district['GEOID'].isin(subset_ids)] 
			return sub_df