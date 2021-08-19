import argparse
import os

from helpers import api_get
from social import Twitter

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--account', help='Twitter account name')
args = parser.parse_args()

if args.account:
    tweet = Twitter(args.account)
else:
    print('Specify an -a or --account argument')
    exit()

def get_latest_story():
    data = api_get(f"https://api.npr.org/query?orgId=4780105&fields=title,parent,teaser,image&dateType=story&output=JSON&apiKey={os.environ['NPR_API_KEY']}")
    return data['list']['story'][0]

def get_network():
    latest_story = get_latest_story()
    is_fpren = True if latest_story['parent'][0]['title']['$text'] == 'FPREN' else False
    return latest_story['parent'][0]['title']['$text'] if is_fpren else False

def get_title():
    return get_latest_story()['title']['$text'] if get_network() else False

def get_teaser():
    return get_latest_story()['teaser']['$text'] if get_network() else False

def get_story_link():
    return get_latest_story()['link'][0]['$text'] if get_network() else False

def get_story_graphic():
    return get_latest_story()['image'][0]['src']

def twitter_message():
    message = f"{get_teaser()} More >> {get_story_link()}"
    return message

def send_tweet_story():
    tweet.tweet_image_from_web(get_story_graphic(), twitter_message())


if __name__ == '__main__':
    send_tweet_story()