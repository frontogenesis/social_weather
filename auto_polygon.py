import matplotlib.pyplot as plt
from metpy.plots import USCOUNTIES
import geopandas
from cartopy import crs as ccrs
from cartopy.io.img_tiles import GoogleTiles, OSM, Stamen
import cartopy.feature as cfeature
from shapely.geometry import shape, Polygon

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

def create_map(alert):
    if alert['geometry']:
        alert_map_info = convert_geojson_to_geopandas_df(alert)
    else:
        return
                
    warning_cmap = {'Flood Advisory': '#00FF7F',
                    'Flash Flood Warning': '#8B0000',
                    'Flood Warning': '#00FF00',
                    'Severe Thunderstorm Warning': '#FFA500',
                    'Special Weather Statement': '#FFE4B5',
                    'Tornado Warning': '#FF0000'}

    image = GoogleTiles()
    data_crs = ccrs.PlateCarree()

    # Setup matplotlib figure
    fig = plt.figure(figsize=(1920/72, 1080/72))
    ax = fig.add_axes([0, 0, 1, 1], projection=data_crs)

    ax.add_image(image, 8)
    ax.set_extent([alert_map_info['west_bound'] - 0.5, alert_map_info['east_bound'] + 0.5, 
                   alert_map_info['south_bound'] - 0.5, alert_map_info['north_bound'] + 0.5], data_crs)
    ax.set_adjustable('datalim')

    # Setup borders (states, countries, coastlines, etc)
    ax.add_feature(USCOUNTIES.with_scale('20m'), edgecolor='black', zorder=5, linewidth=0.3)
    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=3, zorder=5)
    
    # Plot polygon
    for key in warning_cmap.keys():
        if key == alert_map_info['type']:
            ax.add_geometries(alert_map_info['polygon'], crs=data_crs, facecolor=warning_cmap[key],
                              edgecolor='black', linewidth=4, zorder=1, alpha=0.04)
        else:
            ax.add_geometries(alert_map_info['polygon'], crs=data_crs, facecolor='none',
                              edgecolor='black', linewidth=4, zorder=1)

    # Set title
    ax.set_title(alert_map_info['type'], loc='left', 
                 ha='left', va='top', fontsize=72, color='white', 
                 fontweight='bold', fontname='Arial', y=0.95, x=0.03, zorder=11,
                 bbox=dict(facecolor='navy', alpha=1.0, edgecolor='none'))

    plt.savefig('alert_visual.png', dpi=72)