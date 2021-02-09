import tweepy
import requests
import os
from datetime import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler

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

def extract_alert_data(alert: list[dict]) -> dict:
    _id = alert['properties']['id']
    hyperlink = f'https://alerts-v2.weather.gov/#/?id={_id}'
    event = alert['properties']['event']
    locations = alert['properties']['areaDesc']
    onset = alert['properties']['onset']
    ends = alert['properties']['ends']
    effective = alert['properties']['effective']
    expires = alert['properties']['expires']
    
    if ends is None:
        ends = expires 
    
    message = f'{event} for {locations} from {convert_to_local(onset)} until {convert_to_local(ends)}'
    
    return {
        'id': _id,
        'hyperlink': hyperlink,
        'message': message,
        'event': event,
        'locations': locations,
        'onset': onset,
        'ends': ends,
        'effective': effective,
        'expires': expires
    }
    
def get_alerts(usa_state: str) -> dict:
    data = api_get(f'https://api.weather.gov/alerts/active/area/{usa_state.upper()}')
    alerts = data['features']
    alerts = list(map(extract_alert_data, alerts))
    return alerts
    

active_alerts_ids = []
new_alerts_ids = []

def prepare_tweet_alerts_messages() -> list:
    alerts = get_alerts('wi')
    
    # Get all IDs
    ids = list(map(lambda alert: alert['id'], alerts))
    
    # Store Alert IDs
    # If alert ID appears that isn't already in active_alerts_ids, store it in new_alerts_ids
    new_alerts_ids = []
    for id in ids:
        if id not in active_alerts_ids:
            active_alerts_ids.append(id)
            new_alerts_ids.append(id)
    
    # Get messages associated with any new alerts IDs
    new_alerts = []
    for new_alert_id in new_alerts_ids:
        new_alerts.append(next(alert for alert in alerts if alert["id"] == new_alert_id))
    
    new_messages = list(map(lambda new_alert: new_alert['message'], new_alerts))
    
    return new_messages

def send_tweets_alerts():
    [tweet_text_only(tweet[:280]) for tweet in prepare_tweet_alerts_messages() if len(tweet) > 0]
    print(f'{datetime.utcnow()} - Tweet alert code ran successfully!')

def log_alerts_messages():
    [print(message[:280]) for message in prepare_tweet_alerts_messages() if len(message) > 0]
    print(f'{datetime.utcnow()} - Alerts logging ran successfully')

# Initial run of the program - Get all existing alerts and send tweet
log_alerts_messages()
#send_tweets_alerts()

# Code for later
#tweet_image_from_web('https://pbsweather.org/maps/FL/currents/FL-Temps.jpg', 'Current temperatures across Florida')
#tweet_image_from_local('cold.png', 'Another test')
    
# Run scheduled task
if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(log_alerts_messages, trigger='interval', minutes=10)
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()