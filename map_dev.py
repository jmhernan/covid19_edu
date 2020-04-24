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
dist = dist[pd.to_numeric(dist['ID'], errors='coerce').notnull()]
dist.reset_index(drop=True, inplace=True)
dist['ID'] = dist['ID'].apply(lambda x: '{0:0>7}'.format(x))
sub_ids = dist['ID'].tolist()

#dist_pol = dd.get_geodata(location=url, subset_ids=sub_ids)
# add save functinality to function save = True parmeter and load from local or API
#dist_pol.to_file(os.path.join(project_root,"data/district_subset.geojson"), driver='GeoJSON')
dist_pol = gpd.read_file(os.path.join(project_root,"data/district_subset.geojson"))

dist_pol.plot()
# save files locally not tracked as to not ping the api every time
# Need to clean up headers 
# Add colors to the districts and attach to the polygon data frame

# join relevant features to geopd 
# from district file
rev_features = ['ID','DATE UPDATED','OVERVIEW','WIFI ACCESS PROVIDED', 'DEVICES PROVIDED','RESOURCES FOR SPECIAL POPULATIONS','LEVEL',
    'SCHOOL CLOSURE START DATE','ANTICIPATED DISTANCE-LEARNING START DATE']
district_sub = dist[rev_features]
district_sub = district_sub[pd.to_numeric(district_sub['ID'], errors='coerce').notnull()]
district_sub.reset_index(drop=True, inplace=True)
district_sub['ID'] = district_sub['ID'].apply(lambda x: '{0:0>7}'.format(x))
district_sub = district_sub.rename(columns={"ID": "GEOID"})
district_sub['OVERVIEW'] = district_sub['OVERVIEW'].str.replace('\n', '<br>') # replace the \n with <br> not the best fix (hacky)

# data from other google sheet 
misc_data = dd.get_gsdata(db_name='District Coronavirus Plans Analysis public file', data_file='EISi extract match')
misc_data = misc_data.drop('DISTRICT', axis = 1)
misc_data['ID'] = misc_data['ID'].apply(lambda x: '{0:0>7}'.format(x))
misc_data = misc_data.rename(columns={"ID": "GEOID"})
##########
## Explore .dta files (STATA...yuck)
df_dems = dd.get_locdata(file_name='data06-newvars.dta')
# 2017 most recent pass list of variables that we will use for map +
# pass list of districts we want to focus on

vars_dems = ['leaid','year','leaname','stateabb','totalenrollment','frl','censusid','schlev','pp_totexp','pc_frlstudentsps',
'frl_high', 'nonwhite_high', 'st_num', 'pc_iepstudentsdist']

df_dems = dd.get_locdata(file_name='data06-newvars.dta', raw=False, vars_get=vars_dems,
    subset_ids=sub_ids, sub_year=2016)

# locate seda performance data 
df_seda = dd.get_locdata(file_name='data02-seda.dta')

max(df_seda['year'])
# use mn_avgall 
vars_seda = ['leaid', 'year', 'mn_avgallela', 'z_allela', 'pct_allela', 'mn_avgallmath', 'z_allmath',
    'pct_allmath']

df_seda = dd.get_locdata(file_name='data02-seda.dta', raw=False, vars_get=vars_seda,
    subset_ids=sub_ids)

# merge with geodata

dist_pol = dist_pol.merge(district_sub, on = 'GEOID')
dist_pol = dist_pol.merge(misc_data, on = 'GEOID')
dist_pol = dist_pol.merge(df_dems, left_on='GEOID', right_on='leaid')
dist_pol = dist_pol.merge(df_seda, left_on='GEOID', right_on='leaid')
###
dist_pol = dist_pol.sort_values(
    by='PctNonWh',
    ascending=True
)

dist_pol['LEVEL'].value_counts()

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

cat_col_dict = {
    0:'#d7191c',
    1:'#fdae61',
    2:'#ffffbf',
    3:'#a6d96a',
    4:'#1a9641'
}

dist_pol['color'] = dist_pol['LEVEL'].map(cat_col_dict)


def style_function_base(feature):
    return {
        'fillColor': feature['properties']['color'],
        'color': feature['properties']['color'],
        'fillOpacity': 0.4,
        'weight':1,
    }

def style_function_poly(feature):
    return{
        'fillColor': color_ramp_size(feature['properties']['PctNonWh']),
        'color': color_ramp_size(feature['properties']['PctNonWh']),
        'fillOpacity': 0.5,
        'weight':1
    }

variable_pops = ['NAME','Schools','Students','PctNonWh']
variable_alias = ['District:','No. of Schools:','Enrollment:','Non-White Proportion:']

usa_base = folium.Map(location=[38,-97], zoom_start=4,tiles="cartodbpositron")

points = folium.FeatureGroup('District Info')
# add markers with color codes
#for lat, lon, pop_text, color in zip(dist_pol['Lat'],dist_pol['Long'],dist_pol['OVERVIEW'],dist_pol['color']):
#    folium.Marker(location=[lat,lon], popup=pop_text, icon=folium.Icon(color=color)).add_to(m)
#m
cols = ['SCHOOL CLOSURE START DATE','OVERVIEW','WIFI ACCESS PROVIDED','DEVICES PROVIDED','NAME']
cols = ['color','Lat','Long']
[dist_pol.columns.get_loc(c) for c in cols if c in dist_pol]
dist_pol.columns[23] # find column name by index
with open(os.path.join(project_root, 'html/custom_popup.html'), 'r') as f:
    popup_html_str = f.read()

def f_string_convert_str(non_f_str: str):
    return eval(f'f"""{non_f_str}"""')

for i in range(dist_pol.shape[0]):
    tooltip = 'Click here for '+ dist_pol.iloc[i,6] +' COVID-19 information'
    lat = dist_pol.iloc[i,33]
    lon = dist_pol.iloc[i,34]
    color = dist_pol.iloc[i,59]
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

race = folium.FeatureGroup('Non-White Student Population (%)', show=False)

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

exp = folium.FeatureGroup('Total Per-Pupil Expenditure', show=False)

# create color scales 
grbblue = ['#d0d1e6','#a6bddb','#67a9cf','#1c9099','#016c59']

variable = 'pp_totexp'
dist_pol_income=dist_pol_income.sort_values(by=variable, ascending=True)

dist_pol_income[variable].quantile([0.05,0.95]).apply(lambda x: round(x, 2))

color_ramp_rev = branca.colormap.LinearColormap(
    colors=grbblue,
    vmin=9445,
    vmax=26815
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

variable_pops_ex=['NAME','Schools','Students', 'pp_totexp']
variable_alias_ex=['District:','No. of Schools:','Enrollment:','Per-Pupil Expenditures:']

folium.GeoJson(
    dist_pol_income,
    name='US States',
    style_function=style_function_rev,
    highlight_function=lambda x: {
        'fillOpacity':1
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=variable_pops_ex,
        aliases=variable_alias_ex)).add_to(exp)


color_ramp_rev.add_to(usa_base)

# add performance
ach = folium.FeatureGroup('Student Achievement', show=False)

# create color scales 
red_blue = ['#ca0020','#f4a582','#f7f7f7','#92c5de','#0571b0']

variable = 'z_allmath'
dist_pol_perf=dist_pol_perf.sort_values(by=variable, ascending=True)

dist_pol_perf[variable].quantile([0.05,0.95]).apply(lambda x: round(x, 2))

min = dist_pol_perf[variable].min()
max = dist_pol_perf[variable].max()

color_ramp_perf = branca.colormap.LinearColormap(
    colors=red_blue,
    index=dist_pol_perf[variable].quantile([0.0,0.05,0.8,0.95]),
    vmin=min,
    vmax=max
).to_step(n=5)

color_ramp_perf
color_ramp_perf.caption="Math Performance (Z-Score)"


def style_function_perf(feature):
    return{
        'fillColor': color_ramp_perf(feature['properties']['z_allmath']),
        'color': color_ramp_perf(feature['properties']['z_allmath']),
        'fillOpacity': 0.5,
        'weight':1
    } 

variable_pops_perf=['NAME','Schools','Students','z_allmath']
variable_alias_perf=['District:','No. of Schools:','Enrollment:','Math Proficiency:']

folium.GeoJson(
    dist_pol_perf,
    name='US States',
    style_function=style_function_perf,
    highlight_function=lambda x: {
        'fillOpacity':1
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=variable_pops_perf,
        aliases=variable_alias_perf)).add_to(ach)


color_ramp_perf.add_to(usa_base)
#############

usa_base.add_child(race)
usa_base.add_child(exp)
usa_base.add_child(ach)

folium.LayerControl(position='topleft').add_to(usa_base)
usa_base.keep_in_front(points)
usa_base.add_child(mt.BindColormap(race, color_ramp_size)).add_child(mt.BindColormap(exp, color_ramp_rev)).add_child(mt.BindColormap(ach,color_ramp_perf))

usa_base.save('map.html')
