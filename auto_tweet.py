from decimal import Decimal
import json
from datetime import datetime

from social import Twitter
from db import Database
from accounts_args import account_info 
from accounts import creds
from helpers import convert_to_local, is_alert_active, api_get
from auto_polygon import create_map
from banner import upload_and_transform, upload_and_no_transform, cleanup

dynamo = Database(creds[account_info()]['db_table_env_var'])
tweet = Twitter(account_info())
    
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
    
def get_alerts(endpoint):
    data = api_get(f"https://api.weather.gov/alerts/active?status=actual&message_type=alert&{endpoint}")
    alerts = data['features']
    return alerts

def aggregate_message_and_media():
    alerts_of_interest = [
        'Tornado Warning', 'Severe Thunderstorm Warning', 'Flash Flood Warning',
        'Tornado Watch', 'Severe Thunderstorm Watch']

    tweetable_alerts = []
    new_alerts = retrieve_new_alerts()
    new_messages = []

    tweetable_alerts = [new_alert for new_alert in new_alerts if new_alert['properties']['event'] in alerts_of_interest]
    
    if tweetable_alerts:
        for tweetable_alert in tweetable_alerts:
            create_map(tweetable_alert)
            img_url = (
                upload_and_transform(tweetable_alert['properties']['event']) if creds[account_info()]['overlays'] 
                else upload_and_no_transform())
            new_messages.append({'message': prepare_alert_message(tweetable_alert), 'media': img_url})
            
    return new_messages
      
def retrieve_new_alerts():    
    # Make API call to retrieve alerts    
    alerts = get_alerts(creds[account_info()]['api_endpoint'])

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
    cleanup()

def send_tweets_alerts():
    [tweet.tweet_image_from_web(message['media'], message['message']) for message in aggregate_message_and_media()]
    print(f'{datetime.utcnow()} - Tweet alert code ran successfully!')
    cleanup()

if __name__ == '__main__':
    #log_alerts_messages()
    send_tweets_alerts()