import folium
import geojsonio
from pathlib import Path
import geopandas as gpd
import matplotlib
import branca
import pandas as pd

this_file_path = os.path.abspath(__file__)
project_root = os.path.split(this_file_path)[0]
sys.path.append(project_root)

import etl_preprocess as etl


dd = etl.download_data(project_root)
dist = dd.get_gdata(db_name='District Coronavirus Plans Analysis public file', data_file='3.30.20')
url = 'https://opendata.arcgis.com/datasets/95738ddb2b784336a60aff23312ff480_0.geojson'
sub_ids = dist['ID'].to_list()

dist_pol = dd.get_geo_data(location=url, subset_ids=sub_ids)
# add save functinality to function save = True parmeter and load from local or API
#dist_pol.to_file(os.path.join(project_root,"data/district_subset.geojson"), driver='GeoJSON')
dist_pol = gpd.read_file(os.path.join(project_root,"data/district_subset.geojson"))

dist_pol.plot()
# save files locally not tracked as to not ping the api every time
# Need to clean up headers 
# Add colors to the districts and attach to the polygon data frame
dist.columns
dist.head

dist_pol.head
# join relevant features to geopd 
# from district file
rev_features = ['ID','DATE UPDATED','OVERVIEW','WIFI ACCESS PROVIDED', 'DEVICES PROVIDED','RESOURCES FOR SPECIAL POPULATIONS','LEVEL',
    'SCHOOL CLOSURE START DATE','ANTICIPATED DISTANCE-LEARNING START DATE']
district_sub = dist[rev_features]
district_sub = district_sub[pd.to_numeric(district_sub['ID'], errors='coerce').notnull()]
district_sub.reset_index(drop=True, inplace=True)
district_sub['ID'] = district_sub['ID'].apply(lambda x: '{0:0>7}'.format(x))
district_sub = district_sub.rename(columns={"ID": "GEOID"})
# merge with geodata
dist_pol = dist_pol.merge(district_sub, on = 'GEOID')

# data from other sources
misc_data = dd.get_gdata(db_name='District Coronavirus Plans Analysis public file', data_file='EISi extract match')
misc_data = misc_data.drop('DISTRICT', axis = 1)
misc_data['ID'] = misc_data['ID'].apply(lambda x: '{0:0>7}'.format(x))
misc_data = misc_data.rename(columns={"ID": "GEOID"})
# merge with geodata
dist_pol = dist_pol.merge(misc_data, on = 'GEOID')

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
    index = dist_pol['PctNonWh'].quantile([0.2,0.4,0.6,0.8]),
    vmin=min,
    vmax=max
)
color_ramp_size
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
dist_pol.columns

variable_pops = ['NAME','Schools','Students','PctNonWh']
variable_alias = ['District:','No. of Schools:','Enrollment:','Non-White Proportion:']

m = folium.Map(location=[38,-97], zoom_start=4,tiles="cartodbpositron")

stategeo = folium.GeoJson(
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
).add_to(m)
color_ramp_size.add_to(m)
m
dist_pol.columns
# add markers with color codes
#for lat, lon, pop_text, color in zip(dist_pol['Lat'],dist_pol['Long'],dist_pol['OVERVIEW'],dist_pol['color']):
#    folium.Marker(location=[lat,lon], popup=pop_text, icon=folium.Icon(color=color)).add_to(m)
#m
cols = ['SCHOOL CLOSURE START DATE','OVERVIEW','WIFI ACCESS PROVIDED','DEVICES PROVIDED','NAME']
cols = ['color','Lat','Long']
[dist_pol.columns.get_loc(c) for c in cols if c in dist_pol]

for i in range(dist_pol.shape[0]):
    tooltip = 'Click here for '+ dist_pol.iloc[i,6] +' COVID-19 information'
    lat = dist_pol.iloc[i,33]
    lon = dist_pol.iloc[i,34]
    color = dist_pol.iloc[i,37]
    district = dist_pol.iloc[i,6] 
    closure = dist_pol.iloc[i,28]  
    over_text = dist_pol.iloc[i,23]
    device = dist_pol.iloc[i,25]
    wifi = dist_pol.iloc[i,24]
    html = f'''
<h2>{district}</h2>

<strong>Closure Start Date:</strong> {closure}<br>
<br>
<p>
<strong>Overview:</strong><br>
{over_text}
</p>
<strong>Devices Provided:</strong> {device}<br>
<strong>WiFi Provided:</strong> {wifi}<br>
    '''
    iframe = branca.element.IFrame(html, width=300+180, height=400)
    popup = folium.Popup(iframe, max_width=650)

    marker = folium.CircleMarker(location = [lat,lon],
        popup=popup, tooltip=tooltip,radius=7,
            fill = True,
            fill_color=color,
            color=color,
            fill_opacity=0.7).add_to(m)
# add legend 
legend_html = '''
<div style="position: fixed; 
    bottom: 100px; right: 100px; width: 190px; height: 190px; 
    border:1px solid grey; 
    z-index:9999; 
    font-size:12px;
">&nbsp; <b><font color=#090909>Distance Learning</font></b> &nbsp;<br>
<br>
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #1a9641; 
background: #1a9641; height:15px; width:15px; display:inline-block"></i>&nbsp;<font color=#090909>Curriculum, instruction, and progress monitoring</font>&nbsp;<br> 
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #a6d96a; 
background: #a6d96a; height:15px; width:15px; display:inline-block"></i>&nbsp;<font color=#090909>Curriculum and instruction</font>&nbsp;<br></i>
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #ffffbf; 
background: #ffffbf; height:15px; width:15px; display:inline-block"></i>&nbsp;<font color=#090909>Formal curriculum but no instruction</font>&nbsp;<br> 
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #fdae61; 
background: #fdae61; height:15px; width:15px; display:inline-block"></i>&nbsp;<font color=#090909>Access to general resources only</font>&nbsp;<br></i>
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #d7191c; 
background: #d7191c; height:15px; width:15px; display:inline-block"></i>&nbsp;<font color=#090909>No educational resources</font>&nbsp;<br></i>

</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))
m
m.save('map.html')
# map
map_layer_control = folium.Map(location=[38, -98], zoom_start=4)

# add tiles to map
folium.raster_layers.TileLayer('Open Street Map').add_to(map_layer_control)
folium.raster_layers.TileLayer('Stamen Terrain').add_to(map_layer_control)
folium.raster_layers.TileLayer('Stamen Toner').add_to(map_layer_control)
folium.raster_layers.TileLayer('Stamen Watercolor').add_to(map_layer_control)
folium.raster_layers.TileLayer('CartoDB Positron').add_to(map_layer_control)
folium.raster_layers.TileLayer('CartoDB Dark_Matter').add_to(map_layer_control)

# add layer control to show different maps
folium.LayerControl().add_to(map_layer_control)

# display map
map_layer_control

map_test = folium.Map()

folium.GeoJson(test, name = 'geo_districts').add_to(map_test)
folium.raster_layers.TileLayer('CartoDB Dark_Matter').add_to(map_test)
folium.raster_layers.TileLayer('CartoDB Positron').add_to(map_test)
# folium.LayerControl().add_to(map_test)

map_test
