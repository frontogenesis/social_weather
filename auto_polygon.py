import itertools

from matplotlib.figure import Figure
from metpy.plots import USCOUNTIES
import geopandas
from cartopy import crs as ccrs
from cartopy.io.img_tiles import GoogleTiles
import cartopy.feature as cfeature
from shapely.geometry import shape
import requests

cat_gdf = geopandas.read_file('z_30mr21/z_30mr21.shp')
ugc_county = geopandas.read_file('c_10nv20/c_10nv20.shp')

def is_ugc_county(ugcs):
    '''Determines whether alert type is UGC county or UGC zone'''
    return True if ugcs[0][2] == 'C' else False

def ugc_zone_geography(ugcs):
    '''Returns latitudes and longitudes from UGC zone-based alerts'''
    counties = [ugc.replace('Z', '') for ugc in ugcs]

    latitudes = []
    longitudes = []
    geometries = []
    
    for ugc in counties:
        latitude = (cat_gdf[cat_gdf['STATE_ZONE'] == ugc]['LAT']).tolist()
        longitude = (cat_gdf[cat_gdf['STATE_ZONE'] == ugc]['LON']).tolist()
        geometry = (cat_gdf[cat_gdf['STATE_ZONE'] == ugc]['geometry']).tolist()
        latitudes.append(latitude)
        longitudes.append(longitude)
        geometries.append(geometry)
        
    flatten = itertools.chain.from_iterable
    latitudes = list(flatten(latitudes))
    longitudes = list(flatten(longitudes))

    return latitudes, longitudes, geometries

def ugc_county_geography(ugcs):
    '''Returns latitudes and longitudes from UGC county-based alerts'''
    counties = [int(ugc[-3:]) for ugc in ugcs]
    state = ugcs[0][0:2]

    latitudes = []
    longitudes = []
    geometries = []
    
    for ugc in counties:
        latitude = ugc_county.loc[(ugc_county['STATE'] == state) & (ugc_county['FIPS'].astype(int) % 1000 == ugc)]['LAT'].tolist()
        longitude = ugc_county.loc[(ugc_county['STATE'] == state) & (ugc_county['FIPS'].astype(int) % 1000 == ugc)]['LON'].tolist()
        geometry = ugc_county.loc[(ugc_county['STATE'] == state) & (ugc_county['FIPS'].astype(int) % 1000 == ugc)]['geometry']
        latitudes.append(latitude)
        longitudes.append(longitude)
        geometries.append(geometry)
        
    flatten = itertools.chain.from_iterable
    latitudes = list(flatten(latitudes))
    longitudes = list(flatten(longitudes))

    return latitudes, longitudes, geometries

def convert_geojson_to_geopandas_df(alert_geojson):
    '''Returns map bounds for polygon-based NWS alerts'''
    alert_geojson['geometry'] = shape(alert_geojson['geometry'])
    gdf = geopandas.GeoDataFrame(alert_geojson).set_geometry('geometry')
    west_bound, south_bound, east_bound, north_bound = gdf['geometry'][0].bounds

    poly = gdf['geometry']
    alert_type = gdf['properties'].loc['event']
    
    return {
        'west_bound': west_bound,
        'south_bound': south_bound,
        'east_bound': east_bound,
        'north_bound': north_bound,
        'polygon': poly,
        'type': alert_type
    }

def calculate_ugc_geography(alert):
    ugcs = alert['properties']['geocode']['UGC']

    if is_ugc_county(ugcs):
        latitudes, longitudes, geometries = ugc_county_geography(ugcs)
    else:
        latitudes, longitudes, geometries = ugc_zone_geography(ugcs)
    
    return {
        'west_bound': min(longitudes),
        'south_bound': min(latitudes),
        'east_bound': max(longitudes),
        'north_bound': max(latitudes),
        'polygon': geometries
    }

def get_radar_timestamp():
    f = requests.get('https://mesonet.agron.iastate.edu/data/gis/images/4326/USCOMP/n0q_0.json').json()
    validDATE = f['meta']['valid']
    return validDATE

def create_map(alert):
    ''' Create the alert map'''
    alert_map_info = (
        convert_geojson_to_geopandas_df(alert) if alert['geometry'] else calculate_ugc_geography(alert))
                
    warning_cmap = {'Flood Watch': '#2E8B57',
                    'Flash Flood Watch': '#2E8B57',
                    'Flash Flood Warning': '#8B0000',
                    'Flood Warning': '#00FF00',
                    'Coastal Flood Watch': '#66CDAA',
                    'Coastal Flood Warning': '#228B22',
                    'Severe Thunderstorm Watch': '#DB7093',
                    'Severe Thunderstorm Warning': '#FFA500',
                    'Special Weather Statement': '#FFE4B5',
                    'Tornado Watch': '#FFFF00',
                    'Tornado Warning': '#FF0000',
                    'Storm Surge Watch': '#DB7FF7',
                    'Storm Surge Warning': '#B524F7',
                    'Dense Fog Advisory': '#708090',
                    'Rip Current Statement': '#40E0D0',
                    'Red Flag Warning': '#FF1493'}

    google_tiles = GoogleTiles()
    data_crs = ccrs.PlateCarree()

    # Setup matplotlib figure
    fig = Figure(figsize=(1280/72, 720/72))
    ax = fig.add_axes([0, 0, 1, 1], projection=data_crs)
    ax.add_image(google_tiles, 8)
    ax.set_extent([alert_map_info['west_bound'] - 0.5, alert_map_info['east_bound'] + 0.5, 
                   alert_map_info['south_bound'] - 0.5, alert_map_info['north_bound'] + 0.6], data_crs)
    ax.set_adjustable('datalim')

    # Setup borders (states, countries, coastlines, etc)
    ax.add_feature(USCOUNTIES.with_scale('20m'), edgecolor='gray', zorder=5, linewidth=1.2)
    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=3, zorder=5)

    # Add radar
    ax.add_wms(
        wms='https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0q-t.cgi?',
        layers='nexrad-n0q-wmst',
        wms_kwargs={'transparent':True, 'time': get_radar_timestamp()}, 
        zorder=4, alpha=0.4)

    # Plot alerts on the map
    for key in warning_cmap.keys():
        if key == alert['properties']['event'] and alert['geometry']:
            ax.add_geometries(alert_map_info['polygon'], crs=data_crs, facecolor=warning_cmap[key],
                              edgecolor='black', linewidth=4, zorder=6, alpha=0.04)
        elif key == alert['properties']['event'] and not alert['geometry']:
            for polys in alert_map_info['polygon']:
                ax.add_geometries(polys, crs=data_crs, facecolor=warning_cmap[key], edgecolor='black',
                                  linewidth=4,  alpha=0.5, zorder=6)
        else:
            continue

    # Set title
    title = ('SIGNIFICANT WEATHER ALERT' if alert['properties']['event'] == 'Special Weather Statement' 
             else alert['properties']['event'].upper())

    ax.set_title(title, loc='left', 
                 ha='left', va='top', fontsize=72, color='white', 
                 fontweight='bold', fontname='Arial', y=0.95, x=0.03, zorder=11,
                 bbox={'facecolor': '#0c3245', 'alpha': 1.0, 'edgecolor': 'none', 'boxstyle':'square,pad=0.2'})
    
    fig.savefig('alert_visual.png', dpi=72)