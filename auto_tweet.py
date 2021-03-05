import tweepy
import requests
import os
from decimal import Decimal
import json
from datetime import datetime, timezone
import pytz
import time
import boto3
from botocore.exceptions import ClientError

from auto_polygon import create_map

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

def put_alert(alert):
    response = table.put_item(Item={
        'id': alert['properties']['id'],
        'expires': alert['properties']['expires']
    })
    return response

def get_existing_alerts():
    try:
        response = table.scan()
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response['Items']

def delete_expired_alert(id):
    try:
        response = table.delete_item(Key={'id': id})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response

def twitter_api():
    consumer_key = os.environ['TWITTER_CONSUMER_KEY']
    consumer_secret = os.environ['TWITTER_CONSUMER_SECRET']
    access_token = os.environ['TWITTER_ACCESS_TOKEN']
    access_token_secret = os.environ['TWITTER_ACCESS_TOKEN_SECRET']

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    return api

def tweet_text_only(message):
    message = f'{message[:270]} #FLwx'
    try:
        twitter_api().update_status(message)
    except tweepy.TweepError as e:
        print(f'Error message: {e.reason}. Intended tweet: {message}')
        return
    
def tweet_text_and_media(message, media_id):
    message = f'{message[:270]} #FLwx'
    try:
        twitter_api().update_status(status=message, media_ids=[media_id])
    except tweepy.TweepError as e:
        print(f'Error message: {e.reason}. Intended media_id: {media_id} Intended tweet:{message}')
        return

def twitter_media_upload(filename):
    media = twitter_api().media_upload(filename)
    return media

def tweet_image_from_web(url, message):
    filename = 'temp.jpg'
    request = requests.get(url, stream=True)
    if request.status_code == 200:
        with open(filename, 'wb') as image:
            for chunk in request:
                image.write(chunk)

        twitter_api().update_with_media(filename, status=message)
        os.remove(filename)
    else:
        print('Unable to download image')
        
def tweet_image_from_local(filename, message):
    twitter_api().update_with_media(filename, message)
    
def api_get(url):
    response = requests.get(url, timeout=30, headers={"User-Agent": "curl/7.61.0"})
    
    if response.status_code != 200:
        raise requests.HTTPError(f'Error accessing {response.request.url}. Status code: {response.requests.status_code}')
    
    return response.json()

def convert_to_local(str):
    if str is None:
        return 'unspecified'
    
    date_time = datetime.strptime(str, "%Y-%m-%dT%H:%M:%S%z")
    date_time = datetime.strftime(date_time, '%a %b %-d %-I:%M %p')
    return date_time

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

def prepare_alert_message(alert):
    _id = alert['properties']['id']
    hyperlink = f'https://alerts-v2.weather.gov/#/?id={_id}'
    event = alert['properties']['event']
    locations = alert['properties']['areaDesc']
    onset = alert['properties']['onset']
    ends = alert['properties']['ends']
    effective = alert['properties']['effective']
    expires = alert['properties']['expires']
    status = alert['properties']['status']
    
    if ends is None:
        ends = expires 
    
    if status != 'Test':
        message = f'{event} for {locations} from {convert_to_local(onset)} until {convert_to_local(ends)}'
    else:
        message = ''
    
    return message
    
def get_alerts(usa_state):
    data = api_get(f'https://api.weather.gov/alerts/active/area/{usa_state.upper()}')
    alerts = data['features']
    return alerts
    
def send_tweet_alerts_messages():
    
    def package_text_and_media(new_alert):
        message_type = new_alert['properties']['messageType']
        event = new_alert['properties']['event']
        
        alerts_of_interest = ['Tornado Warning', 'Severe Thunderstorm Warning', 'Flash Flood Warning',
                              'Tornado Watch', 'Severe Thunderstorm Watch', 'Flood Warning',
                              'Rip Current Statement']
        
        tweetable_alert = [new_alert for alert_of_interest in alerts_of_interest 
                           if alert_of_interest == event and message_type == 'Alert']
        
        if tweetable_alert and new_alert['geometry']:
            create_map(new_alert)
            media = twitter_media_upload('alert_visual.png')
            new_messages.append({'message': prepare_alert_message(new_alert), 
                                 'media': media.media_id})
        elif tweetable_alert:
            new_messages.append({'message': prepare_alert_message(new_alert)})   
        
    # Make API call to retrieve alerts    
    alerts = get_alerts('fl')

    # Retrieve active alerts from the database
    active_alerts = get_existing_alerts()

    # Store any new alerts since the script last ran
    new_alerts = []
    
    # Add new alerts to active_alerts list if they don't already exist
    # Add the new alerts that came in since the script last ran
    for alert in alerts:
        if alert['properties']['id'] not in list(map(lambda alert: alert['id'], active_alerts)):
            put_alert(json.loads(json.dumps(alert), parse_float=Decimal))
            new_alerts.append(alert)
      
    # Remove expired alerts from database
    expired_alerts = list(filter(lambda alert: is_alert_active(alert['expires']) == False, active_alerts))
    [delete_expired_alert(expired_alert['id']) for expired_alert in expired_alerts]

    print('----')
    print('New Alerts: ', list(map(lambda new_alert: new_alert['properties']['id'], new_alerts)))
    print('Active Alerts: ', list(map(lambda active_alert: active_alert['id'], active_alerts)))
    
    new_messages = []
    list(map(package_text_and_media, new_alerts))
    
    return new_messages

def log_alerts_messages():
    [print(f"{new_tweet['message'][:270], new_tweet['media']} #FLwx") if 'media' in new_tweet 
     else print(f"{new_tweet['message'][:270]} #FLwx") for new_tweet in send_tweet_alerts_messages()]
            
    print(f'{datetime.utcnow()} - Alerts logging ran successfully')
    
def send_tweets_alerts():
    [tweet_text_and_media(new_tweet['message'], new_tweet['media']) if 'media' in new_tweet 
     else tweet_text_only(new_tweet['message']) for new_tweet in send_tweet_alerts_messages()]
    
    print(f'{datetime.utcnow()} - Tweet alert code ran successfully!')
    
log_alerts_messages()