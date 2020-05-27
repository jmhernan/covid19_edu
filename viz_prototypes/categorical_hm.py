import altair as alt
from vega_datasets import data
import os
from pathlib import Path
import matplotlib
import pandas as pd
from pandas._testing import assert_frame_equal
import numpy as np

this_file_path = os.path.abspath(__file__)
project_root = os.path.split(os.path.split(this_file_path)[0])[0]
sys.path.append(project_root)

import etl_preprocess as etl

dd = etl.DownloadData(project_root)
dist = dd.get_gsdata(db_name='District Coronavirus Plans Analysis public file', data_file='Tableau Data Viz - DO NOT EDIT')

dist.shape
len(dist['ID'].tolist())

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
df_dems_all['pc_frlstudentsps'].hist()
# one standard deviation above the meant is ~70% for FRL
# pp_totexp needs further insights, there are districts that soend $0 which is not correct check with CRPE analyst

dist_sub['pp_totexp'].describe()
dist_sub['pp_totexp'].hist()
# create binned data for viz
dist_sub['frl_bins_4'] = pd.qcut(dist_sub['pc_frlstudentsps'], q=4) 
dist_sub['frl_bins_4'].value_counts()

cut_labels = ['0 - 25', '25 - 50', '50-75', '75-100']
cut_bins = [0, .25, .50, .75, 1]
dist_sub['frl_cut_4'] = pd.cut(dist_sub['pc_frlstudentsps'], bins=cut_bins, labels=cut_labels)
# frl chart
frl = dist_sub[['LEVEL','REMOTE LEARNING DESCRIPTION','pc_frlstudentsps','frl_cut_4']]
frl = frl[(frl.LEVEL != '#N/A')&(frl.LEVEL != 0)]
frl.dropna(inplace=True)
frl.reset_index(drop=True, inplace=True)

# Configure common options
base = alt.Chart(frl).transform_aggregate(
    num_districts='count()',
    groupby=['LEVEL', 'frl_cut_4']
).encode(
    alt.X('frl_cut_4:O', scale=alt.Scale(paddingInner=0),
        axis=alt.Axis(title='Free or Reduced Lunch Proportion')),
    alt.Y('LEVEL:O', scale=alt.Scale(paddingInner=0),
        sort=alt.EncodingSortField('LEVEL', order='descending'),
        axis=alt.Axis(title='Remote Learning Description')),
)

# Configure heatmap
heatmap = base.mark_rect().encode(
    color=alt.Color('num_districts:Q',
        scale=alt.Scale(scheme='yelloworangered'),
        legend=alt.Legend(direction='horizontal', title='# of Districts')
    )
).properties(
    width=300,
    height=300
)

# Configure text
text = base.mark_text(baseline='middle').encode(
    text='num_districts:Q',
    color=alt.condition(
        alt.datum.num_cars > 100,
        alt.value('black'),
        alt.value('white')
    )
)

# Draw the chart
heatmap.save('frl_heat.html', embed_options={'renderer':'svg'})
heatmap
##############
###
dist_sub['pct_allmath'].describe()
dist_sub['pct_allmath'].hist()
dist_sub['pct_allela'].describe()
dist_sub['pct_allela'].hist()

cut_labels = ['0 - 25', '25 - 50', '50-75', '75-100']
cut_bins = [0, 25, 50, 75, 100]

dist_sub['math_cut_4'] = pd.cut(dist_sub['pct_allmath'], bins=cut_bins, labels=cut_labels)
dist_sub['ela_cut_4'] = pd.cut(dist_sub['pct_allela'], bins=cut_bins, labels=cut_labels)

# math chart
math = dist_sub[['LEVEL','REMOTE LEARNING DESCRIPTION','pct_allmath','math_cut_4']]
math = math[(math.LEVEL != '#N/A')&(math.LEVEL != 0)]
math.dropna(inplace=True)
math.reset_index(drop=True, inplace=True)

# Configure common options
base = alt.Chart(math).transform_aggregate(
    num_districts='count()',
    groupby=['LEVEL', 'math_cut_4']
).encode(
    alt.X('math_cut_4:O', scale=alt.Scale(paddingInner=0),
        axis=alt.Axis(title='Math Proficiency Proportion')),
    alt.Y('LEVEL:O', scale=alt.Scale(paddingInner=0),
        sort=alt.EncodingSortField('LEVEL', order='descending'),
        axis=alt.Axis(title='Remote Learning Description')),
)

# Configure heatmap
heatmap = base.mark_rect().encode(
    color=alt.Color('num_districts:Q',
        scale=alt.Scale(scheme='lightgreyteal'),
        legend=alt.Legend(direction='horizontal', title='# of Districts')
    )
).properties(
    width=300,
    height=300
)

# Draw the chart
heatmap
heatmap.save('math_heat.html', embed_options={'renderer':'svg'})
####

ela = dist_sub[['LEVEL','REMOTE LEARNING DESCRIPTION','pct_allela','ela_cut_4']]
ela = ela[(ela.LEVEL != '#N/A')&(ela.LEVEL != 0)]
ela.dropna(inplace=True)
ela.reset_index(drop=True, inplace=True)

# Configure common options
base = alt.Chart(ela).transform_aggregate(
    num_districts='count()',
    groupby=['LEVEL', 'ela_cut_4']
).encode(
    alt.X('ela_cut_4:O', scale=alt.Scale(paddingInner=0),
        axis=alt.Axis(title='ELA Proficiency Proportion')),
    alt.Y('LEVEL:O', scale=alt.Scale(paddingInner=0),
        sort=alt.EncodingSortField('LEVEL', order='descending'),
        axis=alt.Axis(title='Remote Learning Description')),
)

# Configure heatmap
heatmap = base.mark_rect().encode(
    color=alt.Color('num_districts:Q',
        scale=alt.Scale(scheme='lightgreyteal'),
        legend=alt.Legend(direction='horizontal', title='# of Districts')
    )
).properties(
    width=300,
    height=300
)

# Draw the chart
heatmap
heatmap.save('ela_heat.html', embed_options={'renderer':'svg'})