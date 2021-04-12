from datetime import datetime, timedelta
from random import random
from siphon.catalog import TDSCatalog
import cartopy.crs as ccrs
import xarray as xr
import numpy as np
import metpy

from social import Twitter
from db import Database
from helpers import is_data_new_enough, utc_to_iso8601, iso8601_to_utc, datetime64_to_datetime, seconds_to_mins, current_day_time

radar_database = Database('DYNAMODB_TABLE_RADAR')
#tweet = Twitter('ray_hawthorne')

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

def get_grid_values(bounding_box: []):
    nw_lat, nw_lon, se_lat, se_lon = bounding_box
    x_UL, y_UL = convert_latlon_to_xy(nw_lat, nw_lon)
    x_LR, y_LR = convert_latlon_to_xy(se_lat, se_lon)

    data_array = ds.metpy.sel(x=slice(x_UL, x_LR), y=slice(y_LR, y_UL))
    return data_array.values

def is_threshold_reached(array, threshold):
    return np.any(array[:, :] >= threshold)

def is_eligible_for_tweeting(radar_metadata: []):
    time_deltas = [(iso8601_to_utc(time_script_ran) - iso8601_to_utc(data['data_time'])).seconds for data in radar_metadata]
    time_deltas = [seconds_to_mins(delta) for delta in time_deltas]
    data_with_timedeltas = [dict(data, timedelta=time_deltas[idx]) for idx, data in enumerate(radar_metadata)]
    eligible_radars = [location for location in data_with_timedeltas if location['timedelta'] >= 60 and location['threshold_reached']]
    return eligible_radars

def tweet_message(eligible_data: []):
    if eligible_data:
        [tweet.tweet_image_from_web(info['img_url'], f"[{current_day_time()}]: Radar update in the {info['region']} area") for info in eligible_data]
    
def main():
    area_names = [area['area'] for area in areas]
    coords = [area['coords'] for area in areas]
    url = [area['url'] for area in areas]
    ids = [area['id'] for area in areas]

    # Set Trigger. Example: 50 dBZ for radar.
    trigger = 30

    # Check to see if radar data from server is new enough to process
    if is_data_new_enough(ds.time.values, 30):
        for idx, place_of_interest in enumerate(coords):
            raw_data = get_grid_values(place_of_interest)
            threshold_reached = bool(is_threshold_reached(raw_data, trigger))

            # If threshold reached, save data to database
            radar_database.put(
                {'id': ids[idx], 
                'timestamp': time_script_ran,
                'data_time': datetime64_to_datetime(ds.time.values),
                'region': area_names[idx], 
                'img_url': url[idx],
                'threshold_reached': threshold_reached}) #if threshold_reached else None   

            print(f'[AUTOMATION]: {trigger} dBZ radar echo detected in the {area_names[idx]} area' 
            if threshold_reached else 'Trigger not reached.')
        
        is_eligible = is_eligible_for_tweeting(radar_database.get_all())
        print(is_eligible)
        #tweet_message(is_eligible)

# Areas of interest
areas = [
    {'id': '01',
     'area': 'Western Panhandle',
     'coords': [31.0, -87.7, 30.8, -86.4],
     'url': 'https://pbsweather.org/maps/FL/radars/WUWF-Radar.jpg'},
    {'id': '02',
     'area': 'Panama City',
     'coords': [30.5, -86, 29.9, -85.4],
     'url': 'https://pbsweather.org/maps/FL/radars/WKGC-Radar.jpg'},
    {'id': '03',
     'area': 'Tallahassee',
     'coords': [30.7, -84.7, 30.2, -84.0],
     'url': 'https://pbsweather.org/maps/FL/radars/WFSU-Radar.jpg'},
    {'id': '04',
     'area': 'Lake City',
     'coords': [30.3, -82.8, 30.0, -82.5],
     'url': 'https://pbsweather.org/maps/FL/radars/WUFT-Radar.jpg'},
    {'id': '05',
     'area': 'Jacksonville',
     'coords': [30.7, -82.0, 30.0, -81.3],
     'url': 'https://pbsweather.org/maps/FL/radars/WJCT-Radar.jpg'},
    {'id': '06',
     'area': 'Gainesville',
     'coords': [29.9, -82.65, 29.48, -82.05],
     'url': 'https://pbsweather.org/maps/FL/radars/WUFT-Radar.jpg'},
    {'id': '07',
     'area': 'Orlando',
     'coords': [28.8, -81.5, 28.24, -81.27],
     'url': 'https://pbsweather.org/maps/FL/radars/WMFE-Radar.jpg'},
    {'id': '08',
     'area': 'Tampa/St Pete',
     'coords': [28.16, -82.86, 27.65, -82.25],
     'url': 'https://pbsweather.org/maps/FL/radars/WUSF-Radar.jpg'},
    {'id': '09',
     'area': 'Fort Myers',
     'coords': [26.75, -82.27, 26.40, -81.75],
     'url': 'https://pbsweather.org/maps/FL/radars/WGCU-Radar.jpg'},
    {'id': '10',
     'area': 'Space Coast',
     'coords': [28.65, -80.89, 27.97, -80.43],
     'url': 'https://pbsweather.org/maps/FL/radars/WFIT-Radar.jpg'},
    {'id': '11',
     'area': 'Treasure Coast',
     'coords': [27.67, -80.54, 27.16, -80.15],
     'url': 'https://pbsweather.org/maps/FL/radars/WQCS-Radar.jpg'},
    {'id': '12',
     'area': 'Miami-Dade County',
     'coords': [25.89, -80.50, 25.43, -80.05],
     'url': 'https://pbsweather.org/maps/FL/radars/WLRN-Radar.jpg'},
]

ds = get_catalog()['Base_reflectivity_surface_layer'].squeeze()
time_script_ran = utc_to_iso8601(datetime.utcnow())

if __name__ == '__main__':
    main()