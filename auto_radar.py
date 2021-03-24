from datetime import datetime
from siphon.catalog import TDSCatalog
import cartopy.crs as ccrs
import xarray as xr
import numpy as np
import metpy

from auto_tweet import tweet_text_only
from helpers import is_data_new_enough

def get_catalog():
    radar = TDSCatalog('https://thredds.ucar.edu/thredds/catalog/grib/nexrad/composite/unidata/latest.xml')
    data = radar.datasets[0].remote_access(use_xarray=True)
    return data.metpy.parse_cf()

def get_projection_info(ds):
    return ds.metpy.cartopy_crs

def convert_latlon_to_xy(lat, lon):
    plot_proj = ds.metpy.cartopy_crs
    location = get_projection_info(ds).transform_point(lon, lat, ccrs.PlateCarree())
    x, y = location
    return x, y

def get_grid_values(bounding_box):
    nw_lat, nw_lon, se_lat, se_lon = bounding_box
    x_UL, y_UL = convert_latlon_to_xy(nw_lat, nw_lon)
    x_LR, y_LR = convert_latlon_to_xy(se_lat, se_lon)

    data_array = ds.metpy.sel(x=slice(x_UL, x_LR), y=slice(y_LR, y_UL))
    return data_array.values

def is_threshold_reached(array, threshold):
    return np.any(array[:, :] >= threshold)

# Trigger. Example: 50 dBZ for radar.
trigger = 50

# Areas of interest
areas = {
    'Western Panhandle': [31.0, -87.7, 30.8, -86.4],
    'Panama City': [30.5, -86, 29.9, -85.4],
    'Tallahassee': [30.7, -84.7, 30.2, -84.0],
    'Lake City': [30.3, -82.8, 30.0, -82.5],
    'Jacksonville': [30.7, -82.0, 30.0, -81.3],
    'Gainesville': [29.9, -82.65, 29.48, -82.05],
    'Daytona Beach': [29.35, -81.15, 29.0, -80.05],
    'Orlando': [28.8, -81.5, 28.24, -81.27],
    'Tampa/St Pete': [28.16, -82.86, 27.65, -82.25],
    'Sarasota': [27.54, -82.75, 27.28, -82.43],
    'Fort Myers': [26.75, -82.27, 26.40, -81.75],
    'Naples': [26.20, -81.9, 25.84, -81.62],
    'Space Coast': [28.65, -80.89, 27.97, -80.43],
    'Treasure Coast': [27.67, -80.54, 27.16, -80.15],
    'Palm Beach County': [26.84, -80.19, 26.33, -80.00],
    'Broward County': [26.26, -80.3, 25.97, -80.1],
    'Miami-Dade County': [25.89, -80.50, 25.43, -80.05],
}

ds = get_catalog()['Base_reflectivity_surface_layer'].squeeze()
ds_time = ds.time.values

if is_data_new_enough(ds_time, 30):
    for area, coords in areas.items():
        place_of_interest = [coord for coord in coords]
        raw_data = get_grid_values(place_of_interest)
        result = is_threshold_reached(raw_data, trigger)
        print(f'[AUTOMATION]: {trigger} dBZ radar echo detected in the {area} area' if result else 'Trigger not reached.')