import os

from social import Twitter
from db import Database
from accounts_args import account_info 
from accounts import creds
from helpers import api_get

dynamo = Database(creds[account_info()]['db_table_env_var_stories'])
tweet = Twitter(account_info())

def get_latest_story(desired_tag):
    data = api_get(f"https://api.npr.org/query?orgId=4780105&fields=title,parent,teaser,image&dateType=story&output=JSON&apiKey={os.environ['NPR_API_KEY']}")
    tag = data['list']['story'][0]['parent'][0]['title']['$text'].upper()
    return data['list']['story'][0] if tag == desired_tag.upper() else None

def get_teaser(story):
    return story['teaser']['$text']

def get_story_link(story):
    return story['link'][0]['$text']

def get_story_graphic(story):
    return story['image'][0]['src']

def twitter_message(story):
    message = f"{get_teaser(story)} More >> {get_story_link(story)}"
    return message

def send_tweet_story(story):
    tweet.tweet_image_from_web(get_story_graphic(story), twitter_message(story))

def is_story_already_tweeted(latest_story, existing_story):
    return True if existing_story[0]['id'] == latest_story['id'] else None

def is_database_empty(existing_story):
    return True if len(existing_story) == 0 else False

def store_story_metadata_in_db(story):
    dynamo.put(
        {'id': story['id'], 
        'title': story['title']['$text'], 
        'tag': story['parent'][0]['title']['$text']})

def main():
    latest_story = get_latest_story('FPREN')
    existing_story = dynamo.get_all()

    if is_database_empty(existing_story):
        store_story_metadata_in_db(latest_story)
        send_tweet_story(latest_story)
        return

    if not is_story_already_tweeted(latest_story, existing_story):
        store_story_metadata_in_db(latest_story)
        send_tweet_story(latest_story)
    
    return


if __name__ == '__main__':
    main()