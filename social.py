import os
import requests
import tweepy

class Twitter:

    def __init__(self, account, hashtag):
        self.account = account
        self.hashtag = hashtag

    def twitter_api(self):
        creds = {
            'palmetto_storms': {
                'consumer_key': os.environ['TWITTER_CONSUMER_KEY_PALMETTO'],
                'consumer_secret': os.environ['TWITTER_CONSUMER_SECRET_PALMETTO'],
                'access_token': os.environ['TWITTER_ACCESS_TOKEN_PALMETTO'],
                'access_token_secret': os.environ['TWITTER_ACCESS_TOKEN_SECRET_PALMETTO']
            },
            'ray_hawthorne': {
                'consumer_key': os.environ['TWITTER_CONSUMER_KEY'],
                'consumer_secret': os.environ['TWITTER_CONSUMER_SECRET'],
                'access_token': os.environ['TWITTER_ACCESS_TOKEN'],
                'access_token_secret': os.environ['TWITTER_ACCESS_TOKEN_SECRET']
            }
        }

        api_credentials = creds.get(self.account)

        auth = tweepy.OAuthHandler(api_credentials['consumer_key'], api_credentials['consumer_secret'])
        auth.set_access_token(api_credentials['access_token'], api_credentials['access_token_secret'])
        return tweepy.API(auth)

    def tweet_text_only(self, message):
        message = f'{message[:270]} {self.hashtag}'
        try:
            self.twitter_api().update_status(message)
        except tweepy.TweepError as e:
            print(f'Error message: {e.reason}. Intended tweet: {message}')
            return
        
    def tweet_text_and_media(self, message, media_id):
        message = f'{message[:270]} {self.hashtag}'
        try:
            self.twitter_api().update_status(status=message, media_ids=[media_id])
        except tweepy.TweepError as e:
            print(f'Error message: {e.reason}. Intended media_id: {media_id} Intended tweet:{message}')
            return

    def twitter_media_upload(self, filename):
        media = self.twitter_api().media_upload(filename)
        return media

    def tweet_image_from_web(self, url, message):
        filename = 'temp.jpg'
        request = requests.get(url, stream=True)
        if request.status_code == 200:
            with open(filename, 'wb') as image:
                for chunk in request:
                    image.write(chunk)

            self.twitter_api().update_with_media(filename, status=message)
            os.remove(filename)
        else:
            print('Unable to download image')
            
    def tweet_image_from_local(self, filename, message):
        self.twitter_api().update_with_media(filename, message)