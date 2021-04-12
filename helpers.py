from datetime import datetime, timezone
import pytz
import time
import numpy as np
import requests

def api_get(url):
    response = requests.get(url, timeout=30, headers={"User-Agent": "curl/7.61.0"})
    
    if response.status_code != 200:
        raise requests.HTTPError(f'Error accessing {response.request.url}. Status code: {response.requests.status_code}')
    
    return response.json()

def convert_to_local(str):
    '''
    Takes in ISO8601 date and time and converts to 
    more human-readable date and time
    '''
    if str is None:
        return 'unspecified'
    
    date_time = datetime.strptime(str, "%Y-%m-%dT%H:%M:%S%z")
    date_time = datetime.strftime(date_time, '%a %b %-d %-I:%M %p')
    return date_time

def is_data_new_enough(datetime64, threshold_mins):
    '''
    Takes in a numpy datetime64 type and returns True if the current datetime
    is less than threshold_mins. Otherwise, it returns False.
    '''
    data_time = datetime64
    current_time = np.datetime64(datetime.utcnow())

    time_delta = current_time - data_time
    time_delta = time_delta.astype('timedelta64[m]')

    return True if time_delta < threshold_mins else False

def seconds_to_mins(seconds):
    return seconds // 60

def is_alert_active(expire_time):
    '''Checks to see whether alert is active or expired'''
    
    # Make python datetime UTC aware
    utc=pytz.UTC
    
    # Convert local expiration time to UTC
    datetime_object = datetime.strptime(expire_time, '%Y-%m-%dT%H:%M:%S%z')
    seconds_since_epoch = datetime_object.timestamp()
    target_time = datetime.utcfromtimestamp(seconds_since_epoch)
    target_time_utc = target_time.replace(tzinfo=utc)

    # Calculate current time in UTC
    now_obj = datetime.now(timezone.utc)
    now_obj_utc = now_obj.replace(tzinfo=utc)
    
    return True if now_obj_utc < target_time_utc else False

def utc_to_iso8601(utc):
    '''
    Accepts UTC time in the format returned by datetime module and returns it in ISO8601
    '''
    return utc.isoformat("T","microseconds")

def iso8601_to_utc(iso8601):
    '''Accepts ISO8601 time and returns it as a datetime type'''
    return datetime.strptime(iso8601, "%Y-%m-%dT%H:%M:%S.%f")

def datetime64_to_datetime(dt64):
    ''' Takes a numpy datetime64 type and converts to ISO8601'''
    unix_epoch = np.datetime64(0, 's')
    one_second = np.timedelta64(1, 's')
    seconds_since_epoch = (dt64 - unix_epoch) / one_second

    datetime_obj = datetime.utcfromtimestamp(seconds_since_epoch)
    return utc_to_iso8601(datetime_obj)
    

def current_day_time():
    tz_eastern = pytz.timezone('America/New_York') 
    datetime_eastern = datetime.now(tz_eastern)
    return datetime_eastern.strftime('%a %-I:%M %p')