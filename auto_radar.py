from datetime import datetime, timedelta
from siphon.catalog import TDSCatalog
import cartopy.crs as ccrs
import xarray as xr
import numpy as np
import metpy

from social import Twitter
from db import Database
from helpers import is_data_new_enough, utc_to_iso8601, iso8601_to_utc, seconds_to_hours

radar_database = Database('DYNAMODB_TABLE_RADAR')
tweet = Twitter('ray_hawthorne', '#FLwx')

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
trigger = 15

# Areas of interest
areas = [
    {'area': 'Western Panhandle',
     'coords': [31.0, -87.7, 30.8, -86.4],
     'url': 'https://pbsweather.org/maps/FL/radars/WUWF-Radar.jpg'},
    {'area': 'Panama City',
     'coords': [30.5, -86, 29.9, -85.4],
     'url': 'https://pbsweather.org/maps/FL/radars/WKGC-Radar.jpg'},
    {'area': 'Tallahassee',
     'coords': [30.7, -84.7, 30.2, -84.0],
     'url': 'https://pbsweather.org/maps/FL/radars/WFSU-Radar.jpg'},
    {'area': 'Lake City',
     'coords': [30.3, -82.8, 30.0, -82.5],
     'url': 'https://pbsweather.org/maps/FL/radars/WUFT-Radar.jpg'},
    {'area': 'Jacksonville',
     'coords': [30.7, -82.0, 30.0, -81.3],
     'url': 'https://pbsweather.org/maps/FL/radars/WJCT-Radar.jpg'},
    {'area': 'Gainesville',
     'coords': [29.9, -82.65, 29.48, -82.05],
     'url': 'https://pbsweather.org/maps/FL/radars/WUFT-Radar.jpg'},
    {'area': 'Orlando',
     'coords': [28.8, -81.5, 28.24, -81.27],
     'url': 'https://pbsweather.org/maps/FL/radars/WMFE-Radar.jpg'},
    {'area': 'Tampa/St Pete',
     'coords': [28.16, -82.86, 27.65, -82.25],
     'url': 'https://pbsweather.org/maps/FL/radars/WUSF-Radar.jpg'},
    {'area': 'Fort Myers',
     'coords': [26.75, -82.27, 26.40, -81.75],
     'url': 'https://pbsweather.org/maps/FL/radars/WGCU-Radar.jpg'},
    {'area': 'Space Coast',
     'coords': [28.65, -80.89, 27.97, -80.43],
     'url': 'https://pbsweather.org/maps/FL/radars/WFIT-Radar.jpg'},
    {'area': 'Treasure Coast',
     'coords': [27.67, -80.54, 27.16, -80.15],
     'url': 'https://pbsweather.org/maps/FL/radars/WQCS-Radar.jpg'},
    {'area': 'Miami-Dade County',
     'coords': [25.89, -80.50, 25.43, -80.05],
     'url': 'https://pbsweather.org/maps/FL/radars/WLRN-Radar.jpg'},
]

# ds = get_catalog()['Base_reflectivity_surface_layer'].squeeze()
time_script_ran = utc_to_iso8601(datetime.utcnow())
# ds_time = ds.time.values

# area_names = [area['area'] for area in areas]
# coords = [area['coords'] for area in areas]
# url = [area['url'] for area in areas]

# stored_data = radar_database.get_all()
# print(stored_data)

# if is_data_new_enough(ds_time, 30):
#     for idx, place_of_interest in enumerate(coords):
#         raw_data = get_grid_values(place_of_interest)
#         result = bool(is_threshold_reached(raw_data, trigger))
#         radar_database.put(
#             {'id': str(idx).zfill(2), 
#             'timestamp': time_script_ran, 
#             'region': area_names[idx], 
#             'threshold_reached': result})
#         print(f'[AUTOMATION]: {trigger} dBZ radar echo detected in the {area_names[idx]} area' 
#         if result else 'Trigger not reached.')

        # tweet.tweet_image_from_web(
        #     url[idx], f'[AUTOMATION]: >{trigger} dBZ radar echo detected in the {area_names[idx]} area' if result else None)

stored_data = [{'threshold_reached': True, 'region': 'Jacksonville', 'id': '04', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': True, 'region': 'Tallahassee', 'id': '02', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': True, 'region': 'Orlando', 'id': '06', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': False, 'region': 'Gainesville', 'id': '05', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': False, 'region': 'Fort Myers', 'id': '08', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': False, 'region': 'Western Panhandle', 'id': '00', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': True, 'region': 'Tampa/St Pete', 'id': '07', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': True, 'region': 'Panama City', 'id': '01', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': True, 'region': 'Miami-Dade County', 'id': '11', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': False, 'region': 'Lake City', 'id': '03', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': True, 'region': 'Treasure Coast', 'id': '10', 'timestamp': '2021-03-26T22:05:08.304301'}, {'threshold_reached': True, 'region': 'Space Coast', 'id': '09', 'timestamp': '2021-03-26T22:05:08.304301'}]
time_deltas = [(iso8601_to_utc(time_script_ran) - iso8601_to_utc(data['timestamp'])).seconds for data in stored_data]
time_deltas = [seconds_to_hours(delta) for delta in time_deltas]
stored_data = [dict(data, timedelta=time_deltas[idx]) for idx, data in enumerate(stored_data)]