import os
from decimal import Decimal
import json
from datetime import datetime
import argparse

import tweepy
import requests

from social import Twitter
from db import Database
from helpers import convert_to_local, is_alert_active, api_get
from auto_polygon import create_map

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--account', help='Twitter account name')
args = parser.parse_args()

if args.account:
    dynamo = Database(Twitter.creds[args.account]['db_table_env_var'])
    tweet = Twitter(args.account)
else:
    print('Specify an -a or --account argument')
    exit()
    
def prepare_alert_message(alert):
    _id = alert['properties']['id']
    hyperlink = f'https://alerts-v2.weather.gov/#/?id={_id}'
    is_polygon_based = alert['geometry']
    event = alert['properties']['event']
    nws_office = alert['properties']['senderName']
    locations = alert['properties']['areaDesc']
    sent = alert['properties']['sent']
    onset = alert['properties']['onset']
    ends = alert['properties']['ends']
    effective = alert['properties']['effective']
    expires = alert['properties']['expires']
    status = alert['properties']['status']
    headline = (
        alert['properties']['parameters']['NWSheadline'] 
        if 'NWSheadline' in alert['properties']['parameters'].keys() else None)
    
    if ends is None:
        ends = expires 
    
    if headline and not is_polygon_based:
        message = f'{nws_office} issues {event}: {headline[0].title()}.'
    else:
        message = f'{event} for {locations} from {convert_to_local(onset)} until {convert_to_local(ends)}.'
    
    return message
    
def get_alerts(usa_state):
    data = api_get(f"https://api.weather.gov/alerts/active?status=actual&message_type=alert&{Twitter.creds[args.account]['api_endpoint']}")
    alerts = data['features']
    return alerts

def aggregate_message_and_media():
    alerts_of_interest = ['Tornado Warning', 'Severe Thunderstorm Warning', 'Flash Flood Warning']
    tweetable_alerts = []
    new_alerts = retrieve_new_alerts()
    new_messages = []

    tweetable_alerts = [new_alert for new_alert in new_alerts if new_alert['properties']['event'] in alerts_of_interest]
    
    if tweetable_alerts:
        for tweetable_alert in tweetable_alerts:
            create_map(tweetable_alert, args.account)
            media = tweet.twitter_media_upload('alert_visual.png')
            new_messages.append({'message': prepare_alert_message(tweetable_alert), 'media': media.media_id})
    
    return new_messages
      
def retrieve_new_alerts():    
    # Make API call to retrieve alerts    
    alerts = get_alerts('fl')

    # Retrieve active alerts from the database
    active_alerts = dynamo.get_all()

    # Remove expired alerts from database
    expired_alerts = list(filter(lambda alert: is_alert_active(alert['expires']) == False, active_alerts))
    [dynamo.delete(expired_alert['id']) for expired_alert in expired_alerts]

    # Store any new alerts since the script last ran
    new_alerts = []
    
    # Add new alerts to active_alerts list if they don't already exist and
    # double-check to make sure any of the new alerts aren't already expired
    for alert in alerts:
        if (alert['properties']['id'] not in list(map(lambda alert: alert['id'], active_alerts))
        and is_alert_active(alert['properties']['expires'])):
            dynamo.put(json.loads(json.dumps({
                'id': alert['properties']['id'],
                'event': alert['properties']['event'],
                'areaDesc': alert['properties']['areaDesc'],
                'expires': alert['properties']['expires']
            }), parse_float=Decimal))
            new_alerts.append(alert)

    print('----')
    print('New Alerts: ', list(map(lambda new_alert: new_alert['properties']['id'], new_alerts)))
    print('Active Alerts: ', list(map(lambda active_alert: active_alert['id'], active_alerts)))
    
    return new_alerts

def log_alerts_messages():
    [print(f"{message['message'][:270], message['media']}") for message in aggregate_message_and_media()]     
    print(f'{datetime.utcnow()} - Alerts logging ran successfully')
    
def send_tweets_alerts():
    [tweet.tweet_text_and_media(message['message'], message['media']) for message in aggregate_message_and_media()]
    print(f'{datetime.utcnow()} - Tweet alert code ran successfully!')

if __name__ == '__main__':
    #log_alerts_messages()
    send_tweets_alerts()