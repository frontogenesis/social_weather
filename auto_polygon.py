from matplotlib.figure import Figure
from metpy.plots import USCOUNTIES
import geopandas
from cartopy import crs as ccrs
from cartopy.io.img_tiles import GoogleTiles, OSM, Stamen
import cartopy.feature as cfeature
from shapely.geometry import shape, Polygon
import itertools

cat_gdf = geopandas.read_file('z_30mr21/z_30mr21.shp')

def convert_geojson_to_geopandas_df(alert_geojson):
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
    counties = alert['properties']['geocode']['UGC']
    counties = [county.replace('Z', '') for county in counties]

    latitudes = []
    longitudes = []
    
    for ugc in counties:
        latitude = (cat_gdf[cat_gdf['STATE_ZONE'] == ugc]['LAT']).tolist()
        longitude = (cat_gdf[cat_gdf['STATE_ZONE'] == ugc]['LON']).tolist()
        latitudes.append(latitude)
        longitudes.append(longitude)
        
    flatten = itertools.chain.from_iterable
    latitudes = list(flatten(latitudes))
    longitudes = list(flatten(longitudes))
    
    return {
        'west_bound': min(longitudes),
        'south_bound': min(latitudes),
        'east_bound': max(longitudes),
        'north_bound': max(latitudes),
        'polygon': counties
    }

def create_map(alert):
    if alert['geometry']:
        alert_map_info = convert_geojson_to_geopandas_df(alert)
    else:
        alert_map_info = calculate_ugc_geography(alert)
                
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
                    'Hurricane Watch': '#FF00FF',
                    'Hurricane Warning': '#DC143C',
                    'Tropical Storm Watch': '#F08080',
                    'Tropical Storm Warning': '#B22222',
                    'Storm Surge Watch': '#DB7FF7',
                    'Storm Surge Warning': '#B524F7',
                    'Dense Fog Advisory': '#708090',
                    'Rip Current Statement': '#40E0D0',
                    'Red Flag Warning': '#FF1493'}

    image = GoogleTiles()
    data_crs = ccrs.PlateCarree()

    # Setup matplotlib figure
    fig = Figure(figsize=(1920/72, 1080/72))
    ax = fig.add_axes([0, 0, 1, 1], projection=data_crs)
    ax.add_image(image, 8)
    ax.set_extent([alert_map_info['west_bound'] - 0.5, alert_map_info['east_bound'] + 0.5, 
                   alert_map_info['south_bound'] - 0.5, alert_map_info['north_bound'] + 0.5], data_crs)
    ax.set_adjustable('datalim')

    # Setup borders (states, countries, coastlines, etc)
    ax.add_feature(USCOUNTIES.with_scale('20m'), edgecolor='gray', zorder=5, linewidth=0.8)
    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=3, zorder=5)
    
    # Plot polygon or UGC-based alert
    for key in warning_cmap.keys():
        if key == alert['properties']['event'] and alert['geometry']:
            ax.add_geometries(alert_map_info['polygon'], crs=data_crs, facecolor=warning_cmap[key],
                              edgecolor='black', linewidth=4, zorder=1, alpha=0.04)
        elif key == alert['properties']['event'] and not alert['geometry']:   
            for ugc in alert_map_info['polygon']:
                ax.add_geometries(cat_gdf[cat_gdf['STATE_ZONE'] == ugc]['geometry'], crs=data_crs, 
                                  facecolor=warning_cmap[key], edgecolor='black', 
                                  linewidth=4,  alpha=0.5, zorder=6)
        else:
            continue

    # Set title
    title = ('Significant Weather Alert' if alert['properties']['event'] == 'Special Weather Statement' 
             else alert['properties']['event'])

    ax.set_title(title, loc='left', 
                 ha='left', va='top', fontsize=72, color='white', 
                 fontweight='bold', fontname='Arial', y=0.95, x=0.03, zorder=11,
                 bbox=dict(facecolor='navy', alpha=1.0, edgecolor='none'))
    
    fig.savefig('alert_visual.png', dpi=72)