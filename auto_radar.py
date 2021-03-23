from siphon.catalog import TDSCatalog
import cartopy.crs as ccrs
import xarray as xr
import numpy as np
import metpy

from auto_tweet import tweet_text_only

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

def get_grid_values(nw_lat, nw_lon, se_lat, se_lon):
    x_UL, y_UL = convert_latlon_to_xy(nw_lat, nw_lon)
    x_LR, y_LR = convert_latlon_to_xy(se_lat, se_lon)

    data_array = ds.metpy.sel(x=slice(x_UL, x_LR), y=slice(y_LR, y_UL))
    return data_array.values

def is_threshold_reached(array, threshold):
    return np.any(array[:, :] >= threshold)

# Trigger
trigger = 45

ds = get_catalog()['Base_reflectivity_surface_layer'].squeeze()
raw_data = get_grid_values(35, -80, 30.2, -75)
result = is_threshold_reached(raw_data, trigger)

print(f'[AUTOMATION]: {trigger} dBZ radar echo detected within bounding box' if result else 'Trigger not reached.')

print(result)