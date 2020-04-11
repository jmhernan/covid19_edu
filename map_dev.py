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

dist_pol.plot()
# save files locally not tracked as to not ping the api every time
# Need to clean up headers 
# Add colors to the districts and attach to the polygon data frame
dist.columns
dist.head

dist_pol.head
# join relevant features to geopd 
district_sub = dist[['ID','LEVEL']]
district_sub[district_sub.ID.apply(lambda x: x.isnumeric())]
district_sub = district_sub[pd.to_numeric(district_sub['ID'], errors='coerce').notnull()]
district_sub['ID'] = district_sub['ID'].apply(lambda x: '{0:0>7}'.format(x))
district_sub = district_sub.rename(columns={"ID": "GEOID", "LEVEL": "LEVEL"})

dist_pol = dist_pol.merge(district_sub, on = 'GEOID')

# create color map

# ['#d7191c','#fdae61','#ffffbf','#a6d96a','#1a9641']

colormap = branca.colormap.StepColormap(
    colors=['#d7191c','#fdae61','#ffffbf','#a6d96a','#1a9641'],
    index=[0,1,2,3,4,5],
    vmin=0,
    vmax=5
)

colormap.caption="Distance Learning - District Provides:"
colormap

m = folium.Map(location=[38,-97], zoom_start=4,tiles="CartoDB Dark_Matter")



style_function = lambda x: {
    'fillColor': colormap(x['properties']['LEVEL']),
    'color': colormap(x['properties']['LEVEL']),
    'weight':1,
    'fillOpacity':0.4
}

stategeo = folium.GeoJson(
    dist_pol,
    name='US States',
    style_function=style_function
).add_to(m)

# add legend 
legend_html = '''
<div style="position: fixed; 
    bottom: 20px; left: 20px; width: 190px; height: 145px; 
    border:1px solid white; 
    z-index:9999; 
    font-size:10px;
">&nbsp; <b><font color=#ffffff>District Learning</font></b> &nbsp;<br>
<br>
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #1a9641; 
background: #1a9641; height:10px; width:10px; display:inline-block"></i>&nbsp;<font color=#ffffff>Curriculum, instruction, and progress monitoring</font>&nbsp;<br> 
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #a6d96a; 
background: #a6d96a; height:10px; width:10px; display:inline-block"></i>&nbsp;<font color=#ffffff>Curriculum and instruction</font>&nbsp;<br></i>
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #ffffbf; 
background: #ffffbf; height:10px; width:10px; display:inline-block"></i>&nbsp;<font color=#ffffff>Formal curriculum but no instruction</font>&nbsp;<br> 
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #fdae61; 
background: #fdae61; height:10px; width:10px; display:inline-block"></i>&nbsp;<font color=#ffffff>Access to general resources only</font>&nbsp;<br></i>
<i class="Legend-categoryCircle"
style="opacity:1; border:1px solid #d7191c; 
background: #d7191c; height:10px; width:10px; display:inline-block"></i>&nbsp;<font color=#ffffff>No educational resources</font>&nbsp;<br></i>

</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))
m
# map
map_layer_control = folium.Map(location=[38, -98], zoom_start=2)

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
