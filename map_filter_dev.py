import os
import folium
import geojsonio
from pathlib import Path
import geopandas as gpd
import matplotlib
import branca
import pandas as pd
import numpy as np
from folium import plugins
this_file_path = os.path.abspath(__file__)
project_root = os.path.split(this_file_path)[0]
sys.path.append(project_root)

import etl_preprocess as etl
import map_tools as mt

dd = etl.DownloadData(project_root)
dist = dd.get_gsdata(db_name='District Coronavirus Plans Analysis public file', data_file='3.30.20')
url = 'https://opendata.arcgis.com/datasets/95738ddb2b784336a60aff23312ff480_0.geojson'

# check with updated data 
dist_update = dd.get_gsdata(db_name='District Coronavirus Plans Analysis public file', data_file='Public-3.30.20')

assert_frame_equal(dist, dist_update, check_dtype=False)
dist_update.columns
# get ID's corresponding to district focus
dist_pol = dd.get_geodata(location=url, subset_ids=dist['ID'].tolist(), refresh = False)

# from district file
rev_features = ['ID','DATE UPDATED','OVERVIEW','WIFI ACCESS PROVIDED', 'DEVICES PROVIDED','RESOURCES FOR SPECIAL POPULATIONS','LEVEL',
    'SCHOOL CLOSURE START DATE','ANTICIPATED DISTANCE-LEARNING START DATE']
dist_sub = dist[rev_features]
dist_sub = dist_sub[pd.to_numeric(dist_sub['ID'], errors='coerce').notnull()]
dist_sub.reset_index(drop=True, inplace=True)
dist_sub['ID'] = dist_sub['ID'].apply(lambda x: '{0:0>7}'.format(x))
dist_sub = dist_sub.rename(columns={"ID": "GEOID"})
dist_sub['OVERVIEW'] = dist_sub['OVERVIEW'].str.replace('\n', '<br>') # replace the \n with <br> not the best fix (hacky)

# data from other google sheet 
misc_data = dd.get_gsdata(db_name='District Coronavirus Plans Analysis public file', data_file='EISi extract match')
misc_data = misc_data.drop('DISTRICT', axis = 1)
misc_data['ID'] = misc_data['ID'].apply(lambda x: '{0:0>7}'.format(x))
misc_data = misc_data.rename(columns={"ID": "GEOID"})

# look at the ids that are missing from polygon district and google sheet data 
pol_dist = list(dist_pol['GEOID'])

dist_sub[~dist_sub.GEOID.isin(pol_dist)]
misc_data[~misc_data.GEOID.isin(pol_dist)]

## Explore .dta files (STATA...yuck)
dist_ids = etl.clean_id(dist['ID'])

vars_dems = ['leaid','year','leaname','stateabb','totalenrollment','frl','censusid','schlev','pp_totexp','pc_frlstudentsps',
'frl_high', 'nonwhite_high', 'st_num', 'pc_iepstudentsdist']

df_dems = dd.get_locdata(file_name='data06-newvars.dta', raw=False, vars_get=vars_dems,
    subset_ids=dist_ids, sub_year=2016)

# locate seda performance data 
# use mn_avgall 
vars_seda = ['leaid', 'year', 'mn_avgallela', 'z_allela', 'pct_allela', 'mn_avgallmath', 'z_allmath',
    'pct_allmath']

df_seda = dd.get_locdata(file_name='data02-seda.dta', raw=False, vars_get=vars_seda,
    subset_ids=dist_ids)

# merge with geodata
# google sheet files 
dist_pol = dist_pol.merge(dist_sub, on = 'GEOID')
dist_pol = dist_pol.merge(misc_data, on = 'GEOID')

# crpe files 
dist_pol = dist_pol.merge(df_dems, left_on='GEOID', right_on='leaid')

# seda files from crpe missing some values!
dist_pol = dist_pol.merge(df_seda, left_on='GEOID', right_on='leaid', how='outer')


# take a look at the distribution of columns of interest but on the whole population within a year
df_dems_all = dd.get_locdata(file_name='data06-newvars.dta', raw=False, vars_get=vars_dems, sub_year=2016)
df_dems_all.columns
df_dems_all['pc_frlstudentsps'].dropna().describe()
# one standard deviation above the meant is ~70% for FRL
# pp_totexp needs further insights, there are districts that soend $0 which is not correct check with CRPE analyst

dist_pol['pp_totexp'].describe()
bin_values = np.arange(start=9093, stop=32248, step=1000)
bin_values
dist_pol['pp_totexp'].hist(bins = bin_values)

# create plot columns for asthetics 
dist_pol['wht_perc_plot'] = etl.pct_str(dist_pol, 'PctNonWh')
dist_pol['frl_pct'] = etl.pct_str(dist_pol, 'pc_frlstudentsps')
dist_pol['pct_allmath_plot'] = etl.pct_str(dist_pol, 'pct_allmath') 

# initiate map 
usa_base = folium.Map(location=[38,-97], zoom_start=4,tiles="cartodbpositron")

# Create points base group 
cat_col_dict = {
    0:'#d7191c',
    1:'#fdae61',
    2:'#ffffbf',
    3:'#a6d96a',
    4:'#1a9641'
}

dist_pol['color'] = dist_pol['LEVEL'].map(cat_col_dict)

points = folium.FeatureGroup('All Districts')

cols_to_locate = ['NAME','Lat','Long','color','NAME','SCHOOL CLOSURE START DATE',
    'Schools', 'Students', 'pp_totexp', 'wht_perc_plot', 'frl_pct', 'pct_allmath_plot',
    'OVERVIEW','DEVICES PROVIDED','WIFI ACCESS PROVIDED', 'RESOURCES FOR SPECIAL POPULATIONS']

[dist_pol.columns.get_loc(c) for c in cols_to_locate if c in dist_pol]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_pol.shape[0]):
    tooltip = 'Click here for '+ dist_pol.iloc[i,6] +' COVID-19 information'
    lat = dist_pol.iloc[i,33]
    lon = dist_pol.iloc[i,34]
    color = dist_pol.iloc[i,62]
    district = dist_pol.iloc[i,6] 
    closure = dist_pol.iloc[i,28]
    schools = dist_pol.iloc[i,30]   
    students = dist_pol.iloc[i,31]
    totexp = dist_pol.iloc[i,45]
    whtperc = dist_pol.iloc[i,59]
    frl = dist_pol.iloc[i,60]
    prf = dist_pol.iloc[i,61]
    over_text = dist_pol.iloc[i,23]
    device = dist_pol.iloc[i,25]
    wifi = dist_pol.iloc[i,24]
    rsc_sp = dist_pol.iloc[i,26]
    html = f_string_convert_str(popup_html_str)
    
    iframe = branca.element.IFrame(html, width=300+180, height=400)
    popup = folium.Popup(iframe, max_width=650)

    marker = folium.CircleMarker(location = [lat,lon],
        popup=popup, tooltip=tooltip,radius=7,
            fill = True,
            fill_color=color,
            color=color,
            fill_opacity=0.7).add_to(points)

usa_base.add_child(points)

# add other filters
pop_filter = folium.FeatureGroup('District Non-White Population > 75%', show=False)
dist_pol.columns

high_wht = dist_pol['PctNonWh'] > .75 
dist_pol_sub1 = dist_pol[high_wht]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_pol_sub1.shape[0]):
    tooltip = 'Click here for '+ dist_pol_sub1.iloc[i,6] +' COVID-19 information'
    lat = dist_pol_sub1.iloc[i,33]
    lon = dist_pol_sub1.iloc[i,34]
    color = dist_pol_sub1.iloc[i,62]
    district = dist_pol_sub1.iloc[i,6] 
    closure = dist_pol_sub1.iloc[i,28]
    schools = dist_pol_sub1.iloc[i,30]   
    students = dist_pol_sub1.iloc[i,31]
    totexp = dist_pol_sub1.iloc[i,45]
    whtperc = dist_pol_sub1.iloc[i,59]
    frl = dist_pol_sub1.iloc[i,60]
    prf = dist_pol_sub1.iloc[i,61]
    over_text = dist_pol_sub1.iloc[i,23]
    device = dist_pol_sub1.iloc[i,25]
    wifi = dist_pol_sub1.iloc[i,24]
    rsc_sp = dist_pol_sub1.iloc[i,26]
    html = f_string_convert_str(popup_html_str)
    
    iframe = branca.element.IFrame(html, width=300+180, height=400)
    popup = folium.Popup(iframe, max_width=650)

    marker = folium.CircleMarker(location = [lat,lon],
        popup=popup, tooltip=tooltip,radius=7,
            fill = True,
            fill_color=color,
            color=color,
            fill_opacity=0.7).add_to(pop_filter)

usa_base.add_child(pop_filter)

# add frl filter
frl_filter = folium.FeatureGroup('District FRL Population > 75%', show=False)
dist_pol.columns

high_frl = dist_pol['pc_frlstudentsps'] > .75 
dist_pol_sub2 = dist_pol[high_frl]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_pol_sub2.shape[0]):
    tooltip = 'Click here for '+ dist_pol_sub2.iloc[i,6] +' COVID-19 information'
    lat = dist_pol_sub2.iloc[i,33]
    lon = dist_pol_sub2.iloc[i,34]
    color = dist_pol_sub2.iloc[i,62]
    district = dist_pol_sub2.iloc[i,6] 
    closure = dist_pol_sub2.iloc[i,28]
    schools = dist_pol_sub2.iloc[i,30]   
    students = dist_pol_sub2.iloc[i,31]
    totexp = dist_pol_sub2.iloc[i,45]
    whtperc = dist_pol_sub2.iloc[i,59]
    frl = dist_pol_sub2.iloc[i,60]
    prf = dist_pol_sub2.iloc[i,61]
    over_text = dist_pol_sub2.iloc[i,23]
    device = dist_pol_sub2.iloc[i,25]
    wifi = dist_pol_sub2.iloc[i,24]
    rsc_sp = dist_pol_sub2.iloc[i,26]
    html = f_string_convert_str(popup_html_str)
    
    iframe = branca.element.IFrame(html, width=300+180, height=400)
    popup = folium.Popup(iframe, max_width=650)

    marker = folium.CircleMarker(location = [lat,lon],
        popup=popup, tooltip=tooltip,radius=7,
            fill = True,
            fill_color=color,
            color=color,
            fill_opacity=0.7).add_to(frl_filter)

usa_base.add_child(frl_filter)

# add pop totexp
exp_filter = folium.FeatureGroup('District Per-pupil Expenditures > $15,500', show=False)
dist_pol.columns

avg_exp = dist_pol['pp_totexp'] > 15500 
dist_pol_sub3 = dist_pol[avg_exp]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_pol_sub3.shape[0]):
    tooltip = 'Click here for '+ dist_pol_sub3.iloc[i,6] +' COVID-19 information'
    lat = dist_pol_sub3.iloc[i,33]
    lon = dist_pol_sub3.iloc[i,34]
    color = dist_pol_sub3.iloc[i,62]
    district = dist_pol_sub3.iloc[i,6] 
    closure = dist_pol_sub3.iloc[i,28]
    schools = dist_pol_sub3.iloc[i,30]   
    students = dist_pol_sub3.iloc[i,31]
    totexp = dist_pol_sub3.iloc[i,45]
    whtperc = dist_pol_sub3.iloc[i,59]
    frl = dist_pol_sub3.iloc[i,60]
    prf = dist_pol_sub3.iloc[i,61]
    over_text = dist_pol_sub3.iloc[i,23]
    device = dist_pol_sub3.iloc[i,25]
    wifi = dist_pol_sub3.iloc[i,24]
    rsc_sp = dist_pol_sub3.iloc[i,26]
    html = f_string_convert_str(popup_html_str)
    
    iframe = branca.element.IFrame(html, width=300+180, height=400)
    popup = folium.Popup(iframe, max_width=650)

    marker = folium.CircleMarker(location = [lat,lon],
        popup=popup, tooltip=tooltip,radius=7,
            fill = True,
            fill_color=color,
            color=color,
            fill_opacity=0.7).add_to(exp_filter)

usa_base.add_child(exp_filter)

# add legend 
with open(os.path.join(project_root, 'html/legend_update.html'), 'r') as f:
    legend_html_str = f.read()

usa_base.get_root().html.add_child(folium.Element(legend_html_str))

folium.LayerControl(position='topleft').add_to(usa_base)


usa_base.save('map_filters.html')