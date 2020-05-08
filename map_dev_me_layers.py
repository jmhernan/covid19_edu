import os
import folium
import geojsonio
from pathlib import Path
import geopandas as gpd
import matplotlib
import branca
import pandas as pd
from pandas._testing import assert_frame_equal
import numpy as np
from folium import plugins
this_file_path = os.path.abspath(__file__)
project_root = os.path.split(this_file_path)[0]
sys.path.append(project_root)

import etl_preprocess as etl
import map_tools as mt

dd = etl.DownloadData(project_root)
dist = dd.get_gsdata(db_name='District Coronavirus Plans Analysis public file', data_file='Tableau Data Viz - DO NOT EDIT')
url = 'https://opendata.arcgis.com/datasets/95738ddb2b784336a60aff23312ff480_0.geojson'
dist.shape
len(dist['ID'].tolist())
# geo data for diustrict no longer required
# dist_pol = dd.get_geodata(location=url, subset_ids=dist['ID'].tolist(), refresh = False)

# from district file
rev_features = ['DISTRICT','ID','DATE UPDATED','OVERVIEW','ENROLLMENT','LEVEL','REMOTE LEARNING DESCRIPTION',
    'latitude','longitude']
dist_sub = dist[rev_features]
dist_sub['ID'] = dist_sub['ID'].replace(r'#N/A', 9999999, regex=True)
dist_sub['ID'] = dist_sub['ID'].apply(lambda x: '{0:0>7}'.format(x))
dist_sub['OVERVIEW'] = dist_sub['OVERVIEW'].str.replace('\n', '<br>') # replace the \n with <br> not the best fix (hacky)
dist_sub['ID']

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
# crpe files 
dist_sub = dist_sub.merge(df_dems, left_on='ID', right_on='leaid', how='outer')
dist_sub.columns
len(dist_sub)
# seda files from crpe missing some values!
dist_sub = dist_sub.merge(df_seda, left_on='ID', right_on='leaid', how='outer')

# take a look at the distribution of columns of interest but on the whole population within a year
df_dems_all = dd.get_locdata(file_name='data06-newvars.dta', raw=False, vars_get=vars_dems, sub_year=2016)
df_dems_all['pc_frlstudentsps'].dropna().describe()
# one standard deviation above the meant is ~70% for FRL
# pp_totexp needs further insights, there are districts that soend $0 which is not correct check with CRPE analyst

dist_sub['pp_totexp'].describe()
bin_values = np.arange(start=9093, stop=32248, step=1000)
bin_values
dist_sub['pp_totexp'].hist(bins = bin_values)

# create plot columns for asthetics 
dist_sub['frl_pct'] = etl.pct_str(dist_sub, 'pc_frlstudentsps')
dist_sub['pct_allmath_plot'] = etl.pct_str(dist_sub, 'pct_allmath') 
dist_sub['pp_totexp'] = dist_sub.pp_totexp.round()
dist_sub['pp_tot_plot'] = '$' + dist_sub.apply(lambda x: '{:,}'.format(x['pp_totexp']), axis = 1)
# initiate map 
usa_base = folium.Map(location=[38,-97], zoom_start=4,tiles=None)
folium.TileLayer('cartodbpositron', show=False, control=False).add_to(usa_base)

# Create points base group 
dist_sub['LEVEL'].value_counts()
cat_col_dict = {
    1:'#d7191c',
    2:'#fdae61',
    2.5:'#ffffbf',
    3:'#a6d96a',
    4:'#1a9641'
}

dist_sub['color'] = dist_sub['LEVEL'].map(cat_col_dict)

points = folium.FeatureGroup('All Districts', show=False, overlay=False)

folium.TileLayer('cartodbpositron',show=True).add_to(points)


cols_to_locate = ['DISTRICT','latitude','longitude','color', 'ENROLLMENT', 'pp_totexp', 'frl_pct', 'pct_allmath_plot',
    'OVERVIEW', 'REMOTE LEARNING DESCRIPTION', 'pp_tot_plot']

[dist_sub.columns.get_loc(c) for c in cols_to_locate if c in dist_sub]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_sub.shape[0]):
    tooltip = 'Click here for '+ dist_sub.iloc[i,0] +' COVID-19 information'
    lat = dist_sub.iloc[i,7]
    lon = dist_sub.iloc[i,8]
    color = dist_sub.iloc[i,34]
    district = dist_sub.iloc[i,0]   
    students = dist_sub.iloc[i,4]
    totexp = dist_sub.iloc[i,33]
    frl = dist_sub.iloc[i,31]
    prf = dist_sub.iloc[i,32]
    over_text = dist_sub.iloc[i,3]
    update = dist_sub.iloc[i,2]
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
# pop_filter = folium.FeatureGroup('District Non-White Population > 75%', show=False, overlay=False)
# dist_sub.columns

# high_wht = dist_sub['PctNonWh'] > .75 
# dist_sub_sub1 = dist_sub[high_wht]

# with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
#     popup_html_str = f.read()

# def f_string_convert_str(non_f_str: str):
#     return eval(f'f"""{non_f_str}"""')

# for i in range(dist_sub_sub1.shape[0]):
#     tooltip = 'Click here for '+ dist_sub_sub1.iloc[i,6] +' COVID-19 information'
#     lat = dist_sub_sub1.iloc[i,33]
#     lon = dist_sub_sub1.iloc[i,34]
#     color = dist_sub_sub1.iloc[i,62]
#     district = dist_sub_sub1.iloc[i,6] 
#     closure = dist_sub_sub1.iloc[i,28]
#     schools = dist_sub_sub1.iloc[i,30]   
#     students = dist_sub_sub1.iloc[i,31]
#     totexp = dist_sub_sub1.iloc[i,45]
#     whtperc = dist_sub_sub1.iloc[i,59]
#     frl = dist_sub_sub1.iloc[i,60]
#     prf = dist_sub_sub1.iloc[i,61]
#     over_text = dist_sub_sub1.iloc[i,23]
#     device = dist_sub_sub1.iloc[i,25]
#     wifi = dist_sub_sub1.iloc[i,24]
#     rsc_sp = dist_sub_sub1.iloc[i,26]
#     html = f_string_convert_str(popup_html_str)
    
#     iframe = branca.element.IFrame(html, width=300+180, height=400)
#     popup = folium.Popup(iframe, max_width=650)

#     marker = folium.CircleMarker(location = [lat,lon],
#         popup=popup, tooltip=tooltip,radius=7,
#             fill = True,
#             fill_color=color,
#             color=color,
#             fill_opacity=0.7).add_to(pop_filter)

# usa_base.add_child(pop_filter)

# add frl filter
frl_filter = folium.FeatureGroup('District FRL Population > 75%', show=False, overlay=False)

folium.TileLayer('cartodbpositron').add_to(frl_filter)

high_frl = dist_sub['pc_frlstudentsps'] > .75 
dist_sub2 = dist_sub[high_frl]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_sub2.shape[0]):
    tooltip = 'Click here for '+ dist_sub2.iloc[i,0] +' COVID-19 information'
    lat = dist_sub2.iloc[i,7]
    lon = dist_sub2.iloc[i,8]
    color = dist_sub2.iloc[i,34]
    district = dist_sub2.iloc[i,0]   
    students = dist_sub2.iloc[i,4]
    totexp = dist_sub2.iloc[i,33]
    frl = dist_sub2.iloc[i,31]
    prf = dist_sub2.iloc[i,32]
    over_text = dist_sub2.iloc[i,3]
    update = dist_sub2.iloc[i,2]
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
exp_filter = folium.FeatureGroup('District Per-pupil Expenditures > $15,500', show=False, overlay=False)

folium.TileLayer('cartodbpositron').add_to(exp_filter)

avg_exp = dist_sub['pp_totexp'] > 15500 
dist_sub3 = dist_sub[avg_exp]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_sub3.shape[0]):
    tooltip = 'Click here for '+ dist_sub3.iloc[i,0] +' COVID-19 information'
    lat = dist_sub3.iloc[i,7]
    lon = dist_sub3.iloc[i,8]
    color = dist_sub3.iloc[i,34]
    district = dist_sub3.iloc[i,0]   
    students = dist_sub3.iloc[i,4]
    totexp = dist_sub3.iloc[i,33]
    frl = dist_sub3.iloc[i,31]
    prf = dist_sub3.iloc[i,32]
    over_text = dist_sub3.iloc[i,3]
    update = dist_sub3.iloc[i,2]
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
usa_base

usa_base.save('map_filters.html')