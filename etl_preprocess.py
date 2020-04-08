# Tools for ETL dev

# Initial step
# dowload google drive dataset
# function to work with the google api 
# you will need to enable your api and generate a key
# `GoogleAuth` will look for a "client_secrets.json" in the base directory
# You need to get the google drive file directory ID see analysis script for examples

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from pathlib import Path

this_file_path = os.path.abspath(__file__)
project_root = os.path.split(this_file_path)[0]

import datetime

def _getToday():
	return datetime.date.today().strftime("%Y%m%d")

# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(project_root, 'creds.json'), scope)
client = gspread.authorize(creds)

gdata = client.open("District Coronavirus Plans Analysis public file")

gdata.worksheets()
updated_data = gdata.worksheet('3.30.20')

# Extract and print all of the values
list_of_hashes = updated_data.get_all_records()

headers = list_of_hashes.pop(0)

df = pd.DataFrame(list_of_hashes, columns=headers)
print(df.head())

# Need to clean up headers 


