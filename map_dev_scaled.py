import folium
import geojsonio
from pathlib import Path
import geopandas as gpd
import matplotlib
import branca
import pandas as pd
from folium import plugins
this_file_path = os.path.abspath(__file__)
project_root = os.path.split(this_file_path)[0]
sys.path.append(project_root)

import etl_preprocess as etl
import map_tools as mt

dd = etl.DownloadData(project_root)
dist = dd.get_gsdata(db_name='District Coronavirus Plans Analysis public file', data_file='3.30.20')
url = 'https://opendata.arcgis.com/datasets/95738ddb2b784336a60aff23312ff480_0.geojson'

# get ID's corresponding to district focus
sub_ids = dist['ID'].tolist()
dist_pol = dd.get_geodata(location=url, subset_ids=sub_ids, refresh = False)

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
dist_pol_seda = dist_pol.merge(df_seda, left_on='GEOID', right_on='leaid')

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

points = folium.FeatureGroup('District Info')

cols_to_locate = ['NAME','Lat','Long','color','NAME','SCHOOL CLOSURE START DATE',
    'OVERVIEW','DEVICES PROVIDED','WIFI ACCESS PROVIDED']

[dist_pol.columns.get_loc(c) for c in cols_to_locate if c in dist_pol]

with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_pol.shape[0]):
    tooltip = 'Click here for '+ dist_pol.iloc[i,6] +' COVID-19 information'
    lat = dist_pol.iloc[i,33]
    lon = dist_pol.iloc[i,34]
    color = dist_pol.iloc[i,51]
    district = dist_pol.iloc[i,6] 
    closure = dist_pol.iloc[i,28]  
    over_text = dist_pol.iloc[i,23]
    device = dist_pol.iloc[i,25]
    wifi = dist_pol.iloc[i,24]
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

# add legend 
with open(os.path.join(project_root, 'html/legend_update.html'), 'r') as f:
    legend_html_str = f.read()

usa_base.get_root().html.add_child(folium.Element(legend_html_str))

# Race dem poly 
race = folium.FeatureGroup('Non-White Student Population (%)', show=False)

# create str vars for plotting asthetics
dist_pol['wht_perc_plot'] = etl.pct_str(dist_pol, 'PctNonWh')

dist_pol = dist_pol.sort_values(
    by='PctNonWh',
    ascending=True
)

min, max = dist_pol['PctNonWh'].quantile([0.05,0.95]).apply(lambda x: round(x, 2))
min
max

# create color map
color_ramp_size = branca.colormap.LinearColormap(
    colors=['#feebe2','#fbb4b9','#f768a1','#c51b8a','#7a0177'],
    vmin=min,
    vmax=max
).to_step(n=5)

color_ramp_size.caption="Non-White Student Population (%)"

def style_function_poly(feature):
    return{
        'fillColor': color_ramp_size(feature['properties']['PctNonWh']),
        'color': color_ramp_size(feature['properties']['PctNonWh']),
        'fillOpacity': 0.5,
        'weight':1
    }

variable_pops = ['NAME','Schools','Students','wht_perc_plot']
variable_alias = ['District:','No. of Schools:','Enrollment:','Non-White Proportion:']

# add layer
folium.GeoJson(
    dist_pol,
    name='US States',
    style_function=style_function_poly,
    highlight_function=lambda x: {
        'fillOpacity':1
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=variable_pops,
        aliases=variable_alias,
    )
).add_to(race)

color_ramp_size.add_to(usa_base)

usa_base.add_child(race)

# create expenditure poly
exp = folium.FeatureGroup('Total Per-Pupil Expenditure', show=False)

# create color scales 
grbblue = ['#d0d1e6','#a6bddb','#67a9cf','#1c9099','#016c59']

variable = 'pp_totexp'

# take care of missing values
dist_pol_exp = dist_pol.dropna(how='all', subset=[variable])
dist_pol_exp.reset_index(drop=True, inplace=True)

dist_pol_exp=dist_pol_exp.sort_values(by=variable, ascending=True)

dist_pol_exp[variable].quantile([0.05,0.95]).apply(lambda x: round(x, 2))

color_ramp_rev = branca.colormap.LinearColormap(
    colors=grbblue,
    vmin=1027,
    vmax=25994
).to_step(n=5)

color_ramp_rev
color_ramp_rev.caption="Total Per-Pupil Expenditures ($)"


def style_function_rev(feature):
    return{
        'fillColor': color_ramp_rev(feature['properties']['pp_totexp']),
        'color': color_ramp_rev(feature['properties']['pp_totexp']),
        'fillOpacity': 0.5,
        'weight':1
    } 

#create pp_totexp astethic varibale 
variable_pops_ex=['NAME','Schools','Students', 'pp_totexp']
variable_alias_ex=['District:','No. of Schools:','Enrollment:','Per-Pupil Expenditures:']

folium.GeoJson(
    dist_pol_exp,
    name='US States',
    style_function=style_function_rev,
    highlight_function=lambda x: {
        'fillOpacity':1
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=variable_pops_ex,
        aliases=variable_alias_ex)).add_to(exp)

color_ramp_rev.add_to(usa_base)

usa_base.add_child(exp)

# add performance
ach = folium.FeatureGroup('Student Achievement', show=False)

# create color scales 
pur_blue = ['#762a83','#af8dc3','#e7d4e8','#f7f7f7','#d1e5f0','#67a9cf','#2166ac']

variable = 'mn_avgallmath'

dist_pol_ach = dist_pol_seda.dropna(how='all', subset=[variable])
dist_pol_ach.reset_index(drop=True, inplace=True)

dist_pol_ach=dist_pol_ach.sort_values(by=variable, ascending=True)

dist_pol_ach[variable].quantile([0.05,.25,.50,.75,0.95]).apply(lambda x: round(x, 2))

min = dist_pol_ach[variable].min()
max = dist_pol_ach[variable].max()

color_ramp_perf = branca.colormap.LinearColormap(
    colors=pur_blue,
    index=[210,220,230,242,250,260,270],
    vmin=min,
    vmax=max
)

color_ramp_perf
color_ramp_perf.caption="Math Performance (Scaled-Score)"


def style_function_perf(feature):
    return{
        'fillColor': color_ramp_perf(feature['properties']['mn_avgallmath']),
        'color': color_ramp_perf(feature['properties']['mn_avgallmath']),
        'fillOpacity': 0.5,
        'weight':1
    } 

variable_pops_perf=['NAME','Schools','Students','mn_avgallmath']
variable_alias_perf=['District:','No. of Schools:','Enrollment:','Math Proficiency:']

folium.GeoJson(
    dist_pol_ach,
    name='US States',
    style_function=style_function_perf,
    highlight_function=lambda x: {
        'fillOpacity':1
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=variable_pops_perf,
        aliases=variable_alias_perf)).add_to(ach)


color_ramp_perf.add_to(usa_base)

usa_base.add_child(ach)

# add frl poly 
frl = folium.FeatureGroup('FRL Levels', show=False)

# create color scales 
map_blue = ['#ffffcc','#a1dab4','#41b6c4','#2c7fb8','#253494']

variable = 'pc_frlstudentsps'

# clean up missing 
dist_pol_frl = dist_pol.dropna(how='all', subset=[variable])
dist_pol_frl.reset_index(drop=True, inplace=True)

# create asthetic
dist_pol_frl['frl_pct'] = etl.pct_str(dist_pol_frl, variable)

dist_pol_frl=dist_pol_frl.sort_values(by=variable, ascending=True)

dist_pol_frl[variable].quantile([0.05,.25,.50,.75,0.95]).apply(lambda x: round(x, 2))

min = dist_pol_frl[variable].min()
max = dist_pol_frl[variable].max()

color_ramp_frl = branca.colormap.LinearColormap(
    colors=map_blue,
    index=dist_pol_frl[variable].quantile([0.05,.25,.50,.75,0.95]),
    vmin=min,
    vmax=max
)

color_ramp_frl
color_ramp_frl.caption="Free or Reduced Priced Lunch (%)"


def style_function_frl(feature):
    return{
        'fillColor': color_ramp_frl(feature['properties']['pc_frlstudentsps']),
        'color': color_ramp_frl(feature['properties']['pc_frlstudentsps']),
        'fillOpacity': 0.5,
        'weight':1
    } 

variable_pops_frl=['NAME','Schools','Students','frl_pct']
variable_alias_frl=['District:','No. of Schools:','Enrollment:','FRL Percent:']

folium.GeoJson(
    dist_pol_frl,
    name='US States',
    style_function=style_function_frl,
    highlight_function=lambda x: {
        'fillOpacity':1
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=variable_pops_frl,
        aliases=variable_alias_frl)).add_to(frl)

color_ramp_frl.add_to(usa_base)
usa_base.add_child(frl)

# add layers to base map
usa_base.add_child(race)
usa_base.add_child(exp)
usa_base.add_child(ach)
usa_base.add_child(frl)

folium.LayerControl(position='topleft').add_to(usa_base)
usa_base.keep_in_front(points)
usa_base.add_child(mt.BindColormap(race, color_ramp_size)).add_child(mt.BindColormap(exp, color_ramp_rev)).add_child(mt.BindColormap(ach,color_ramp_perf)).add_child(mt.BindColormap(frl, color_ramp_frl))

usa_base.save('map.html')
