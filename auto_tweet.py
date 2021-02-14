import tweepy
import requests
import os
from datetime import datetime, timezone
import pytz
import time
from apscheduler.schedulers.background import BackgroundScheduler

from auto_polygon import create_map

def twitter_api():
    consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
    consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    return api

def tweet_text_only(message):
    twitter_api().update_status(message)

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
    response = requests.get(url, headers={"User-Agent": "curl/7.61.0"})
    return response.json()

def convert_to_local(str) -> str:
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

def prepare_alert_message(alert: dict) -> str:
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
    
def get_alerts(usa_state: str) -> dict:
    data = api_get(f'https://api.weather.gov/alerts/active/area/{usa_state.upper()}')
    alerts = data['features']
    return alerts
    

active_alerts = []
new_alerts = []

def send_tweet_alerts_messages() -> list:
    global active_alerts
    
    def package_text_and_media(new_alert):
        new_messages.append(prepare_alert_message(new_alert))
        create_map(new_alert)
        
    alerts = get_alerts('fl')
    
    # Store any new alerts since the script last ran
    new_alerts = []
    
    # Add new alerts to active_alerts list if they don't already exist
    for alert in alerts:
        if alert['properties']['id'] not in list(map(lambda alert: alert['properties']['id'], active_alerts)):
            active_alerts.append(alert)
            new_alerts.append(alert)
            
    # Keep all active alerts and remove all expired alerts
    active_alerts = list(filter(lambda alert: is_alert_active(alert['properties']['expires']), active_alerts)) 
    
    print(list(map(lambda new_alert: new_alert['properties']['id'], new_alerts)))
    print(list(map(lambda active_alert: active_alert['properties']['id'], active_alerts)))
    print('----')
    
    new_messages = []
    list(map(package_text_and_media, new_alerts))
    
    return new_messages

def log_alerts_messages():
    [print(message[:280]) for message in send_tweet_alerts_messages() if len(message) > 0]
    print(f'{datetime.utcnow()} - Alerts logging ran successfully')
    
def send_tweets_alerts():
    [tweet_image_from_local('alert_visual.png', tweet[:280]) for tweet in send_tweet_alerts_messages() if len(tweet) > 0]
    print(f'{datetime.utcnow()} - Tweet alert code ran successfully!')

# Initial run of the program - Get all existing alerts and send tweet
#log_alerts_messages()
send_tweets_alerts()
    
# Run scheduled task
if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_tweets_alerts, trigger='interval', minutes=10)
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()